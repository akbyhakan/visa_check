"""
Helpers - Yardımcı fonksiyonlar
"""

import asyncio
import random
import re
from datetime import datetime
from typing import TypeVar, Callable, Any
from functools import wraps


T = TypeVar('T')


def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Async retry decorator with exponential backoff"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
            
            raise last_exception
        return wrapper
    return decorator


async def random_delay(min_seconds: float = 1.0, max_seconds: float = 3.0) -> None:
    """Random delay between actions to appear more human-like"""
    delay = random.uniform(min_seconds, max_seconds)
    await asyncio.sleep(delay)


def format_date(date: datetime, format_str: str = "%d.%m.%Y %H:%M") -> str:
    """Format datetime to string"""
    return date.strftime(format_str)


def parse_date(date_str: str, format_str: str = "%d.%m.%Y") -> datetime:
    """Parse string to datetime"""
    return datetime.strptime(date_str, format_str)


def mask_sensitive(text: str, visible_chars: int = 4) -> str:
    """Mask sensitive data like passwords and tokens"""
    if not text or len(text) <= visible_chars:
        return "*" * len(text) if text else ""
    return text[:visible_chars] + "*" * (len(text) - visible_chars)


def mask_email(email: str) -> str:
    """Mask email address for logging"""
    if not email or "@" not in email:
        return mask_sensitive(email)
    
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        masked_local = "*" * len(local)
    else:
        masked_local = local[0] + "*" * (len(local) - 2) + local[-1]
    
    return f"{masked_local}@{domain}"


def extract_otp_from_text(text: str) -> str | None:
    """Extract 6-digit OTP code from text"""
    patterns = [
        r'\b(\d{6})\b',
        r'code[:\s]*(\d{6})',
        r'OTP[:\s]*(\d{6})',
        r'verification[:\s]*(\d{6})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def clean_text(text: str) -> str:
    """Clean and normalize text"""
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def truncate(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to max length"""
    if not text or len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def generate_session_id() -> str:
    """Generate unique session ID"""
    import uuid
    return str(uuid.uuid4())[:8]


def bytes_to_human(size: int) -> str:
    """Convert bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def seconds_to_human(seconds: float) -> str:
    """Convert seconds to human readable format"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


class RateLimiter:
    """Simple rate limiter"""
    
    def __init__(self, max_requests: int, time_window: float):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
    
    async def acquire(self) -> bool:
        now = datetime.now().timestamp()
        self.requests = [r for r in self.requests if now - r < self.time_window]
        
        if len(self.requests) >= self.max_requests:
            wait_time = self.time_window - (now - self.requests[0])
            if wait_time > 0:
                await asyncio.sleep(wait_time)
        
        self.requests.append(now)
        return True
