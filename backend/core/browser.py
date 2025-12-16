import asyncio
from typing import Optional, Dict, List
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from config import settings, COUNTRIES

class BrowserManager:
    """Playwright Firefox tarayıcı yönetimi"""
    
    def __init__(self):
        self.playwright = None
        self.browsers: Dict[str, Browser] = {}
        self.contexts: Dict[str, BrowserContext] = {}
        self.pages: Dict[str, Page] = {}
    
    async def initialize(self):
        """Playwright'i başlat"""
        if not self.playwright:
            self.playwright = await async_playwright().start()
    
    async def create_browser(self, country_code: str, proxy: Optional[Dict] = None) -> Page:
        """Yeni bir Firefox tarayıcı oluştur"""
        await self.initialize()
        
        launch_options = {
            "headless": True,
            "firefox_user_prefs": {
                "media.navigator.enabled": False,
                "geo.enabled": False,
            }
        }
        
        if proxy:
            launch_options["proxy"] = {
                "server": f"http://{proxy['host']}:{proxy['port']}",
                "username": proxy.get("username"),
                "password": proxy.get("password")
            }
        
        browser = await self.playwright.firefox.launch(**launch_options)
        self.browsers[country_code] = browser
        
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="tr-TR",
            timezone_id="Europe/Istanbul",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
        )
        self.contexts[country_code] = context
        
        page = await context.new_page()
        self.pages[country_code] = page
        
        return page
    
    async def get_page(self, country_code: str) -> Optional[Page]:
        return self.pages.get(country_code)
    
    async def close_browser(self, country_code: str):
        if country_code in self.pages:
            try:
                await self.pages[country_code].close()
            except:
                pass
            del self.pages[country_code]
        
        if country_code in self.contexts:
            try:
                await self.contexts[country_code].close()
            except:
                pass
            del self.contexts[country_code]
        
        if country_code in self.browsers:
            try:
                await self.browsers[country_code].close()
            except:
                pass
            del self.browsers[country_code]
    
    async def clear_browser_data(self, country_code: str):
        if country_code in self.contexts:
            context = self.contexts[country_code]
            try:
                await context.clear_cookies()
                if country_code in self.pages:
                    page = self.pages[country_code]
                    await page.evaluate("window.localStorage.clear()")
                    await page.evaluate("window.sessionStorage.clear()")
            except Exception as e:
                print(f"Error clearing browser data for {country_code}: {e}")
    
    async def take_screenshot(self, country_code: str, path: str) -> bool:
        if country_code in self.pages:
            try:
                await self.pages[country_code].screenshot(path=path, full_page=True)
                return True
            except Exception as e:
                print(f"Screenshot error for {country_code}: {e}")
        return False
    
    async def close_all(self):
        for country_code in list(self.browsers.keys()):
            await self.close_browser(country_code)
        
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None

browser_manager = BrowserManager()
