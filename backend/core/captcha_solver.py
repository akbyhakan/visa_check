import asyncio
import httpx
from typing import Optional
from playwright.async_api import Page

class CaptchaSolver:
    """2Captcha Turnstile çözücü"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "http://2captcha.com"
    
    async def solve_turnstile(self, page: Page, site_key: str, page_url: str) -> Optional[str]:
        """Cloudflare Turnstile captcha'yı çöz"""
        try:
            # 1. Captcha görevini gönder
            task_id = await self._create_task(site_key, page_url)
            if not task_id:
                return None
            
            # 2. Sonucu bekle (max 120 saniye)
            token = await self._wait_for_result(task_id, timeout=120)
            if not token:
                return None
            
            # 3. Token'ı sayfaya enjekte et
            await self._inject_token(page, token)
            
            return token
            
        except Exception as e:
            print(f"Captcha solve error: {e}")
            return None
    
    async def _create_task(self, site_key: str, page_url: str) -> Optional[str]:
        """2Captcha'ya görev gönder"""
        async with httpx.AsyncClient() as client:
            params = {
                "key": self.api_key,
                "method": "turnstile",
                "sitekey": site_key,
                "pageurl": page_url,
                "json": 1
            }
            
            response = await client.get(f"{self.base_url}/in.php", params=params)
            data = response.json()
            
            if data.get("status") == 1:
                return data.get("request")
            else:
                print(f"2Captcha task creation failed: {data}")
                return None
    
    async def _wait_for_result(self, task_id: str, timeout: int = 120) -> Optional[str]:
        """Captcha sonucunu bekle"""
        async with httpx.AsyncClient() as client:
            start_time = asyncio.get_event_loop().time()
            
            while True:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > timeout:
                    print("Captcha solve timeout")
                    return None
                
                await asyncio.sleep(5)  # 5 saniye bekle
                
                params = {
                    "key": self.api_key,
                    "action": "get",
                    "id": task_id,
                    "json": 1
                }
                
                response = await client.get(f"{self.base_url}/res.php", params=params)
                data = response.json()
                
                if data.get("status") == 1:
                    return data.get("request")
                elif data.get("request") == "CAPCHA_NOT_READY":
                    continue
                else:
                    print(f"2Captcha error: {data}")
                    return None
    
    async def _inject_token(self, page: Page, token: str):
        """Token'ı sayfaya enjekte et"""
        try:
            # Turnstile callback'i çağır
            await page.evaluate(f"""
                (token) => {{
                    // Turnstile input alanını bul ve doldur
                    const input = document.querySelector('[name="cf-turnstile-response"]');
                    if (input) {{
                        input.value = token;
                    }}
                    
                    // Callback fonksiyonunu çağır
                    if (typeof window.turnstileCallback === 'function') {{
                        window.turnstileCallback(token);
                    }}
                    
                    // Form varsa gönder
                    const form = document.querySelector('form');
                    if (form && form.querySelector('[name="cf-turnstile-response"]')) {{
                        // Form otomatik submit edilebilir
                    }}
                }}
            """, token)
        except Exception as e:
            print(f"Token injection error: {e}")
    
    async def get_balance(self) -> Optional[float]:
        """2Captcha bakiyesini kontrol et"""
        try:
            async with httpx.AsyncClient() as client:
                params = {
                    "key": self.api_key,
                    "action": "getbalance",
                    "json": 1
                }
                
                response = await client.get(f"{self.base_url}/res.php", params=params)
                data = response.json()
                
                if data.get("status") == 1:
                    return float(data.get("request", 0))
                return None
        except Exception as e:
            print(f"Balance check error: {e}")
            return None
    
    async def check_api_key(self) -> bool:
        """API key'in geçerli olup olmadığını kontrol et"""
        balance = await self.get_balance()
        return balance is not None and balance > 0

    async def detect_turnstile(self, page: Page) -> Optional[str]:
        """Sayfada Turnstile captcha olup olmadığını kontrol et ve site key'i döndür"""
        try:
            # Turnstile iframe'ini ara
            turnstile_frame = await page.query_selector('iframe[src*="challenges.cloudflare.com"]')
            if turnstile_frame:
                # Site key'i bul
                site_key = await page.evaluate("""
                    () => {
                        const widget = document.querySelector('[data-sitekey]');
                        if (widget) return widget.getAttribute('data-sitekey');
                        
                        const script = document.querySelector('script[data-sitekey]');
                        if (script) return script.getAttribute('data-sitekey');
                        
                        // Turnstile container'dan al
                        const container = document.querySelector('.cf-turnstile');
                        if (container) return container.getAttribute('data-sitekey');
                        
                        return null;
                    }
                """)
                return site_key
            return None
        except Exception as e:
            print(f"Turnstile detection error: {e}")
            return None
