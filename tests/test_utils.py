"""Tests for utility functions."""

from datetime import date
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import parse_date


def test_parse_date_ymd_dash():
    """Test YYYY-MM-DD format."""
    result = parse_date("2024-03-15")
    assert result == date(2024, 3, 15)


def test_parse_date_ymd_slash():
    """Test YYYY/MM/DD format."""
    result = parse_date("2024/03/15")
    assert result == date(2024, 3, 15)


def test_parse_date_dmy_dash():
    """Test DD-MM-YYYY format."""
    result = parse_date("15-03-2024")
    assert result == date(2024, 3, 15)


def test_parse_date_dmy_slash():
    """Test DD/MM/YYYY format."""
    result = parse_date("15/03/2024")
    assert result == date(2024, 3, 15)


def test_parse_date_none_returns_default():
    """Test None input returns default."""
    default_date = date(2020, 1, 1)
    result = parse_date(None, default=default_date)
    assert result == default_date


def test_parse_date_empty_string_returns_default():
    """Test empty string input returns default."""
    default_date = date(2020, 1, 1)
    result = parse_date("", default=default_date)
    assert result == default_date


def test_parse_date_whitespace_string_returns_default():
    """Test whitespace-only string returns default."""
    default_date = date(2020, 1, 1)
    result = parse_date("   ", default=default_date)
    assert result == default_date


def test_parse_date_none_no_default():
    """Test None input with no default returns None."""
    result = parse_date(None)
    assert result is None


def test_parse_date_empty_no_default():
    """Test empty input with no default returns None."""
    result = parse_date("")
    assert result is None


def test_parse_date_invalid_raises_valueerror():
    """Test invalid date string raises ValueError."""
    try:
        parse_date("not-a-date")
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "Cannot parse date" in str(e)
        assert "not-a-date" in str(e)


def test_parse_date_invalid_format_raises_valueerror():
    """Test valid but unsupported format raises ValueError."""
    try:
        parse_date("03-15-2024")  # MM-DD-YYYY is not supported
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "Cannot parse date" in str(e)


def test_parse_date_strips_whitespace():
    """Test that leading/trailing whitespace is stripped."""
    result = parse_date("  2024-03-15  ")
    assert result == date(2024, 3, 15)


def test_parse_date_leap_year():
    """Test leap year date parsing."""
    result = parse_date("2024-02-29")
    assert result == date(2024, 2, 29)


def test_parse_date_invalid_date_raises_valueerror():
    """Test invalid calendar date raises ValueError."""
    try:
        parse_date("2023-02-29")  # 2023 is not a leap year
        assert False, "Expected ValueError"
    except ValueError:
        pass  # Expected


if __name__ == "__main__":
    # Run all tests
    tests = [
        test_parse_date_ymd_dash,
        test_parse_date_ymd_slash,
        test_parse_date_dmy_dash,
        test_parse_date_dmy_slash,
        test_parse_date_none_returns_default,
        test_parse_date_empty_string_returns_default,
        test_parse_date_whitespace_string_returns_default,
        test_parse_date_none_no_default,
        test_parse_date_empty_no_default,
        test_parse_date_invalid_raises_valueerror,
        test_parse_date_invalid_format_raises_valueerror,
        test_parse_date_strips_whitespace,
        test_parse_date_leap_year,
        test_parse_date_invalid_date_raises_valueerror,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            print(f"✓ {test.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__}: {type(e).__name__}: {e}")
            failed += 1

    print(f"\n{passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
