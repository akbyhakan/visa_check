import asyncio
from typing import Optional, Dict, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

class ScanStatus(str, Enum):
    """Tarama durumları"""
    IDLE = "idle"
    CHECKING = "checking"
    WAITING_LOGIN = "waiting_login"
    LOGGING_IN = "logging_in"
    WAITING_OTP = "waiting_otp"
    SCANNING = "scanning"
    PAUSED = "paused"
    ERROR = "error"
    COMPLETED = "completed"


@dataclass
class CountrySession:
    """Ülke oturum bilgisi"""
    country_code: str
    status: ScanStatus = ScanStatus.IDLE
    current_round: int = 0
    total_rounds: int = 5
    current_combination: int = 0
    total_combinations: int = 0
    combinations: List[Dict] = field(default_factory=list)
    current_proxy: Optional[str] = None
    start_time: Optional[datetime] = None
    last_update: Optional[datetime] = None
    error_message: Optional[str] = None
    appointments_found: int = 0
    total_checks: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "country_code": self.country_code,
            "status": self.status.value,
            "current_round": self.current_round,
            "total_rounds": self.total_rounds,
            "current_combination": self.current_combination,
            "total_combinations": self.total_combinations,
            "current_proxy": self.current_proxy,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "error_message": self.error_message,
            "appointments_found": self.appointments_found,
            "total_checks": self.total_checks
        }


class SessionManager:
    """Oturum yönetimi - paralel tarama kontrolü"""
    
    def __init__(self, max_parallel: int = 3):
        self.max_parallel = max_parallel
        self.sessions: Dict[str, CountrySession] = {}
        self.login_queue: asyncio.Queue = asyncio.Queue()
        self.login_lock: asyncio.Lock = asyncio.Lock()
        self._login_in_progress: bool = False
    
    def get_session(self, country_code: str) -> CountrySession:
        if country_code not in self.sessions:
            self.sessions[country_code] = CountrySession(country_code=country_code)
        return self.sessions[country_code]
    
    def get_active_count(self) -> int:
        active_statuses = [
            ScanStatus.CHECKING,
            ScanStatus.WAITING_LOGIN,
            ScanStatus.LOGGING_IN,
            ScanStatus.WAITING_OTP,
            ScanStatus.SCANNING
        ]
        return sum(1 for s in self.sessions.values() if s.status in active_statuses)
    
    def can_start_scan(self) -> bool:
        return self.get_active_count() < self.max_parallel
    
    def get_active_countries(self) -> List[str]:
        active_statuses = [
            ScanStatus.CHECKING,
            ScanStatus.WAITING_LOGIN,
            ScanStatus.LOGGING_IN,
            ScanStatus.WAITING_OTP,
            ScanStatus.SCANNING
        ]
        return [code for code, s in self.sessions.items() if s.status in active_statuses]
    
    async def request_login(self, country_code: str) -> bool:
        session = self.get_session(country_code)
        session.status = ScanStatus.WAITING_LOGIN
        session.last_update = datetime.now()
        
        async with self.login_lock:
            session.status = ScanStatus.LOGGING_IN
            session.last_update = datetime.now()
            return True
    
    def release_login(self, country_code: str):
        session = self.get_session(country_code)
        if session.status == ScanStatus.LOGGING_IN:
            session.status = ScanStatus.SCANNING
            session.last_update = datetime.now()
    
    def update_session_status(self, country_code: str, status: ScanStatus, error: Optional[str] = None):
        session = self.get_session(country_code)
        session.status = status
        session.last_update = datetime.now()
        if error:
            session.error_message = error
    
    def update_scan_progress(self, country_code: str, round_num: int, combination_num: int, total_combinations: int):
        session = self.get_session(country_code)
        session.current_round = round_num
        session.current_combination = combination_num
        session.total_combinations = total_combinations
        session.total_checks += 1
        session.last_update = datetime.now()
    
    def set_combinations(self, country_code: str, combinations: List[Dict]):
        session = self.get_session(country_code)
        session.combinations = combinations
        session.total_combinations = len(combinations)
    
    def record_appointment_found(self, country_code: str):
        session = self.get_session(country_code)
        session.appointments_found += 1
        session.last_update = datetime.now()
    
    def start_session(self, country_code: str, proxy: Optional[str] = None):
        session = self.get_session(country_code)
        session.status = ScanStatus.CHECKING
        session.start_time = datetime.now()
        session.last_update = datetime.now()
        session.current_round = 0
        session.current_combination = 0
        session.error_message = None
        session.current_proxy = proxy
    
    def stop_session(self, country_code: str):
        session = self.get_session(country_code)
        session.status = ScanStatus.IDLE
        session.last_update = datetime.now()
    
    def reset_session(self, country_code: str):
        if country_code in self.sessions:
            del self.sessions[country_code]
    
    def get_all_sessions_status(self) -> Dict:
        return {
            "max_parallel": self.max_parallel,
            "active_count": self.get_active_count(),
            "can_start_new": self.can_start_scan(),
            "sessions": {code: session.to_dict() for code, session in self.sessions.items()}
        }
    
    def get_stats(self) -> Dict:
        total_appointments = sum(s.appointments_found for s in self.sessions.values())
        total_checks = sum(s.total_checks for s in self.sessions.values())
        
        return {
            "active_scans": self.get_active_count(),
            "max_parallel": self.max_parallel,
            "total_appointments_found": total_appointments,
            "total_checks": total_checks,
            "active_countries": self.get_active_countries()
        }


session_manager = SessionManager(max_parallel=3)
