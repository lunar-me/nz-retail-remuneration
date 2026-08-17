"""New Zealand calendar utilities.

Provides NZ public holidays (national + regional anniversary days), school
term dates, and retail peak-period helpers. These are used by the synthetic
data generators to embed realistic NZ seasonality and by downstream engines
(leave, capacity) for compliance-aware calculations.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# NZ Public Holidays (2024–2026)
# ---------------------------------------------------------------------------
# National public holidays are fixed by the Holidays Act 2003. Regional
# anniversary days vary by region. We encode the observed dates for the
# generation window (2024-07-01 → 2026-06-30).

# (month, day) for fixed-date national holidays
_FIXED_NATIONAL = [
    (1, 1),   # New Year's Day
    (1, 2),   # Day after New Year's Day
    (2, 6),   # Waitangi Day
    (4, 25),  # ANZAC Day
    (12, 25), # Christmas Day
    (12, 26), # Boxing Day
]

# (year, month, day) for moveable national holidays
_MOVEABLE_NATIONAL = {
    2024: [
        (2024, 3, 29),  # Good Friday
        (2024, 4, 1),   # Easter Monday
        (2024, 6, 3),   # King's Birthday
        (2024, 10, 28), # Labour Day
    ],
    2025: [
        (2025, 4, 18),  # Good Friday
        (2025, 4, 21),  # Easter Monday
        (2025, 6, 2),   # King's Birthday
        (2025, 10, 27), # Labour Day
    ],
    2026: [
        (2026, 4, 3),   # Good Friday
        (2026, 4, 6),   # Easter Monday
        (2026, 6, 1),   # King's Birthday
        (2026, 10, 26), # Labour Day
    ],
}

# Regional anniversary days: region name -> (month, day) observed
_REGIONAL_ANNIVERSARY_DAYS: Dict[str, Tuple[int, int]] = {
    "Auckland": (1, 29),       # Auckland Anniversary (Mon nearest 29 Jan)
    "Wellington": (1, 20),      # Wellington Anniversary (Mon nearest 22 Jan)
    "Canterbury": (11, 15),     # Canterbury Anniversary (Fri after 2nd Tue Nov)
    "Waikato": (3, 30),         # Waikato Anniversary (Fri before Easter)
    "Bay of Plenty": (10, 31),  # Bay of Plenty Anniversary (Fri before Labour Day)
}

# Map config region names to anniversary-day region keys
_REGION_TO_ANNIVERSARY_KEY = {
    "Auckland": "Auckland",
    "Wellington": "Wellington",
    "Christchurch": "Canterbury",
    "Hamilton": "Waikato",
    "Tauranga": "Bay of Plenty",
}


@dataclass(frozen=True)
class NZHoliday:
    """A single NZ public holiday occurrence."""

    date: dt.date
    name: str
    region: Optional[str] = None  # None = national holiday


def _monday_on_or_after(anchor: dt.date) -> dt.date:
    """Return the Monday on or after ``anchor``."""
    days_ahead = (0 - anchor.weekday()) % 7
    return anchor + dt.timedelta(days=days_ahead)


def _monday_before_or_on(anchor: dt.date) -> dt.date:
    """Return the Monday on or before ``anchor``."""
    days_back = (anchor.weekday() - 0) % 7
    return anchor - dt.timedelta(days=days_back)


def _friday_before(anchor: dt.date) -> dt.date:
    """Return the Friday before ``anchor`` (strictly before)."""
    days_back = (anchor.weekday() - 4) % 7
    if days_back == 0:
        days_back = 7
    return anchor - dt.timedelta(days=days_back)


def _observed_date(month: int, day: int, year: int) -> dt.date:
    """Return the observed date for a fixed-date holiday.

    NZ law: if the holiday falls on a weekend, it is observed on the
    following Monday (or Tuesday if Monday is itself a holiday).
    """
    date = dt.date(year, month, day)
    if date.weekday() == 5:  # Saturday
        return date + dt.timedelta(days=2)
    if date.weekday() == 6:  # Sunday
        return date + dt.timedelta(days=1)
    return date


def get_national_public_holidays(year: int) -> List[NZHoliday]:
    """Return all national public holidays for a given year (observed dates)."""
    holidays: List[NZHoliday] = []

    # Fixed-date holidays
    for month, day in _FIXED_NATIONAL:
        observed = _observed_date(month, day, year)
        holidays.append(NZHoliday(date=observed, name=_holiday_name(month, day)))

    # Moveable holidays
    for y, m, d in _MOVEABLE_NATIONAL.get(year, []):
        holidays.append(NZHoliday(date=dt.date(y, m, d), name=_moveable_name(y, m, d)))

    return holidays


def _holiday_name(month: int, day: int) -> str:
    names = {
        (1, 1): "New Year's Day",
        (1, 2): "Day after New Year's Day",
        (2, 6): "Waitangi Day",
        (4, 25): "ANZAC Day",
        (12, 25): "Christmas Day",
        (12, 26): "Boxing Day",
    }
    return names.get((month, day), "Public Holiday")


def _moveable_name(year: int, month: int, day: int) -> str:
    names = {
        (3, 29): "Good Friday",
        (4, 1): "Easter Monday",
        (4, 18): "Good Friday",
        (4, 21): "Easter Monday",
        (4, 3): "Good Friday",
        (4, 6): "Easter Monday",
        (6, 3): "King's Birthday",
        (6, 2): "King's Birthday",
        (6, 1): "King's Birthday",
        (10, 28): "Labour Day",
        (10, 27): "Labour Day",
        (10, 26): "Labour Day",
    }
    return names.get((month, day), "Public Holiday")


def get_regional_anniversary_days(year: int, region_key: str) -> Optional[NZHoliday]:
    """Return the regional anniversary day for a region in a given year.

    Parameters
    ----------
    year : int
        The calendar year.
    region_key : str
        One of the keys in ``_REGIONAL_ANNIVERSARY_DAYS``.

    Returns
    -------
    Optional[NZHoliday]
        The observed anniversary day, or ``None`` if the region is unknown.
    """
    if region_key not in _REGIONAL_ANNIVERSARY_DAYS:
        return None

    month, day = _REGIONAL_ANNIVERSARY_DAYS[region_key]
    anchor = dt.date(year, month, day)

    if region_key == "Auckland":
        observed = _monday_on_or_after(anchor)
    elif region_key == "Wellington":
        observed = _monday_on_or_after(anchor)
    elif region_key == "Canterbury":
        # Friday after the second Tuesday in November
        first = dt.date(year, 11, 1)
        first_tue = first + dt.timedelta(days=(1 - first.weekday()) % 7)
        second_tue = first_tue + dt.timedelta(days=7)
        observed = second_tue + dt.timedelta(days=3)  # Friday
    elif region_key == "Waikato":
        # Friday before Easter Sunday (approximate: use Good Friday - 1)
        good_friday = _find_good_friday(year)
        observed = good_friday - dt.timedelta(days=1)
    elif region_key == "Bay of Plenty":
        # Friday before Labour Day (last Monday of October)
        labour_day = _find_labour_day(year)
        observed = labour_day - dt.timedelta(days=3)
    else:
        observed = anchor

    return NZHoliday(date=observed, name=f"{region_key} Anniversary", region=region_key)


def _find_good_friday(year: int) -> dt.date:
    """Return the Good Friday date for a year (from the moveable table)."""
    for y, m, d in _MOVEABLE_NATIONAL.get(year, []):
        if m == 4 and d in (3, 6, 18, 21, 29):
            return dt.date(y, m, d)
    # Fallback: approximate using Easter algorithm (Meeus)
    a = year % 19
    b = year // 100
    c = year % 100
    d = (19 * a + b - b // 4 - ((b - (b + 8) // 25 + 1) // 3) + 15) % 30
    e = (32 + 2 * (b % 4) + 2 * (c // 4) - d - (c % 4)) % 7
    f = d + e - 7 * ((a + 11 * d + 22 * e) // 451) + 114
    month = f // 31
    day = f % 31 + 1
    easter = dt.date(year, month, day)
    return easter - dt.timedelta(days=2)


def _find_labour_day(year: int) -> dt.date:
    """Return the Labour Day date (last Monday of October) for a year."""
    oct_last = dt.date(year, 10, 31)
    return _monday_before_or_on(oct_last)


def get_all_holidays(start: dt.date, end: dt.date, regions: Optional[List[str]] = None) -> List[NZHoliday]:
    """Return all NZ public holidays (national + regional) in a date range.

    Parameters
    ----------
    start : dt.date
        Inclusive start date.
    end : dt.date
        Inclusive end date.
    regions : Optional[List[str]]
        Region names to include regional anniversary days for. If ``None``,
        only national holidays are returned.

    Returns
    -------
    List[NZHoliday]
        Sorted list of holidays.
    """
    holidays: List[NZHoliday] = []
    for year in range(start.year, end.year + 1):
        holidays.extend(get_national_public_holidays(year))

        if regions:
            for region in regions:
                key = _REGION_TO_ANNIVERSARY_KEY.get(region)
                if key:
                    ann = get_regional_anniversary_days(year, key)
                    if ann and start <= ann.date <= end:
                        holidays.append(ann)

    return sorted(holidays, key=lambda h: h.date)


# ---------------------------------------------------------------------------
# School term dates (simplified NZ school year)
# ---------------------------------------------------------------------------
# NZ school year typically runs late January → mid December with four terms.
# These are approximate dates used to model retail demand peaks.

_SCHOOL_TERMS: Dict[int, List[Tuple[dt.date, dt.date]]] = {
    2024: [
        (dt.date(2024, 1, 29), dt.date(2024, 4, 12)),
        (dt.date(2024, 4, 29), dt.date(2024, 7, 5)),
        (dt.date(2024, 7, 22), dt.date(2024, 9, 27)),
        (dt.date(2024, 10, 14), dt.date(2024, 12, 20)),
    ],
    2025: [
        (dt.date(2025, 1, 27), dt.date(2025, 4, 11)),
        (dt.date(2025, 4, 28), dt.date(2025, 7, 4)),
        (dt.date(2025, 7, 21), dt.date(2025, 9, 26)),
        (dt.date(2025, 10, 13), dt.date(2025, 12, 19)),
    ],
    2026: [
        (dt.date(2026, 1, 26), dt.date(2026, 4, 10)),
        (dt.date(2026, 4, 27), dt.date(2026, 7, 3)),
        (dt.date(2026, 7, 20), dt.date(2026, 9, 25)),
        (dt.date(2026, 10, 12), dt.date(2026, 12, 18)),
    ],
}


def is_school_term(date: dt.date) -> bool:
    """Return ``True`` if ``date`` falls within a NZ school term."""
    terms = _SCHOOL_TERMS.get(date.year, [])
    return any(start <= date <= end for start, end in terms)


def get_school_holiday_periods(year: int) -> List[Tuple[dt.date, dt.date]]:
    """Return the school-holiday periods (gaps between terms) for a year."""
    terms = _SCHOOL_TERMS.get(year, [])
    periods: List[Tuple[dt.date, dt.date]] = []
    for i in range(len(terms) - 1):
        gap_start = terms[i][1] + dt.timedelta(days=1)
        gap_end = terms[i + 1][0] - dt.timedelta(days=1)
        if gap_start <= gap_end:
            periods.append((gap_start, gap_end))
    return periods


# ---------------------------------------------------------------------------
# Retail peak periods
# ---------------------------------------------------------------------------
def is_retail_peak(date: dt.date) -> bool:
    """Return ``True`` if ``date`` is in a known NZ retail peak period.

    Peaks: Christmas/New Year (mid-Dec → mid-Jan), Easter, school holidays,
    and long weekends.
    """
    # Christmas / New Year peak
    if (date.month == 12 and date.day >= 15) or (date.month == 1 and date.day <= 15):
        return True

    # School holidays
    if is_school_term(date) is False and date.month not in (1, 12):
        # Outside term time but not summer break → school holiday
        return True

    return False


def build_calendar_frame(
    start: dt.date,
    end: dt.date,
    regions: Optional[List[str]] = None,
) -> List[Dict]:
    """Build a calendar reference table for the generation window.

    Parameters
    ----------
    start : dt.date
        Inclusive start date.
    end : dt.date
        Inclusive end date.
    regions : Optional[List[str]]
        Region names for regional holiday inclusion.

    Returns
    -------
    List[Dict]
        One dict per date with calendar attributes.
    """
    holidays = get_all_holidays(start, end, regions)
    holiday_by_date: Dict[dt.date, NZHoliday] = {h.date: h for h in holidays}

    rows: List[Dict] = []
    current = start
    while current <= end:
        holiday = holiday_by_date.get(current)
        rows.append(
            {
                "date": current,
                "year": current.year,
                "month": current.month,
                "day": current.day,
                "day_of_week": current.weekday(),  # 0=Monday … 6=Sunday
                "is_weekend": current.weekday() >= 5,
                "is_public_holiday": holiday is not None,
                "public_holiday_name": holiday.name if holiday else None,
                "public_holiday_region": holiday.region if holiday else None,
                "is_school_term": is_school_term(current),
                "is_retail_peak": is_retail_peak(current),
            }
        )
        current += dt.timedelta(days=1)

    return rows