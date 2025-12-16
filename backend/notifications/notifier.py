"""
Notifier - Çoklu kanal bildirim sistemi
"""

import asyncio
from enum import Enum
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from abc import ABC, abstractmethod


class NotificationType(Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    APPOINTMENT_FOUND = "appointment_found"
    OTP_REQUIRED = "otp_required"
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    SCAN_STARTED = "scan_started"
    SCAN_STOPPED = "scan_stopped"


class NotificationPriority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class Notification:
    type: NotificationType
    title: str
    message: str
    priority: NotificationPriority = NotificationPriority.NORMAL
    timestamp: datetime = field(default_factory=datetime.now)
    data: Dict[str, Any] = field(default_factory=dict)
    screenshot: Optional[bytes] = None


class NotificationChannel(ABC):
    @abstractmethod
    async def send(self, notification: Notification) -> bool:
        pass
    
    @abstractmethod
    def is_enabled(self) -> bool:
        pass


class Notifier:
    """Çoklu kanal bildirim yöneticisi"""
    
    def __init__(self):
        self.channels: List[NotificationChannel] = []
        self.history: List[Notification] = []
        self.max_history = 100
        self.callbacks: List[Callable[[Notification], None]] = []
    
    def add_channel(self, channel: NotificationChannel) -> None:
        self.channels.append(channel)
    
    def add_callback(self, callback: Callable[[Notification], None]) -> None:
        self.callbacks.append(callback)
    
    async def notify(
        self,
        type: NotificationType,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        data: Dict[str, Any] = None,
        screenshot: bytes = None
    ) -> bool:
        notification = Notification(
            type=type,
            title=title,
            message=message,
            priority=priority,
            data=data or {},
            screenshot=screenshot
        )
        
        self.history.append(notification)
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
        
        for callback in self.callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(notification)
                else:
                    callback(notification)
            except:
                pass
        
        success = False
        for channel in self.channels:
            if channel.is_enabled():
                try:
                    if await channel.send(notification):
                        success = True
                except:
                    pass
        
        return success
    
    async def notify_appointment_found(self, location: str, dates: List[str], screenshot: bytes = None) -> bool:
        message = f"📍 {location}\n📅 Tarihler:\n" + "\n".join(f"  • {d}" for d in dates[:5])
        return await self.notify(
            type=NotificationType.APPOINTMENT_FOUND,
            title="🎉 RANDEVU BULUNDU!",
            message=message,
            priority=NotificationPriority.URGENT,
            data={"location": location, "dates": dates},
            screenshot=screenshot
        )
    
    async def notify_error(self, error: str) -> bool:
        return await self.notify(
            type=NotificationType.ERROR,
            title="❌ Hata",
            message=error,
            priority=NotificationPriority.HIGH
        )
    
    async def notify_otp_required(self) -> bool:
        return await self.notify(
            type=NotificationType.OTP_REQUIRED,
            title="🔐 OTP Gerekli",
            message="Lütfen SMS/Email doğrulama kodunu girin.",
            priority=NotificationPriority.URGENT
        )
    
    def get_history(self, type: NotificationType = None, limit: int = 20) -> List[Notification]:
        history = self.history
        if type:
            history = [n for n in history if n.type == type]
        return history[-limit:]
