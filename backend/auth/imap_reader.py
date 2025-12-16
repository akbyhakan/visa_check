"""Gmail IMAP Reader - Email OTP okuyucu"""

import imaplib
import email
import re
import asyncio
from datetime import datetime, timedelta
from typing import Optional
from email.header import decode_header


class IMAPReader:
    def __init__(self, email_address: str, app_password: str):
        self.email_address = email_address
        self.app_password = app_password
        self.imap_server = "imap.gmail.com"
        self.imap_port = 993
        self.otp_patterns = [r'\b(\d{6})\b', r'OTP[:\s]+(\d{6})', r'kod[:\s]+(\d{6})']
        self.vfs_senders = ['vfs', 'vfsglobal', 'visa', 'appointment']
    
    def _connect(self) -> imaplib.IMAP4_SSL:
        mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
        mail.login(self.email_address, self.app_password)
        return mail
    
    def _extract_otp(self, text: str) -> Optional[str]:
        for pattern in self.otp_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def _decode_body(self, msg) -> str:
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        body += part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    except:
                        pass
        else:
            try:
                body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
            except:
                pass
        return body
    
    def get_latest_otp_sync(self) -> Optional[str]:
        try:
            mail = self._connect()
            mail.select('INBOX')
            since = (datetime.now() - timedelta(minutes=5)).strftime("%d-%b-%Y")
            status, messages = mail.search(None, f'(SINCE {since})')
            if status != 'OK':
                mail.logout()
                return None
            
            for eid in reversed(messages[0].split()[-10:]):
                try:
                    status, data = mail.fetch(eid, '(RFC822)')
                    msg = email.message_from_bytes(data[0][1])
                    sender = msg.get('From', '').lower()
                    subject = msg.get('Subject', '')
                    body = self._decode_body(msg)
                    text = f"{sender} {subject} {body}".lower()
                    
                    if any(v in text for v in self.vfs_senders):
                        otp = self._extract_otp(f"{subject} {body}")
                        if otp:
                            mail.logout()
                            return otp
                except:
                    continue
            mail.logout()
            return None
        except:
            return None
    
    async def get_latest_otp(self) -> Optional[str]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_latest_otp_sync)
    
    async def wait_for_otp(self, timeout: int = 120) -> Optional[str]:
        start = datetime.now()
        while (datetime.now() - start).total_seconds() < timeout:
            otp = await self.get_latest_otp()
            if otp:
                return otp
            await asyncio.sleep(3)
        return None
    
    def test_connection(self) -> bool:
        try:
            mail = self._connect()
            mail.logout()
            return True
        except:
            return False