"""
Telegram Bot - Telegram bildirim entegrasyonu
"""

import asyncio
import aiohttp
from typing import Optional, List
from dataclasses import dataclass

from backend.config import settings
from .notifier import NotificationChannel, Notification, NotificationType


@dataclass
class TelegramConfig:
    bot_token: str
    chat_id: str
    parse_mode: str = "HTML"
    disable_notification: bool = False


class TelegramNotifier(NotificationChannel):
    """Telegram bildirim kanalı"""
    
    BASE_URL = "https://api.telegram.org/bot{token}/{method}"
    
    EMOJI_MAP = {
        NotificationType.INFO: "ℹ️",
        NotificationType.SUCCESS: "✅",
        NotificationType.WARNING: "⚠️",
        NotificationType.ERROR: "❌",
        NotificationType.APPOINTMENT_FOUND: "🎉",
        NotificationType.OTP_REQUIRED: "🔐",
        NotificationType.LOGIN_SUCCESS: "🔓",
        NotificationType.LOGIN_FAILED: "🔒",
        NotificationType.SCAN_STARTED: "▶️",
        NotificationType.SCAN_STOPPED: "⏹️",
    }
    
    def __init__(self, bot_token: str = None, chat_id: str = None):
        self.bot_token = bot_token or settings.TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or settings.TELEGRAM_CHAT_ID
        self._enabled = bool(self.bot_token and self.chat_id)
    
    def is_enabled(self) -> bool:
        return self._enabled
    
    async def send(self, notification: Notification) -> bool:
        if not self._enabled:
            return False
        
        try:
            emoji = self.EMOJI_MAP.get(notification.type, "📢")
            message = f"{emoji} <b>{notification.title}</b>\n\n{notification.message}"
            
            if notification.data:
                if "location" in notification.data:
                    message += f"\n\n📍 <b>Lokasyon:</b> {notification.data['location']}"
                if "dates" in notification.data:
                    dates = notification.data["dates"][:5]
                    message += "\n📅 <b>Tarihler:</b>\n" + "\n".join(f"  • {d}" for d in dates)
            
            message += f"\n\n🕐 {notification.timestamp.strftime('%H:%M:%S')}"
            
            success = await self._send_message(message)
            
            if success and notification.screenshot:
                await self._send_photo(notification.screenshot, f"{emoji} {notification.title}")
            
            return success
        except Exception as e:
            print(f"[Telegram] Gönderim hatası: {e}")
            return False
    
    async def _send_message(self, text: str) -> bool:
        url = self.BASE_URL.format(token=self.bot_token, method="sendMessage")
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as resp:
                    result = await resp.json()
                    return result.get("ok", False)
        except:
            return False
    
    async def _send_photo(self, photo: bytes, caption: str = "") -> bool:
        url = self.BASE_URL.format(token=self.bot_token, method="sendPhoto")
        
        try:
            data = aiohttp.FormData()
            data.add_field("chat_id", self.chat_id)
            data.add_field("photo", photo, filename="screenshot.png", content_type="image/png")
            if caption:
                data.add_field("caption", caption[:1024])
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data) as resp:
                    result = await resp.json()
                    return result.get("ok", False)
        except:
            return False
    
    async def send_quick_message(self, text: str) -> bool:
        return await self._send_message(text)
    
    async def test_connection(self) -> bool:
        if not self._enabled:
            return False
        
        url = self.BASE_URL.format(token=self.bot_token, method="getMe")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    result = await resp.json()
                    return result.get("ok", False)
        except:
            return False
