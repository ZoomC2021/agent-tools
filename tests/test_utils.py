"""Tests for utility functions and helper scripts."""

from datetime import date
import sys
import os
import tempfile
import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import parse_date


def _load_opencode_gemini_review_module():
    script_path = Path(__file__).resolve().parent.parent / "prompts" / "opencode" / "bin" / "opencode-gemini-review"
    loader = SourceFileLoader("opencode_gemini_review", str(script_path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


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


def test_opencode_gemini_review_build_chunks_respects_file_boundaries():
    """Large files should get their own chunk; smaller files should pack together."""
    module = _load_opencode_gemini_review_module()
    chunks = module.build_chunks(
        [
            {"path": "a.py", "diff_bytes": b"a" * 20, "size_bytes": 20},
            {"path": "b.py", "diff_bytes": b"b" * 40, "size_bytes": 40},
            {"path": "c.py", "diff_bytes": b"c" * 90, "size_bytes": 90},
            {"path": "d.py", "diff_bytes": b"d" * 10, "size_bytes": 10},
        ],
        chunk_bytes=50,
    )

    assert [chunk["files"] for chunk in chunks] == [["a.py"], ["b.py"], ["c.py"], ["d.py"]]
    assert [chunk["size_bytes"] for chunk in chunks] == [20, 40, 90, 10]


def test_opencode_gemini_review_build_chunks_groups_small_files():
    """Small file diffs should share a chunk until the size threshold is reached."""
    module = _load_opencode_gemini_review_module()
    chunks = module.build_chunks(
        [
            {"path": "a.py", "diff_bytes": b"a" * 20, "size_bytes": 20},
            {"path": "b.py", "diff_bytes": b"b" * 20, "size_bytes": 20},
            {"path": "c.py", "diff_bytes": b"c" * 15, "size_bytes": 15},
        ],
        chunk_bytes=50,
    )

    assert [chunk["files"] for chunk in chunks] == [["a.py", "b.py"], ["c.py"]]
    assert [chunk["size_bytes"] for chunk in chunks] == [40, 15]


def test_opencode_gemini_review_classify_failure_cases():
    """Common Gemini CLI error shapes should map to stable failure reasons."""
    module = _load_opencode_gemini_review_module()

    assert module.classify_failure("Please run gemini login first", False) == "auth"
    assert module.classify_failure("Model is unavailable for this account", False) == "model_unavailable"
    assert module.classify_failure("quota exceeded / rate limit hit", False) == "rate_limited"
    assert module.classify_failure("gemini: command not found", False) == "missing_cli"
    assert module.classify_failure("anything", True) == "timeout"
    assert module.classify_failure("internal server error: 500", False) == "command_failed"


def test_opencode_gemini_review_git_output_handles_missing_git():
    """git_output should return a clear RuntimeError when git is unavailable."""
    module = _load_opencode_gemini_review_module()
    original_run = module.subprocess.run

    def _missing_git(*args, **kwargs):  # noqa: ANN002, ANN003
        raise FileNotFoundError("git")

    module.subprocess.run = _missing_git
    try:
        try:
            module.git_output(Path("."), ["status"], text=True)
            assert False, "Expected RuntimeError"
        except RuntimeError as exc:
            assert "git command not found" in str(exc)
    finally:
        module.subprocess.run = original_run


def test_opencode_gemini_review_run_gemini_uses_subprocess_timeout_only():
    """run_gemini should avoid unsupported CLI timeout flags."""
    module = _load_opencode_gemini_review_module()
    original_run = module.subprocess.run
    observed: dict[str, object] = {}

    class _Completed:
        returncode = 0
        stdout = b"ok"
        stderr = b""

    def _fake_run(cmd, **kwargs):  # noqa: ANN001, ANN003
        observed["cmd"] = cmd
        observed["timeout"] = kwargs.get("timeout")
        return _Completed()

    module.subprocess.run = _fake_run
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            stdout_path = Path(temp_dir) / "stdout.txt"
            stderr_path = Path(temp_dir) / "stderr.txt"
            result = module.run_gemini(
                "gemini",
                "gemini-3.1-pro-preview",
                "prompt text",
                120,
                b"diff",
                stdout_path,
                stderr_path,
            )
    finally:
        module.subprocess.run = original_run

    cmd = observed.get("cmd", [])
    assert "--timeout" not in cmd
    assert observed.get("timeout") == 135
    assert result["success"] is True


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
        test_opencode_gemini_review_build_chunks_respects_file_boundaries,
        test_opencode_gemini_review_build_chunks_groups_small_files,
        test_opencode_gemini_review_classify_failure_cases,
        test_opencode_gemini_review_git_output_handles_missing_git,
        test_opencode_gemini_review_run_gemini_uses_subprocess_timeout_only,
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
