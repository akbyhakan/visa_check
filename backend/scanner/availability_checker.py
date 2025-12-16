"""
Availability Checker - Randevu müsaitlik kontrolü
"""

import asyncio
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass, field
from playwright.async_api import Page


@dataclass
class DateSlot:
    date: str
    day_name: str = ""
    slots: List[str] = field(default_factory=list)
    is_preferred: bool = False


@dataclass
class AvailabilityResult:
    has_availability: bool
    available_dates: List[DateSlot] = field(default_factory=list)
    checked_at: datetime = field(default_factory=datetime.now)
    location: str = ""
    category: str = ""
    error: Optional[str] = None
    
    @property
    def total_slots(self) -> int:
        return sum(len(d.slots) for d in self.available_dates)
    
    @property
    def earliest_date(self) -> Optional[str]:
        return self.available_dates[0].date if self.available_dates else None


class AvailabilityChecker:
    """VFS Global randevu müsaitlik kontrolcüsü"""
    
    SELECTORS = {
        "calendar": ".calendar, .date-picker, [data-testid='calendar']",
        "available_day": "td.available, .day-available, td:not(.disabled)",
        "next_month": ".next-month, .calendar-next, button:has-text('>')",
        "slot_available": ".slot-available, .time-available",
    }
    
    DAY_NAMES_TR = {
        0: "Pazartesi", 1: "Salı", 2: "Çarşamba",
        3: "Perşembe", 4: "Cuma", 5: "Cumartesi", 6: "Pazar"
    }
    
    def __init__(self, preferred_dates: List[str] = None, preferred_days: List[str] = None):
        self.preferred_dates = preferred_dates or []
        self.preferred_days = preferred_days or []
        self.last_result: Optional[AvailabilityResult] = None
    
    async def check(self, page: Page, location: str = "", category: str = "") -> AvailabilityResult:
        try:
            if await self._check_no_availability(page):
                return AvailabilityResult(has_availability=False, location=location, category=category)
            
            available_dates = await self._collect_available_dates(page)
            
            for date_slot in available_dates:
                date_slot.is_preferred = self._is_preferred_date(date_slot)
            
            result = AvailabilityResult(
                has_availability=len(available_dates) > 0,
                available_dates=available_dates,
                location=location,
                category=category
            )
            self.last_result = result
            return result
        except Exception as e:
            return AvailabilityResult(has_availability=False, location=location, error=str(e))
    
    async def _check_no_availability(self, page: Page) -> bool:
        no_texts = ["no appointment", "müsait randevu", "unavailable", "dolu"]
        try:
            body = await page.inner_text("body")
            return any(t in body.lower() for t in no_texts)
        except:
            return False
    
    async def _collect_available_dates(self, page: Page) -> List[DateSlot]:
        dates = []
        try:
            days = await page.query_selector_all(self.SELECTORS["available_day"])
            for day in days:
                try:
                    date_attr = await day.get_attribute("data-date")
                    date_text = await day.text_content()
                    date_str = date_attr or (date_text.strip() if date_text else "")
                    if date_str:
                        day_name = ""
                        try:
                            dt = datetime.strptime(date_str, "%Y-%m-%d")
                            day_name = self.DAY_NAMES_TR.get(dt.weekday(), "")
                        except:
                            pass
                        dates.append(DateSlot(date=date_str, day_name=day_name))
                except:
                    continue
        except:
            pass
        return dates
    
    def _is_preferred_date(self, date_slot: DateSlot) -> bool:
        if self.preferred_dates and date_slot.date in self.preferred_dates:
            return True
        if self.preferred_days and date_slot.day_name in self.preferred_days:
            return True
        return not self.preferred_dates and not self.preferred_days
    
    async def check_multiple_months(self, page: Page, months: int = 2) -> AvailabilityResult:
        all_dates = []
        for i in range(months):
            result = await self.check(page)
            all_dates.extend(result.available_dates)
            if i < months - 1:
                next_btn = await page.query_selector(self.SELECTORS["next_month"])
                if next_btn:
                    await next_btn.click()
                    await asyncio.sleep(1)
        return AvailabilityResult(has_availability=len(all_dates) > 0, available_dates=all_dates)
    
    def format_message(self, result: AvailabilityResult) -> str:
        if not result.has_availability:
            return f"❌ {result.location} için müsait randevu yok."
        lines = [f"✅ {result.location} - {len(result.available_dates)} tarih:"]
        for d in result.available_dates[:10]:
            star = "⭐" if d.is_preferred else ""
            lines.append(f"  • {d.date} {d.day_name} {star}")
        return "\n".join(lines)
