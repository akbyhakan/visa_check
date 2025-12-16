"""
Screen Detector - VFS Global sayfa durumu algılama
"""

import re
from enum import Enum
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from playwright.async_api import Page


class ScreenType(Enum):
    UNKNOWN = "unknown"
    LOGIN = "login"
    OTP_VERIFICATION = "otp_verification"
    DASHBOARD = "dashboard"
    APPOINTMENT_SELECTION = "appointment_selection"
    DATE_SELECTION = "date_selection"
    TIME_SELECTION = "time_selection"
    CONFIRMATION = "confirmation"
    SUCCESS = "success"
    ERROR = "error"
    CAPTCHA = "captcha"
    MAINTENANCE = "maintenance"
    BLOCKED = "blocked"
    NO_APPOINTMENT = "no_appointment"


@dataclass
class ScreenInfo:
    screen_type: ScreenType
    url: str
    title: str
    has_captcha: bool = False
    has_error: bool = False
    error_message: Optional[str] = None
    available_actions: List[str] = None
    metadata: Dict = None
    
    def __post_init__(self):
        if self.available_actions is None:
            self.available_actions = []
        if self.metadata is None:
            self.metadata = {}


class ScreenDetector:
    """VFS Global sayfalarını algılar"""
    
    URL_PATTERNS = {
        ScreenType.LOGIN: [r'/login', r'/sign-in'],
        ScreenType.OTP_VERIFICATION: [r'/otp', r'/verify', r'/2fa'],
        ScreenType.DASHBOARD: [r'/dashboard', r'/home'],
        ScreenType.APPOINTMENT_SELECTION: [r'/appointment', r'/book'],
        ScreenType.DATE_SELECTION: [r'/date', r'/calendar'],
        ScreenType.CONFIRMATION: [r'/confirm', r'/review'],
        ScreenType.SUCCESS: [r'/success', r'/complete'],
    }
    
    SCREEN_SELECTORS = {
        ScreenType.LOGIN: ["input[type='email']", "input[type='password']", "#login-form"],
        ScreenType.OTP_VERIFICATION: ["input[name='otp']", ".otp-input", "input[maxlength='6']"],
        ScreenType.DASHBOARD: [".dashboard", ".user-profile", ".welcome-message"],
        ScreenType.DATE_SELECTION: [".calendar", ".date-picker", ".available-dates"],
        ScreenType.TIME_SELECTION: [".time-slots", ".slot-picker"],
        ScreenType.CAPTCHA: ["iframe[src*='recaptcha']", ".g-recaptcha", "[data-sitekey]"],
        ScreenType.NO_APPOINTMENT: [":text('no appointment')", ":text('müsait randevu')"],
    }
    
    def __init__(self):
        self.last_screen: Optional[ScreenInfo] = None
        self.screen_history: List[ScreenType] = []
    
    async def detect(self, page: Page) -> ScreenInfo:
        url = page.url
        title = await page.title()
        
        screen_type = self._detect_from_url(url)
        if screen_type == ScreenType.UNKNOWN:
            screen_type = await self._detect_from_elements(page)
        
        has_captcha = await self._check_captcha(page)
        has_error, error_message = await self._check_error(page)
        actions = await self._get_available_actions(page)
        metadata = await self._collect_metadata(page, screen_type)
        
        screen_info = ScreenInfo(
            screen_type=screen_type,
            url=url,
            title=title,
            has_captcha=has_captcha,
            has_error=has_error,
            error_message=error_message,
            available_actions=actions,
            metadata=metadata
        )
        
        self.last_screen = screen_info
        self.screen_history.append(screen_type)
        if len(self.screen_history) > 50:
            self.screen_history = self.screen_history[-50:]
        
        return screen_info
    
    def _detect_from_url(self, url: str) -> ScreenType:
        url_lower = url.lower()
        for screen_type, patterns in self.URL_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, url_lower):
                    return screen_type
        return ScreenType.UNKNOWN
    
    async def _detect_from_elements(self, page: Page) -> ScreenType:
        for screen_type, selectors in self.SCREEN_SELECTORS.items():
            for selector in selectors:
                try:
                    if await page.query_selector(selector):
                        return screen_type
                except:
                    continue
        return ScreenType.UNKNOWN
    
    async def _check_captcha(self, page: Page) -> bool:
        captcha_selectors = ["iframe[src*='recaptcha']", ".g-recaptcha", "[data-sitekey]"]
        for selector in captcha_selectors:
            try:
                if await page.query_selector(selector):
                    return True
            except:
                continue
        return False
    
    async def _check_error(self, page: Page) -> Tuple[bool, Optional[str]]:
        error_selectors = [".error-message", ".alert-danger", ".error"]
        for selector in error_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    message = await element.text_content()
                    return True, message.strip() if message else None
            except:
                continue
        return False, None
    
    async def _get_available_actions(self, page: Page) -> List[str]:
        actions = []
        action_map = {
            "login": "button[type='submit'], .login-btn",
            "continue": ".continue-btn, button:has-text('Devam')",
            "select_date": ".available-date, td.available",
            "select_time": ".time-slot",
            "confirm": ".confirm-btn, button:has-text('Onayla')",
        }
        for action, selector in action_map.items():
            try:
                el = await page.query_selector(selector)
                if el and await el.is_visible():
                    actions.append(action)
            except:
                continue
        return actions
    
    async def _collect_metadata(self, page: Page, screen_type: ScreenType) -> Dict:
        metadata = {}
        if screen_type == ScreenType.DATE_SELECTION:
            try:
                dates = await page.query_selector_all(".available-date, td.available")
                metadata["available_dates"] = [await d.text_content() for d in dates if d]
            except:
                pass
        return metadata
    
    def get_next_action(self, screen_info: ScreenInfo) -> Optional[str]:
        action_map = {
            ScreenType.LOGIN: "login",
            ScreenType.OTP_VERIFICATION: "enter_otp",
            ScreenType.DASHBOARD: "navigate_to_appointment",
            ScreenType.DATE_SELECTION: "select_date",
            ScreenType.TIME_SELECTION: "select_time",
            ScreenType.CONFIRMATION: "confirm",
            ScreenType.CAPTCHA: "solve_captcha",
            ScreenType.ERROR: "handle_error",
        }
        return action_map.get(screen_info.screen_type)
    
    def is_success_state(self, screen_info: ScreenInfo) -> bool:
        return screen_info.screen_type == ScreenType.SUCCESS
    
    def is_error_state(self, screen_info: ScreenInfo) -> bool:
        return screen_info.screen_type in [ScreenType.ERROR, ScreenType.BLOCKED, ScreenType.MAINTENANCE]
