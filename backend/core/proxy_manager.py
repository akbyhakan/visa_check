import asyncio
import httpx
from typing import Optional, Dict, List
from dataclasses import dataclass, field
import random

@dataclass
class Proxy:
    """Proxy bilgisi"""
    host: str
    port: int
    username: str
    password: str
    
    def to_dict(self) -> Dict:
        return {
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "password": self.password
        }
    
    def to_url(self) -> str:
        return f"http://{self.username}:{self.password}@{self.host}:{self.port}"
    
    def __str__(self) -> str:
        return f"{self.host}:{self.port}"


class ProxyManager:
    """Webshare proxy yönetimi ve rotasyonu"""
    
    def __init__(self, api_url: str):
        self.api_url = api_url
        self.proxies: List[Proxy] = []
        self.country_proxy_index: Dict[str, int] = {}
        self.used_proxies: Dict[str, List[str]] = {}
    
    async def fetch_proxies(self) -> bool:
        """Webshare'den proxy listesini çek"""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(self.api_url)
                
                if response.status_code != 200:
                    print(f"Proxy fetch failed: {response.status_code}")
                    return False
                
                self.proxies = []
                lines = response.text.strip().split("\n")
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    parts = line.split(":")
                    if len(parts) >= 4:
                        proxy = Proxy(
                            host=parts[0],
                            port=int(parts[1]),
                            username=parts[2],
                            password=parts[3]
                        )
                        self.proxies.append(proxy)
                
                print(f"Fetched {len(self.proxies)} proxies")
                return len(self.proxies) > 0
                
        except Exception as e:
            print(f"Proxy fetch error: {e}")
            return False
    
    def get_proxy_for_country(self, country_code: str) -> Optional[Proxy]:
        """Belirli bir ülke için proxy al"""
        if not self.proxies:
            return None
        
        if country_code not in self.country_proxy_index:
            country_codes = ["fra", "dnk", "hrv", "cze", "nld", "lux", "bel", "swe", "ltu", "fin", "bgr"]
            try:
                offset = country_codes.index(country_code)
            except ValueError:
                offset = 0
            
            self.country_proxy_index[country_code] = offset % len(self.proxies)
            self.used_proxies[country_code] = []
        
        index = self.country_proxy_index[country_code]
        proxy = self.proxies[index]
        
        return proxy
    
    def rotate_proxy_for_country(self, country_code: str) -> Optional[Proxy]:
        """Ülke için proxy döndür"""
        if not self.proxies:
            return None
        
        if country_code not in self.country_proxy_index:
            return self.get_proxy_for_country(country_code)
        
        current_index = self.country_proxy_index[country_code]
        current_proxy = self.proxies[current_index]
        
        if country_code not in self.used_proxies:
            self.used_proxies[country_code] = []
        
        self.used_proxies[country_code].append(str(current_proxy))
        
        next_index = (current_index + 1) % len(self.proxies)
        self.country_proxy_index[country_code] = next_index
        
        return self.proxies[next_index]
    
    def get_proxy_count(self) -> int:
        return len(self.proxies)
    
    def get_current_proxy_info(self, country_code: str) -> Optional[str]:
        proxy = self.get_proxy_for_country(country_code)
        if proxy:
            return f"{proxy.host}:{proxy.port}"
        return None
    
    async def test_proxy(self, proxy: Proxy) -> bool:
        try:
            async with httpx.AsyncClient(proxy=proxy.to_url(), timeout=10) as client:
                response = await client.get("https://api.ipify.org?format=json")
                if response.status_code == 200:
                    return True
                return False
        except Exception as e:
            print(f"Proxy test failed for {proxy}: {e}")
            return False
    
    async def test_random_proxy(self) -> bool:
        if not self.proxies:
            await self.fetch_proxies()
        
        if not self.proxies:
            return False
        
        proxy = random.choice(self.proxies)
        return await self.test_proxy(proxy)
    
    def reset_country_rotation(self, country_code: str):
        if country_code in self.country_proxy_index:
            del self.country_proxy_index[country_code]
        if country_code in self.used_proxies:
            del self.used_proxies[country_code]
    
    def reset_all_rotations(self):
        self.country_proxy_index = {}
        self.used_proxies = {}
    
    def get_stats(self) -> Dict:
        return {
            "total_proxies": len(self.proxies),
            "country_assignments": {
                code: {
                    "current_index": idx,
                    "current_proxy": str(self.proxies[idx]) if self.proxies else None,
                    "used_count": len(self.used_proxies.get(code, []))
                }
                for code, idx in self.country_proxy_index.items()
            }
        }
