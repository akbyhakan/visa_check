"""
VFS Visa Checker - Ana FastAPI Uygulaması
"""

import asyncio
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.config import settings
from backend.core.browser import BrowserManager
from backend.auth.login import VFSLogin
from backend.auth.otp_handler import OTPHandler
from backend.scanner.appointment_scanner import AppointmentScanner
from backend.notifications.notifier import Notifier
from backend.health.health_check import HealthChecker


browser_manager: Optional[BrowserManager] = None
scanner: Optional[AppointmentScanner] = None
notifier: Optional[Notifier] = None
health_checker: Optional[HealthChecker] = None
active_websockets: list[WebSocket] = []
is_scanning = False


class ScanConfig(BaseModel):
    email: str
    password: str
    country_code: str = "tur"
    mission_code: str = "ita"
    visa_category: str = "stv"
    visa_subcategory: str = "tourism"
    center_code: str = "IST"
    check_interval: int = 30


class OTPSubmit(BaseModel):
    otp_code: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    global health_checker, notifier
    health_checker = HealthChecker()
    notifier = Notifier()
    print("VFS Visa Checker started")
    yield
    if browser_manager:
        await browser_manager.close()
    print("VFS Visa Checker stopped")


app = FastAPI(
    title="VFS Visa Checker",
    description="VFS Global vize randevu kontrol sistemi",
    version="1.0.0",
    lifespan=lifespan
)

app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/")
async def root():
    return FileResponse("frontend/index.html")


@app.get("/api/health")
async def health():
    if health_checker:
        await health_checker.check_all()
        return health_checker.get_summary()
    return {"status": "unknown"}


@app.get("/api/status")
async def status():
    return {
        "is_scanning": is_scanning,
        "active_connections": len(active_websockets),
        "browser_active": browser_manager is not None,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/scan/start")
async def start_scan(config: ScanConfig, background_tasks: BackgroundTasks):
    global is_scanning, browser_manager, scanner
    if is_scanning:
        raise HTTPException(status_code=400, detail="Scan already running")
    is_scanning = True
    browser_manager = BrowserManager()
    scanner = AppointmentScanner(browser_manager=browser_manager, config=config.model_dump())
    background_tasks.add_task(run_scanner, config)
    await broadcast_log("info", "Scan started")
    return {"status": "started"}


async def run_scanner(config: ScanConfig):
    global is_scanning, browser_manager
    try:
        await browser_manager.start()
        login = VFSLogin(browser_manager)
        otp_handler = OTPHandler()
        await broadcast_log("info", "Logging in to VFS...")
        login_result = await login.login(config.email, config.password)
        if login_result.get("needs_otp"):
            await broadcast_log("warning", "OTP required")
            await broadcast_message("otp_required", {})
            otp_code = await otp_handler.wait_for_otp(timeout=300)
            if otp_code:
                await login.submit_otp(otp_code)
        await broadcast_log("success", "Login successful")
        check_count = 0
        while is_scanning:
            check_count += 1
            await broadcast_log("info", f"Check #{check_count}")
            result = await scanner.check_availability()
            if result.get("available"):
                await broadcast_log("success", f"APPOINTMENT FOUND: {result.get('date')}")
                await broadcast_message("appointment_found", result)
                if notifier:
                    await notifier.send_all(f"VFS Appointment Found! Date: {result.get('date')}")
            await broadcast_message("stats_update", {"check_count": check_count})
            await asyncio.sleep(config.check_interval)
    except Exception as e:
        await broadcast_log("error", str(e))
    finally:
        is_scanning = False
        if browser_manager:
            await browser_manager.close()
            browser_manager = None


@app.post("/api/scan/stop")
async def stop_scan():
    global is_scanning
    if not is_scanning:
        raise HTTPException(status_code=400, detail="Scan not running")
    is_scanning = False
    await broadcast_log("info", "Scan stopped")
    return {"status": "stopped"}


@app.post("/api/otp/submit")
async def submit_otp(data: OTPSubmit):
    otp_handler = OTPHandler()
    otp_handler.set_otp(data.otp_code)
    return {"status": "received"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_websockets.append(websocket)
    await websocket.send_json({"type": "connected", "timestamp": datetime.now().isoformat()})
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        active_websockets.remove(websocket)


async def broadcast_message(msg_type: str, data: dict):
    message = {"type": msg_type, "data": data, "timestamp": datetime.now().isoformat()}
    for ws in active_websockets:
        try:
            await ws.send_json(message)
        except:
            pass


async def broadcast_log(level: str, message: str):
    await broadcast_message("log", {"level": level, "message": message})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
