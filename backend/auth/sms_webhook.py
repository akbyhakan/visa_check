"""SMS Webhook Handler - Android SMS Forwarder"""

import re
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from dataclasses import dataclass
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/webhook", tags=["SMS"])

class SMSPayload(BaseModel):
    from_number: Optional[str] = None
    sender: Optional[str] = None
    message: str

@dataclass
class OTPCode:
    code: str
    sender: str
    received_at: datetime
    used: bool = False

class SMSOTPStore:
    def __init__(self):
        self.codes: List[OTPCode] = []
    
    def extract_otp(self, message: str) -> Optional[str]:
        match = re.search(r'\b(\d{6})\b', message)
        return match.group(1) if match else None
    
    def add_sms(self, sender: str, message: str) -> Optional[str]:
        self.clear_old_codes()
        otp = self.extract_otp(message)
        if otp:
            self.codes.append(OTPCode(code=otp, sender=sender, received_at=datetime.now()))
            return otp
        return None
    
    def get_latest_code(self) -> Optional[str]:
        self.clear_old_codes()
        unused = [c for c in self.codes if not c.used]
        return max(unused, key=lambda x: x.received_at).code if unused else None
    
    def mark_as_used(self, code: str):
        for c in self.codes:
            if c.code == code:
                c.used = True
    
    def clear_old_codes(self):
        cutoff = datetime.now() - timedelta(seconds=300)
        self.codes = [c for c in self.codes if c.received_at > cutoff]
    
    def clear_all(self):
        self.codes = []

sms_otp_store = SMSOTPStore()

class SMSWebhookHandler:
    def __init__(self, store):
        self.store = store
    
    def process_sms(self, payload: SMSPayload) -> Dict:
        sender = payload.from_number or payload.sender or "Unknown"
        otp = self.store.add_sms(sender, payload.message)
        return {"success": True, "otp": otp}

webhook_handler = SMSWebhookHandler(sms_otp_store)

@router.post("/sms")
async def receive_sms(payload: SMSPayload):
    return webhook_handler.process_sms(payload)

@router.get("/sms/latest")
async def get_latest():
    return {"code": sms_otp_store.get_latest_code()}
