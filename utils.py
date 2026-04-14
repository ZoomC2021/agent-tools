"""Utility functions for agent-tools."""

from datetime import date, datetime
from typing import Optional


def parse_date(value: Optional[str], default: Optional[date] = None) -> Optional[date]:
    """Parse a date string using multiple common formats.

    Supported formats:
        - %Y-%m-%d (e.g., "2024-03-15")
        - %Y/%m/%d (e.g., "2024/03/15")
        - %d-%m-%Y (e.g., "15-03-2024")
        - %d/%m/%Y (e.g., "15/03/2024")

    Args:
        value: The date string to parse, or None/empty string.
        default: The value to return if input is None or empty.

    Returns:
        A date object if parsing succeeds, or the default value if input is None/empty.

    Raises:
        ValueError: If the string cannot be parsed with any supported format.

    Examples:
        >>> parse_date("2024-03-15")
        datetime.date(2024, 3, 15)
        >>> parse_date("15/03/2024")
        datetime.date(2024, 3, 15)
        >>> parse_date(None, default=date.today())
        datetime.date(2026, 4, 14)  # or current date
        >>> parse_date("invalid")
        ValueError: Cannot parse date from 'invalid'. Supported formats: YYYY-MM-DD, YYYY/MM/DD, DD-MM-YYYY, DD/MM/YYYY
    """
    if not value or not value.strip():
        return default

    formats = [
        "%Y-%m-%d",  # 2024-03-15
        "%Y/%m/%d",  # 2024/03/15
        "%d-%m-%Y",  # 15-03-2024
        "%d/%m/%Y",  # 15/03/2024
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue

    raise ValueError(
        f"Cannot parse date from '{value}'. "
        f"Supported formats: YYYY-MM-DD, YYYY/MM/DD, DD-MM-YYYY, DD/MM/YYYY"
    )
