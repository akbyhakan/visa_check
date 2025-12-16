import json
import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel
from pydantic_settings import BaseSettings

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SCREENSHOTS_DIR = DATA_DIR / "screenshots"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
SCREENSHOTS_DIR.mkdir(exist_ok=True)

# Country configurations
COUNTRIES = {
    "fra": {"name": "Fransa", "flag": "🇫🇷", "url": "https://visa.vfsglobal.com/tur/tr/fra/login"},
    "dnk": {"name": "Danimarka", "flag": "🇩🇰", "url": "https://visa.vfsglobal.com/tur/tr/dnk/login"},
    "hrv": {"name": "Hırvatistan", "flag": "🇭🇷", "url": "https://visa.vfsglobal.com/tur/tr/hrv/login"},
    "cze": {"name": "Çek Cumhuriyeti", "flag": "🇨🇿", "url": "https://visa.vfsglobal.com/tur/tr/cze/login"},
    "nld": {"name": "Hollanda", "flag": "🇳🇱", "url": "https://visa.vfsglobal.com/tur/tr/nld/login"},
    "lux": {"name": "Lüksemburg", "flag": "🇱🇺", "url": "https://visa.vfsglobal.com/tur/tr/lux/login"},
    "bel": {"name": "Belçika", "flag": "🇧🇪", "url": "https://visa.vfsglobal.com/tur/tr/bel/login"},
    "swe": {"name": "İsveç", "flag": "🇸🇪", "url": "https://visa.vfsglobal.com/tur/en/swe/login"},
    "ltu": {"name": "Litvanya", "flag": "🇱🇹", "url": "https://visa.vfsglobal.com/tur/tr/ltu/apply-visa"},
    "fin": {"name": "Finlandiya", "flag": "🇫🇮", "url": "https://visa.vfsglobal.com/tur/tr/fin/login"},
    "bgr": {"name": "Bulgaristan", "flag": "🇧🇬", "url": "https://visa.vfsglobal.com/tur/tr/bgr/login"},
}

# Maximum parallel scans
MAX_PARALLEL_SCANS = 3

# Scan settings
SCAN_ROUNDS_PER_SESSION = 5
SPINNER_TIMEOUT = 30
OTP_TIMEOUT = 120
CLOUDFLARE_TIMEOUT = 60

class Settings(BaseModel):
    # VFS Login
    vfs_email: str = "akby.hakan@gmail.com"
    vfs_password: str = "ha2302AK*"
    
    # IMAP Settings
    imap_email: str = "akby.hakan@gmail.com"
    imap_password: str = "lnao pgsn gmlx ibot"
    imap_server: str = "imap.gmail.com"
    imap_port: int = 993
    
    # 2Captcha
    captcha_api_key: str = "dd22eca10ee02b8bfcb0a991ea2099dd"
    
    # Telegram
    telegram_bot_token: str = "8284487321:AAGZLKbsViNhRBNzW0GTHYKFnxrrfpylxog"
    telegram_chat_id: str = "8241126839"
    
    # Webshare Proxy
    proxy_api_url: str = "https://proxy.webshare.io/api/v2/proxy/list/download/rwunsfncbvmnsaqoleyvfofizzvqusveyayualgk/-/any/username/backbone/-/?plan_id=12421920"
    
    # Webhook
    webhook_host: str = "0.0.0.0"
    webhook_port: int = 8000

CONFIG_FILE = DATA_DIR / "config.json"

def load_settings() -> Settings:
    """Load settings from config file or return defaults"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return Settings(**data)
        except Exception as e:
            print(f"Error loading config: {e}")
    return Settings()

def save_settings(settings: Settings) -> bool:
    """Save settings to config file"""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(settings.model_dump(), f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False

# Global settings instance
settings = load_settings()
