"""
Health Checker - Sistem sağlık kontrolü
"""

import asyncio
import aiohttp
from enum import Enum
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ComponentHealth:
    name: str
    status: HealthStatus
    message: str = ""
    latency_ms: float = 0
    last_check: datetime = field(default_factory=datetime.now)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemHealth:
    status: HealthStatus
    components: Dict[str, ComponentHealth] = field(default_factory=dict)
    uptime_seconds: float = 0
    checked_at: datetime = field(default_factory=datetime.now)
    
    @property
    def is_healthy(self) -> bool:
        return self.status == HealthStatus.HEALTHY


class HealthChecker:
    """Sistem sağlık kontrolcüsü"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.last_health: Optional[SystemHealth] = None
        self.check_interval = 60
    
    async def check_all(self) -> SystemHealth:
        components = {}
        
        components["browser"] = await self._check_browser()
        components["proxy"] = await self._check_proxy()
        components["captcha_service"] = await self._check_captcha_service()
        components["telegram"] = await self._check_telegram()
        components["vfs_website"] = await self._check_vfs_website()
        
        unhealthy = sum(1 for c in components.values() if c.status == HealthStatus.UNHEALTHY)
        degraded = sum(1 for c in components.values() if c.status == HealthStatus.DEGRADED)
        
        if unhealthy > 0:
            overall = HealthStatus.UNHEALTHY
        elif degraded > 0:
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.HEALTHY
        
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        self.last_health = SystemHealth(
            status=overall,
            components=components,
            uptime_seconds=uptime
        )
        return self.last_health
    
    async def _check_browser(self) -> ComponentHealth:
        try:
            from backend.core.browser import BrowserManager
            return ComponentHealth(name="browser", status=HealthStatus.HEALTHY, message="Browser modülü yüklü")
        except Exception as e:
            return ComponentHealth(name="browser", status=HealthStatus.UNHEALTHY, message=str(e))
    
    async def _check_proxy(self) -> ComponentHealth:
        from backend.config import settings
        if settings.PROXY_ENABLED:
            return ComponentHealth(name="proxy", status=HealthStatus.HEALTHY, message="Proxy aktif")
        return ComponentHealth(name="proxy", status=HealthStatus.DEGRADED, message="Proxy devre dışı")
    
    async def _check_captcha_service(self) -> ComponentHealth:
        from backend.config import settings
        if settings.CAPSOLVER_API_KEY:
            return ComponentHealth(name="captcha_service", status=HealthStatus.HEALTHY, message="CapSolver yapılandırılmış")
        return ComponentHealth(name="captcha_service", status=HealthStatus.DEGRADED, message="API key eksik")
    
    async def _check_telegram(self) -> ComponentHealth:
        from backend.config import settings
        if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID:
            return ComponentHealth(name="telegram", status=HealthStatus.HEALTHY, message="Telegram yapılandırılmış")
        return ComponentHealth(name="telegram", status=HealthStatus.DEGRADED, message="Telegram yapılandırılmamış")
    
    async def _check_vfs_website(self) -> ComponentHealth:
        url = "https://visa.vfsglobal.com"
        start = datetime.now()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    latency = (datetime.now() - start).total_seconds() * 1000
                    if resp.status == 200:
                        return ComponentHealth(name="vfs_website", status=HealthStatus.HEALTHY, message="VFS erişilebilir", latency_ms=latency)
                    return ComponentHealth(name="vfs_website", status=HealthStatus.DEGRADED, message=f"HTTP {resp.status}", latency_ms=latency)
        except Exception as e:
            return ComponentHealth(name="vfs_website", status=HealthStatus.UNHEALTHY, message=str(e))
    
    def get_summary(self) -> Dict[str, Any]:
        if not self.last_health:
            return {"status": "unknown", "message": "Henüz kontrol yapılmadı"}
        
        return {
            "status": self.last_health.status.value,
            "uptime": f"{self.last_health.uptime_seconds / 3600:.1f} saat",
            "components": {name: comp.status.value for name, comp in self.last_health.components.items()},
            "checked_at": self.last_health.checked_at.isoformat()
        }
