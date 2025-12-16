"""
OTP Handler Module
Coordinates SMS and Email OTP verification for authentication.

Created: 2025-12-16
"""

import secrets
import hashlib
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass


class OTPChannel(Enum):
    """Supported OTP delivery channels."""
    SMS = "sms"
    EMAIL = "email"


class OTPStatus(Enum):
    """OTP verification status."""
    PENDING = "pending"
    VERIFIED = "verified"
    EXPIRED = "expired"
    INVALID = "invalid"
    MAX_ATTEMPTS_EXCEEDED = "max_attempts_exceeded"


@dataclass
class OTPRecord:
    """Data class representing an OTP record."""
    otp_hash: str
    channel: OTPChannel
    created_at: datetime
    expires_at: datetime
    attempts: int = 0
    verified: bool = False


class OTPHandler:
    """
    Handles OTP generation, storage, and verification for both SMS and Email channels.
    
    This class coordinates the OTP verification process, supporting multiple
    delivery channels and providing secure verification mechanisms.
    """
    
    DEFAULT_OTP_LENGTH = 6
    DEFAULT_EXPIRY_MINUTES = 5
    MAX_VERIFICATION_ATTEMPTS = 3
    
    def __init__(
        self,
        otp_length: int = DEFAULT_OTP_LENGTH,
        expiry_minutes: int = DEFAULT_EXPIRY_MINUTES,
        max_attempts: int = MAX_VERIFICATION_ATTEMPTS
    ):
        """
        Initialize the OTP Handler.
        
        Args:
            otp_length: Length of the OTP code (default: 6)
            expiry_minutes: OTP validity period in minutes (default: 5)
            max_attempts: Maximum verification attempts allowed (default: 3)
        """
        self.otp_length = otp_length
        self.expiry_minutes = expiry_minutes
        self.max_attempts = max_attempts
        self._otp_store: Dict[str, OTPRecord] = {}
    
    def _generate_otp(self) -> str:
        """Generate a secure random OTP code."""
        return ''.join(secrets.choice('0123456789') for _ in range(self.otp_length))
    
    def _hash_otp(self, otp: str) -> str:
        """Hash the OTP for secure storage."""
        return hashlib.sha256(otp.encode()).hexdigest()
    
    def _get_storage_key(self, identifier: str, channel: OTPChannel) -> str:
        """Generate a unique storage key for the OTP record."""
        return f"{channel.value}:{identifier}"
    
    def generate_and_send_otp(
        self,
        identifier: str,
        channel: OTPChannel,
        send_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Generate an OTP and send it via the specified channel.
        
        Args:
            identifier: User identifier (phone number for SMS, email address for Email)
            channel: Delivery channel (SMS or EMAIL)
            send_callback: Optional callback function to handle actual delivery
            
        Returns:
            Dictionary containing generation status and metadata
        """
        otp = self._generate_otp()
        otp_hash = self._hash_otp(otp)
        now = datetime.utcnow()
        expires_at = now + timedelta(minutes=self.expiry_minutes)
        
        storage_key = self._get_storage_key(identifier, channel)
        
        self._otp_store[storage_key] = OTPRecord(
            otp_hash=otp_hash,
            channel=channel,
            created_at=now,
            expires_at=expires_at,
            attempts=0,
            verified=False
        )
        
        # Send OTP via callback if provided
        delivery_status = "pending"
        if send_callback:
            try:
                send_callback(identifier, otp, channel)
                delivery_status = "sent"
            except Exception as e:
                delivery_status = f"failed: {str(e)}"
        
        return {
            "status": "generated",
            "channel": channel.value,
            "identifier": self._mask_identifier(identifier, channel),
            "expires_at": expires_at.isoformat(),
            "delivery_status": delivery_status,
            # Note: In production, never return the OTP. This is for testing only.
            # "otp": otp  
        }
    
    def verify_otp(
        self,
        identifier: str,
        channel: OTPChannel,
        otp: str
    ) -> Dict[str, Any]:
        """
        Verify an OTP code.
        
        Args:
            identifier: User identifier used during OTP generation
            channel: The channel used for OTP delivery
            otp: The OTP code to verify
            
        Returns:
            Dictionary containing verification result and status
        """
        storage_key = self._get_storage_key(identifier, channel)
        record = self._otp_store.get(storage_key)
        
        if not record:
            return {
                "verified": False,
                "status": OTPStatus.INVALID.value,
                "message": "No OTP found for this identifier"
            }
        
        # Check if already verified
        if record.verified:
            return {
                "verified": False,
                "status": OTPStatus.INVALID.value,
                "message": "OTP has already been used"
            }
        
        # Check expiration
        if datetime.utcnow() > record.expires_at:
            self._invalidate_otp(storage_key)
            return {
                "verified": False,
                "status": OTPStatus.EXPIRED.value,
                "message": "OTP has expired"
            }
        
        # Check max attempts
        if record.attempts >= self.max_attempts:
            self._invalidate_otp(storage_key)
            return {
                "verified": False,
                "status": OTPStatus.MAX_ATTEMPTS_EXCEEDED.value,
                "message": "Maximum verification attempts exceeded"
            }
        
        # Increment attempt counter
        record.attempts += 1
        
        # Verify OTP
        if self._hash_otp(otp) == record.otp_hash:
            record.verified = True
            return {
                "verified": True,
                "status": OTPStatus.VERIFIED.value,
                "message": "OTP verified successfully"
            }
        
        remaining_attempts = self.max_attempts - record.attempts
        return {
            "verified": False,
            "status": OTPStatus.INVALID.value,
            "message": f"Invalid OTP. {remaining_attempts} attempts remaining",
            "remaining_attempts": remaining_attempts
        }
    
    def _invalidate_otp(self, storage_key: str) -> None:
        """Remove an OTP record from storage."""
        if storage_key in self._otp_store:
            del self._otp_store[storage_key]
    
    def _mask_identifier(self, identifier: str, channel: OTPChannel) -> str:
        """Mask the identifier for privacy in responses."""
        if channel == OTPChannel.SMS:
            # Mask phone number: +1234567890 -> +1***7890
            if len(identifier) > 4:
                return identifier[:2] + "***" + identifier[-4:]
            return "***"
        elif channel == OTPChannel.EMAIL:
            # Mask email: user@example.com -> u***@example.com
            if "@" in identifier:
                local, domain = identifier.split("@", 1)
                if len(local) > 1:
                    return local[0] + "***@" + domain
                return "***@" + domain
            return "***"
        return "***"
    
    def resend_otp(
        self,
        identifier: str,
        channel: OTPChannel,
        send_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Resend OTP to the specified identifier.
        
        This invalidates any existing OTP and generates a new one.
        
        Args:
            identifier: User identifier
            channel: Delivery channel
            send_callback: Optional callback for delivery
            
        Returns:
            Dictionary containing resend status
        """
        storage_key = self._get_storage_key(identifier, channel)
        self._invalidate_otp(storage_key)
        return self.generate_and_send_otp(identifier, channel, send_callback)
    
    def get_otp_status(self, identifier: str, channel: OTPChannel) -> Dict[str, Any]:
        """
        Get the current status of an OTP.
        
        Args:
            identifier: User identifier
            channel: Delivery channel
            
        Returns:
            Dictionary containing OTP status information
        """
        storage_key = self._get_storage_key(identifier, channel)
        record = self._otp_store.get(storage_key)
        
        if not record:
            return {
                "exists": False,
                "status": "not_found"
            }
        
        now = datetime.utcnow()
        is_expired = now > record.expires_at
        
        return {
            "exists": True,
            "status": OTPStatus.EXPIRED.value if is_expired else OTPStatus.PENDING.value,
            "verified": record.verified,
            "attempts_used": record.attempts,
            "attempts_remaining": max(0, self.max_attempts - record.attempts),
            "expires_at": record.expires_at.isoformat(),
            "is_expired": is_expired
        }


class SMSEmailOTPCoordinator:
    """
    Coordinator class for managing both SMS and Email OTP verification.
    
    Provides a unified interface for dual-channel OTP verification flows.
    """
    
    def __init__(self, otp_handler: Optional[OTPHandler] = None):
        """
        Initialize the coordinator.
        
        Args:
            otp_handler: Optional custom OTPHandler instance
        """
        self.otp_handler = otp_handler or OTPHandler()
    
    def initiate_sms_verification(
        self,
        phone_number: str,
        send_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """Initiate SMS OTP verification."""
        return self.otp_handler.generate_and_send_otp(
            identifier=phone_number,
            channel=OTPChannel.SMS,
            send_callback=send_callback
        )
    
    def initiate_email_verification(
        self,
        email: str,
        send_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """Initiate Email OTP verification."""
        return self.otp_handler.generate_and_send_otp(
            identifier=email,
            channel=OTPChannel.EMAIL,
            send_callback=send_callback
        )
    
    def verify_sms_otp(self, phone_number: str, otp: str) -> Dict[str, Any]:
        """Verify SMS OTP."""
        return self.otp_handler.verify_otp(
            identifier=phone_number,
            channel=OTPChannel.SMS,
            otp=otp
        )
    
    def verify_email_otp(self, email: str, otp: str) -> Dict[str, Any]:
        """Verify Email OTP."""
        return self.otp_handler.verify_otp(
            identifier=email,
            channel=OTPChannel.EMAIL,
            otp=otp
        )
    
    def verify_dual_channel(
        self,
        phone_number: str,
        sms_otp: str,
        email: str,
        email_otp: str
    ) -> Dict[str, Any]:
        """
        Verify both SMS and Email OTPs for dual-channel authentication.
        
        Args:
            phone_number: User's phone number
            sms_otp: OTP received via SMS
            email: User's email address
            email_otp: OTP received via email
            
        Returns:
            Dictionary containing dual verification result
        """
        sms_result = self.verify_sms_otp(phone_number, sms_otp)
        email_result = self.verify_email_otp(email, email_otp)
        
        both_verified = sms_result.get("verified") and email_result.get("verified")
        
        return {
            "fully_verified": both_verified,
            "sms_verification": sms_result,
            "email_verification": email_result
        }
