"""
Appointment Scanner - VFS Global randevu tarama motoru
"""

import asyncio
import random
from datetime import datetime
from typing import Optional, Dict, List, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from playwright.async_api import Page


class ScanStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"
    FOUND = "found"


@dataclass
class ScanResult:
    found: bool
    dates: List[str] = field(default_factory=list)
    location: str = ""
    appointment_type: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    screenshot: Optional[bytes] = None
    error: Optional[str] = None


@dataclass
class ScanConfig:
    target_url: str
    visa_center: str
    visa_category: str
    visa_subcategory: str
    preferred_dates: List[str] = field(default_factory=list)
    scan_interval: int = 30


class AppointmentScanner:
    """VFS Global randevu tarama motoru"""
    
    SELECTORS = {
        "appointment_button": "[data-testid='appointment-button'], .appointment-btn",
        "available_date": ".available-date, td.available",
        "no_appointment": ".no-appointment, :text('müsait randevu bulunmamaktadır')",
        "visa_center_dropdown": "select[name='visa-center'], #visa-center",
        "category_dropdown": "select[name='category'], #category",
        "continue_button": "button[type='submit'], .continue-btn",
        "captcha_frame": "iframe[src*='captcha']",
    }
    
    def __init__(self, browser_manager, login_handler, captcha_solver=None, on_found_callback=None):
        self.browser = browser_manager
        self.login_handler = login_handler
        self.captcha_solver = captcha_solver
        self.on_found_callback = on_found_callback
        self.status = ScanStatus.IDLE
        self.scan_count = 0
        self.last_scan_time = None
        self.last_result = None
        self._stop_event = asyncio.Event()
        self._pause_event = asyncio.Event()
        self._pause_event.set()
    
    async def start_scanning(self, config: ScanConfig) -> None:
        self.status = ScanStatus.RUNNING
        self._stop_event.clear()
        
        while not self._stop_event.is_set():
            await self._pause_event.wait()
            if self._stop_event.is_set():
                break
            
            try:
                result = await self._perform_scan(config)
                self.last_result = result
                self.scan_count += 1
                self.last_scan_time = datetime.now()
                
                if result.found:
                    self.status = ScanStatus.FOUND
                    if self.on_found_callback:
                        await self._safe_callback(result)
            except Exception as e:
                print(f"[Scanner] Error: {e}")
                await asyncio.sleep(10)
            
            interval = config.scan_interval + random.randint(-5, 10)
            await self._wait_with_interrupt(interval)
        
        self.status = ScanStatus.STOPPED
    
    async def _perform_scan(self, config: ScanConfig) -> ScanResult:
        page = await self.browser.get_page()
        
        try:
            if not await self._check_logged_in(page):
                await self.login_handler.login(page)
            
            await self._navigate_to_appointment_page(page, config)
            
            if await self._check_captcha(page) and self.captcha_solver:
                await self._solve_captcha(page)
            
            return await self._check_availability(page, config)
        except Exception as e:
            return ScanResult(found=False, error=str(e))
    
    async def _check_logged_in(self, page: Page) -> bool:
        return "login" not in page.url.lower()
    
    async def _navigate_to_appointment_page(self, page: Page, config: ScanConfig) -> None:
        btn = await page.query_selector(self.SELECTORS["appointment_button"])
        if btn:
            await btn.click()
            await page.wait_for_load_state("networkidle")
        
        center = await page.query_selector(self.SELECTORS["visa_center_dropdown"])
        if center:
            await center.select_option(label=config.visa_center)
            await asyncio.sleep(1)
        
        category = await page.query_selector(self.SELECTORS["category_dropdown"])
        if category:
            await category.select_option(label=config.visa_category)
            await asyncio.sleep(1)
        
        continue_btn = await page.query_selector(self.SELECTORS["continue_button"])
        if continue_btn:
            await continue_btn.click()
            await page.wait_for_load_state("networkidle")
    
    async def _check_captcha(self, page: Page) -> bool:
        return await page.query_selector(self.SELECTORS["captcha_frame"]) is not None
    
    async def _solve_captcha(self, page: Page) -> bool:
        if not self.captcha_solver:
            return False
        try:
            site_key = await page.evaluate("() => document.querySelector('[data-sitekey]')?.getAttribute('data-sitekey')")
            if not site_key:
                return False
            token = await self.captcha_solver.solve_recaptcha(site_key, page.url)
            await page.evaluate(f"document.querySelector('#g-recaptcha-response').value = '{token}'")
            return True
        except:
            return False
    
    async def _check_availability(self, page: Page, config: ScanConfig) -> ScanResult:
        no_appt = await page.query_selector(self.SELECTORS["no_appointment"])
        if no_appt:
            return ScanResult(found=False, location=config.visa_center)
        
        available = await page.query_selector_all(self.SELECTORS["available_date"])
        if available:
            dates = []
            for el in available:
                text = await el.text_content()
                if text:
                    dates.append(text.strip())
            if dates:
                return ScanResult(found=True, dates=dates, location=config.visa_center)
        
        return ScanResult(found=False, location=config.visa_center)
    
    async def _wait_with_interrupt(self, seconds: int) -> None:
        try:
            await asyncio.wait_for(self._stop_event.wait(), timeout=seconds)
        except asyncio.TimeoutError:
            pass
    
    async def _safe_callback(self, result: ScanResult) -> None:
        try:
            if asyncio.iscoroutinefunction(self.on_found_callback):
                await self.on_found_callback(result)
            else:
                self.on_found_callback(result)
        except Exception as e:
            print(f"[Scanner] Callback error: {e}")
    
    def stop(self):
        self._stop_event.set()
        self._pause_event.set()
        self.status = ScanStatus.STOPPED
    
    def pause(self):
        self._pause_event.clear()
        self.status = ScanStatus.PAUSED
    
    def resume(self):
        self._pause_event.set()
        self.status = ScanStatus.RUNNING
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "scan_count": self.scan_count,
            "last_scan": self.last_scan_time.isoformat() if self.last_scan_time else None,
            "last_found": self.last_result.found if self.last_result else None
        }
