"""
Date normalization utility.

Converts date strings in any format found in complaint text into
Python datetime.date objects safe for PostgreSQL Date columns.

If parsing fails, returns None — the calling code logs a warning
and leaves the DB column as NULL rather than crashing.
"""

import re
from datetime import date, datetime
from typing import Optional


# Ordered list of date format patterns to try
_DATE_FORMATS = [
    "%Y-%m-%d",          # 2026-01-15  (ISO standard — try first)
    "%d-%m-%Y",          # 15-01-2026
    "%m/%d/%Y",          # 01/15/2026  (US format)
    "%d/%m/%Y",          # 15/01/2026  (EU format)
    "%d %B %Y",          # 15 January 2026
    "%B %d, %Y",         # January 15, 2026
    "%b %d, %Y",         # Jan 15, 2026
    "%d %b %Y",          # 15 Jan 2026
    "%B %Y",             # January 2026  (no day — use 1st)
    "%b %Y",             # Jan 2026       (no day — use 1st)
    "%m/%Y",             # 01/2026        (no day — use 1st)
    "%Y/%m/%d",          # 2026/01/15
    "%d.%m.%Y",          # 15.01.2026
    "%Y.%m.%d",          # 2026.01.15
]


def _strip_ordinal_suffixes(text: str) -> str:
    """Remove ordinal suffixes: 1st → 1, 22nd → 22, 3rd → 3, 4th → 4"""
    return re.sub(r"(\d+)(st|nd|rd|th)\b", r"\1", text, flags=re.IGNORECASE)


def parse_date(raw: Optional[str]) -> Optional[date]:
    """
    Try to parse a raw date string into a Python date object.

    Args:
        raw: A date string in any common format (or None).

    Returns:
        A datetime.date object, or None if parsing fails.
    """
    if not raw:
        return None

    cleaned = _strip_ordinal_suffixes(raw.strip())

    for fmt in _DATE_FORMATS:
        try:
            parsed = datetime.strptime(cleaned, fmt)
            return parsed.date()
        except ValueError:
            continue

    # Final attempt — try Python's dateutil if available
    try:
        from dateutil import parser as dateutil_parser
        return dateutil_parser.parse(cleaned, dayfirst=True).date()
    except Exception:
        pass

    return None  # Could not parse — caller handles gracefully
