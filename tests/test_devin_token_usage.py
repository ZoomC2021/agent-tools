"""Tests for scripts/devin-token-usage.py.

Uses temporary directories with fixture JSON/NDJSON files and an in-memory
SQLite database to verify the loading, merging, and cost-calculation logic
without touching real Devin data.
"""

import importlib.util
import json
import os
import sqlite3
import sys
import tempfile
from importlib.machinery import SourceFileLoader
from pathlib import Path

# Load the script as a module (hyphen in filename prevents normal import)
_script_path = Path(__file__).resolve().parent.parent / "scripts" / "devin-token-usage.py"
_loader = SourceFileLoader("devin_token_usage", str(_script_path))
_spec = importlib.util.spec_from_loader(_loader.name, _loader)
dtu = importlib.util.module_from_spec(_spec)
sys.modules["devin_token_usage"] = dtu
assert _spec.loader is not None
_spec.loader.exec_module(dtu)


def _write_transcript(path: Path, session_id: str, model_name: str,
                      prompt: int, completion: int, cached: int, steps: int = 5):
    """Write a minimal CLI transcript JSON file."""
    path.write_text(json.dumps({
        "schema_version": "ATIF-v1.7",
        "session_id": session_id,
        "agent": {"name": "devin", "model_name": model_name},
        "steps": [],
        "final_metrics": {
            "total_prompt_tokens": prompt,
            "total_completion_tokens": completion,
            "total_cached_tokens": cached,
            "total_steps": steps,
        },
    }))


def _write_acp_file(path: Path, title: str, usage_updates: list[tuple[int, int, int]]):
    """Write a minimal ACP NDJSON file with usage_update events.

    Each tuple in ``usage_updates`` is (input, output, cached).
    """
    lines = []
    if title:
        lines.append(json.dumps({
            "providerId": "devin-cli",
            "notification": {"title": title, "sessionUpdate": "session_info_update"},
        }))
    for inp, out, cache in usage_updates:
        lines.append(json.dumps({
            "providerId": "devin-cli",
            "notification": {
                "_meta": {
                    "cognition.ai/inputTokens": inp,
                    "cognition.ai/outputTokens": out,
                    "cognition.ai/cachedReadTokens": cache,
                },
                "sessionUpdate": "usage_update",
            },
        }))
    path.write_text("\n".join(lines) + "\n")


def _create_test_db(path: str, sessions: list[tuple[str, str, str]]):
    """Create a minimal sessions.db with (id, model, title) rows."""
    con = sqlite3.connect(path)
    con.execute("""
        CREATE TABLE sessions (
            id TEXT PRIMARY KEY,
            working_directory TEXT NOT NULL,
            backend_type TEXT NOT NULL,
            model TEXT NOT NULL,
            agent_mode TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            last_activity_at INTEGER NOT NULL,
            title TEXT
        )
    """)
    for sid, model, title in sessions:
        con.execute(
            "INSERT INTO sessions (id, working_directory, backend_type, model, agent_mode, created_at, last_activity_at, title) VALUES (?, '/', 'windsurf', ?, 'bypass', 0, 0, ?)",
            (sid, model, title),
        )
    con.commit()
    con.close()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_load_cli_transcripts_basic():
    """CLI transcripts with final_metrics should be loaded correctly."""
    with tempfile.TemporaryDirectory() as tmp:
        tdir = Path(tmp)
        _write_transcript(tdir / "alpha.json", "alpha", "GLM-5.2",
                          prompt=10000, completion=500, cached=8000)
        _write_transcript(tdir / "beta.json", "beta", "Kimi K2.7",
                          prompt=5000, completion=300, cached=4000)
        result = dtu.load_cli_transcripts(str(tdir))
        assert "alpha" in result
        assert result["alpha"].model == "GLM-5.2"
        assert result["alpha"].prompt == 10000
        assert result["alpha"].completion == 500
        assert result["alpha"].cached == 8000
        assert result["alpha"].source == "cli"
        assert result["beta"].model == "Kimi K2.7"


def test_load_cli_transcripts_skips_missing_metrics():
    """Transcripts without final_metrics should be skipped."""
    with tempfile.TemporaryDirectory() as tmp:
        tdir = Path(tmp)
        (tdir / "empty.json").write_text(json.dumps({"session_id": "empty", "agent": {}}))
        _write_transcript(tdir / "good.json", "good", "GLM-5.2", 100, 10, 50)
        result = dtu.load_cli_transcripts(str(tdir))
        assert "empty" not in result
        assert "good" in result


def test_load_cli_transcripts_skips_invalid_json():
    """Malformed JSON files should be silently skipped."""
    with tempfile.TemporaryDirectory() as tmp:
        tdir = Path(tmp)
        (tdir / "bad.json").write_text("{not valid json")
        result = dtu.load_cli_transcripts(str(tdir))
        assert result == {}


def test_load_acp_events_sums_output():
    """ACP output tokens are per-step and must be summed."""
    with tempfile.TemporaryDirectory() as tmp:
        adir = Path(tmp)
        _write_acp_file(adir / "abc.ndjson", "Test Session", [
            (1000, 100, 900),
            (2000, 200, 1800),
            (3000, 150, 2700),
        ])
        result = dtu.load_acp_events(str(adir))
        assert "abc" in result
        # Input is the last cumulative value
        assert result["abc"].prompt == 3000
        assert result["abc"].cached == 2700
        # Output is the sum of per-step values
        assert result["abc"].completion == 450
        assert result["abc"].source == "acp"


def test_load_acp_events_skips_files_without_usage():
    """ACP files with no usage_update events should be omitted."""
    with tempfile.TemporaryDirectory() as tmp:
        adir = Path(tmp)
        _write_acp_file(adir / "no-usage.ndjson", "Title", [])
        # Also write a file with only a title line
        (adir / "title-only.ndjson").write_text(json.dumps({
            "providerId": "devin-cli",
            "notification": {"title": "X", "sessionUpdate": "session_info_update"},
        }) + "\n")
        result = dtu.load_acp_events(str(adir))
        assert result == {}


def test_load_acp_titles():
    """ACP titles should be extracted from session_info_update events."""
    with tempfile.TemporaryDirectory() as tmp:
        adir = Path(tmp)
        _write_acp_file(adir / "abc.ndjson", "My Session Title", [(100, 10, 90)])
        titles = dtu.load_acp_titles(str(adir))
        assert titles["abc"] == "My Session Title"


def test_load_db_sessions():
    """DB sessions should be loaded into by_id and by_title dicts."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "test.db")
        _create_test_db(db_path, [
            ("alpha", "glm-5-2", "Refactor Code"),
            ("beta", "kimi-k2-7", "Fix Bug"),
        ])
        by_id, by_title = dtu.load_db_sessions(db_path)
        assert by_id["alpha"]["model"] == "glm-5-2"
        assert by_id["alpha"]["title"] == "Refactor Code"
        assert by_title["Fix Bug"]["id"] == "beta"
        assert by_title["Fix Bug"]["model"] == "kimi-k2-7"


def test_load_db_sessions_missing_file():
    """Missing DB file should return empty dicts, not crash."""
    by_id, by_title = dtu.load_db_sessions("/nonexistent/path.db")
    assert by_id == {}
    assert by_title == {}


def test_merge_usage_cli_only():
    """Merge with only CLI sessions should aggregate per-model totals."""
    cli = {
        "s1": dtu.SessionUsage(model="GLM-5.2", prompt=10000, completion=500, cached=8000, source="cli"),
        "s2": dtu.SessionUsage(model="GLM-5.2", prompt=20000, completion=1000, cached=15000, source="cli"),
        "s3": dtu.SessionUsage(model="Kimi K2.7", prompt=5000, completion=300, cached=4000, source="cli"),
    }
    per_model = dtu.merge_usage(cli, {}, {}, {})
    assert per_model["GLM-5.2"].sessions == 2
    assert per_model["GLM-5.2"].prompt == 30000
    assert per_model["GLM-5.2"].completion == 1500
    assert per_model["GLM-5.2"].cached == 23000
    assert per_model["Kimi K2.7"].sessions == 1


def test_merge_usage_acp_resolves_model_via_db():
    """ACP sessions should get their model from DB title matching."""
    cli = {}
    acp = {
        "uuid-1": dtu.SessionUsage(model="unknown", prompt=10000, completion=500, cached=8000, source="acp"),
    }
    acp_titles = {"uuid-1": "Refactor Code"}
    db_by_title = {"Refactor Code": {"id": "db-s1", "model": "glm-5-2"}}
    per_model = dtu.merge_usage(cli, acp, acp_titles, db_by_title)
    assert per_model["GLM-5.2"].sessions == 1
    assert per_model["GLM-5.2"].prompt == 10000


def test_merge_usage_deduplicates_acp_vs_cli():
    """ACP sessions that map to a CLI session should not be double-counted."""
    cli = {
        "db-s1": dtu.SessionUsage(model="GLM-5.2", prompt=10000, completion=500, cached=8000, source="cli"),
    }
    acp = {
        "uuid-1": dtu.SessionUsage(model="unknown", prompt=10000, completion=500, cached=8000, source="acp"),
    }
    acp_titles = {"uuid-1": "Refactor Code"}
    db_by_title = {"Refactor Code": {"id": "db-s1", "model": "glm-5-2"}}
    per_model = dtu.merge_usage(cli, acp, acp_titles, db_by_title)
    assert per_model["GLM-5.2"].sessions == 1  # not 2


def test_merge_usage_acp_defaults_to_glm():
    """ACP sessions without a DB match should default to GLM-5.2."""
    acp = {
        "uuid-1": dtu.SessionUsage(model="unknown", prompt=5000, completion=200, cached=4000, source="acp"),
    }
    per_model = dtu.merge_usage({}, acp, {}, {})
    assert per_model["GLM-5.2"].sessions == 1
    assert per_model["GLM-5.2"].prompt == 5000


def test_model_totals_cost():
    """ModelTotals.cost should compute input/cached/output/total correctly."""
    totals = dtu.ModelTotals(model="GLM-5.2", sessions=3, prompt=1_000_000, completion=100_000, cached=800_000)
    cost = totals.cost(dtu.PRICING)
    # GLM-5.2: in=$1.40, cache=$0.26, out=$4.40
    # uncached = 200_000
    assert abs(cost["input"] - 200_000 / 1e6 * 1.40) < 0.01
    assert abs(cost["cached"] - 800_000 / 1e6 * 0.26) < 0.01
    assert abs(cost["output"] - 100_000 / 1e6 * 4.40) < 0.01
    assert abs(cost["total"] - cost["input"] - cost["cached"] - cost["output"]) < 0.001


def test_compute_report_structure():
    """compute_report should produce a well-structured dict."""
    per_model = {
        "GLM-5.2": dtu.ModelTotals(model="GLM-5.2", sessions=60, prompt=9_000_000, completion=700_000, cached=8_000_000),
        "Kimi K2.7": dtu.ModelTotals(model="Kimi K2.7", sessions=36, prompt=3_700_000, completion=89_000, cached=3_200_000),
    }
    report = dtu.compute_report(per_model)
    assert "GLM-5.2" in report["models"]
    assert "Kimi K2.7" in report["models"]
    assert report["totals"]["sessions"] == 96
    assert report["totals"]["total"] > 0
    assert report["pricing"] == dtu.PRICING


def test_main_text_output():
    """main() with text output should print a report and return 0."""
    with tempfile.TemporaryDirectory() as tmp:
        tdir = Path(tmp)
        _write_transcript(tdir / "s1.json", "s1", "GLM-5.2", 10000, 500, 8000)
        rc = dtu.main(["--transcript-dir", str(tdir), "--no-acp", "--no-db"])
        assert rc == 0


def test_main_json_output():
    """main() with --json should produce valid JSON output."""
    import io
    from contextlib import redirect_stdout
    with tempfile.TemporaryDirectory() as tmp:
        tdir = Path(tmp)
        _write_transcript(tdir / "s1.json", "s1", "GLM-5.2", 10000, 500, 8000)
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = dtu.main(["--transcript-dir", str(tdir), "--no-acp", "--no-db", "--json"])
        assert rc == 0
        data = json.loads(buf.getvalue())
        assert "models" in data
        assert "totals" in data
        assert data["models"]["GLM-5.2"]["sessions"] == 1


def test_main_no_acp_flag():
    """--no-acp should skip ACP processing entirely."""
    import io
    from contextlib import redirect_stdout
    with tempfile.TemporaryDirectory() as tmp:
        tdir = Path(tmp)
        adir = Path(tmp) / "acp"
        adir.mkdir()
        _write_transcript(tdir / "s1.json", "s1", "GLM-5.2", 10000, 500, 8000)
        _write_acp_file(adir / "a1.ndjson", "Title", [(1000, 100, 900)])
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = dtu.main(["--transcript-dir", str(tdir), "--acp-dir", str(adir),
                           "--no-acp", "--no-db", "--json"])
        data = json.loads(buf.getvalue())
        # Only the CLI session should be counted
        assert data["totals"]["sessions"] == 1


# ---------------------------------------------------------------------------
# Date filter tests
# ---------------------------------------------------------------------------

def test_load_cli_transcripts_since_filter():
    """--since filters out transcripts by file mtime."""
    import os
    import time
    with tempfile.TemporaryDirectory() as tmp:
        tdir = Path(tmp)
        _write_transcript(tdir / "old.json", "old", "GLM-5.2", 10000, 500, 8000)
        # Set old.json mtime to 2026-07-10
        old_ts = dtu._date_to_epoch("2026-07-10") + 3600
        os.utime(tdir / "old.json", (old_ts, old_ts))
        _write_transcript(tdir / "new.json", "new", "GLM-5.2", 20000, 1000, 15000)
        # Set new.json mtime to 2026-07-13
        new_ts = dtu._date_to_epoch("2026-07-13") + 3600
        os.utime(tdir / "new.json", (new_ts, new_ts))
        result = dtu.load_cli_transcripts(str(tdir), since="2026-07-13")
        assert "new" in result
        assert "old" not in result


def test_load_cli_transcripts_until_filter():
    """--until filters out transcripts by file mtime."""
    import os
    with tempfile.TemporaryDirectory() as tmp:
        tdir = Path(tmp)
        _write_transcript(tdir / "old.json", "old", "GLM-5.2", 10000, 500, 8000)
        old_ts = dtu._date_to_epoch("2026-07-10") + 3600
        os.utime(tdir / "old.json", (old_ts, old_ts))
        _write_transcript(tdir / "new.json", "new", "GLM-5.2", 20000, 1000, 15000)
        new_ts = dtu._date_to_epoch("2026-07-13") + 3600
        os.utime(tdir / "new.json", (new_ts, new_ts))
        result = dtu.load_cli_transcripts(str(tdir), until="2026-07-10")
        assert "old" in result
        assert "new" not in result


def test_load_acp_events_since_filter():
    """--since filters ACP files by mtime."""
    import os
    with tempfile.TemporaryDirectory() as tmp:
        adir = Path(tmp)
        _write_acp_file(adir / "old.ndjson", "Old", [(1000, 100, 900)])
        old_ts = dtu._date_to_epoch("2026-07-10") + 3600
        os.utime(adir / "old.ndjson", (old_ts, old_ts))
        _write_acp_file(adir / "new.ndjson", "New", [(2000, 200, 1800)])
        new_ts = dtu._date_to_epoch("2026-07-13") + 3600
        os.utime(adir / "new.ndjson", (new_ts, new_ts))
        result = dtu.load_acp_events(str(adir), since="2026-07-13")
        assert "new" in result
        assert "old" not in result


def test_compute_report_includes_date_range():
    """compute_report includes since/until in the report dict."""
    per_model = {
        "GLM-5.2": dtu.ModelTotals(model="GLM-5.2", sessions=1, prompt=1000, completion=100, cached=500),
    }
    report = dtu.compute_report(per_model, since="2026-07-13", until="2026-07-13")
    assert report["since"] == "2026-07-13"
    assert report["until"] == "2026-07-13"


def test_main_since_flag_filters_transcripts():
    """main() with --since filters transcripts by mtime."""
    import io
    import os
    from contextlib import redirect_stdout
    with tempfile.TemporaryDirectory() as tmp:
        tdir = Path(tmp)
        _write_transcript(tdir / "old.json", "old", "GLM-5.2", 10000, 500, 8000)
        old_ts = dtu._date_to_epoch("2026-07-10") + 3600
        os.utime(tdir / "old.json", (old_ts, old_ts))
        _write_transcript(tdir / "new.json", "new", "GLM-5.2", 20000, 1000, 15000)
        new_ts = dtu._date_to_epoch("2026-07-13") + 3600
        os.utime(tdir / "new.json", (new_ts, new_ts))
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = dtu.main(["--transcript-dir", str(tdir), "--no-acp", "--no-db",
                           "--since", "2026-07-13", "--json"])
        assert rc == 0
        data = json.loads(buf.getvalue())
        assert data["totals"]["sessions"] == 1
        assert data["since"] == "2026-07-13"


if __name__ == "__main__":
    tests = [
        test_load_cli_transcripts_basic,
        test_load_cli_transcripts_skips_missing_metrics,
        test_load_cli_transcripts_skips_invalid_json,
        test_load_acp_events_sums_output,
        test_load_acp_events_skips_files_without_usage,
        test_load_acp_titles,
        test_load_db_sessions,
        test_load_db_sessions_missing_file,
        test_merge_usage_cli_only,
        test_merge_usage_acp_resolves_model_via_db,
        test_merge_usage_deduplicates_acp_vs_cli,
        test_merge_usage_acp_defaults_to_glm,
        test_model_totals_cost,
        test_compute_report_structure,
        test_main_text_output,
        test_main_json_output,
        test_main_no_acp_flag,
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
