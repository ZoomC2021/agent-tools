import hashlib
import importlib.util
import json
from pathlib import Path
import stat

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("render_prompts", ROOT / "scripts/render-prompts.py")
render_prompts = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(render_prompts)


def test_current_manifest_and_render_are_complete(tmp_path):
    aliases = render_prompts.validate()
    rendered = render_prompts.render(tmp_path)
    assert aliases
    for item in aliases:
        source = ROOT / "prompts" / item["source"]
        alias = rendered / item["path"]
        assert alias.read_bytes() == source.read_bytes()
        expected_exec = item["mode"] == "100755"
        assert bool(alias.stat().st_mode & stat.S_IXUSR) == expected_exec


def test_rendered_deslop_prompts_are_compact_and_keep_contract(tmp_path):
    rendered = render_prompts.render(tmp_path)
    expected = {
        "agy/deslop/SKILL.md", "amp/deslop/SKILL.md", "antigravity/deslop.md",
        "claude/deslop.md", "cline/deslop.md", "cmd/deslop/SKILL.md",
        "codex/deslop.md", "copilot-cli/deslop.md", "cursor/deslop.md",
        "devin/skills/deslop/SKILL.md", "gemini/deslop/SKILL.md",
        "grok/deslop/SKILL.md", "kilocode/deslop.md",
        "opencode/commands/deslop.md", "pi/deslop.md", "warp/deslop.yaml",
    }
    phrases = ("Quick scan", "Baseline validation", "Eight cleanup lanes",
               "Cleanup ledger", "smallest cohesive", "audit",
               "Behavior first", "Evidence over vibes", "Priority")
    for relative in expected:
        path = rendered / relative
        assert path.is_file(), relative
        contents = path.read_text(encoding="utf-8")
        assert path.stat().st_size < 12 * 1024, relative
        for phrase in phrases:
            assert phrase.lower() in contents.lower(), (relative, phrase)


def test_opencode_primary_frontmatter_matches_config_without_duplicate_task_keys():
    config = json.loads((ROOT / "prompts/opencode/opencode.json.example").read_text())

    for name in ("frontier-worker", "worker-worker"):
        prompt = ROOT / "prompts/opencode/agent" / f"{name}.md"
        frontmatter = prompt.read_text().split("---", 2)[1]
        assert f"model: {config['agent'][name]['model']}" in frontmatter

        task_keys = []
        in_task = False
        for line in frontmatter.splitlines():
            if line == "  task:":
                in_task = True
                continue
            if in_task and line.startswith("    ") and ":" in line:
                task_keys.append(line.strip().split(":", 1)[0].strip("'\""))
            elif in_task and line.strip():
                break
        assert len(task_keys) == len(set(task_keys)), name
        assert set(task_keys) == set(config["agent"][name]["permission"]["task"]), name


def test_opencode_primary_prompts_are_compact_and_keep_orchestration_contract():
    shared_phrases = (
        "Outcome-first task briefs",
        "worker-explore",
        "worker-general",
        "Parallelize independent work",
        "combined validation",
        "actual diff",
        "Never claim",
        "BLOCKED",
        "evidence",
        "recommended next action",
        "User-facing answer",
        "Summarize",
    )
    agent_dir = ROOT / "prompts/opencode/agent"
    for name in ("frontier-worker", "worker-worker"):
        prompt = agent_dir / f"{name}.md"
        contents = prompt.read_text(encoding="utf-8")
        assert prompt.stat().st_size < 16 * 1024, name
        for phrase in shared_phrases:
            assert phrase.lower() in contents.lower(), (name, phrase)

    frontier = (agent_dir / "frontier-worker.md").read_text(encoding="utf-8")
    assert "GPT-5.5 primary orchestrator" in frontier
    assert "reason and plan directly" in frontier

    worker = (agent_dir / "worker-worker.md").read_text(encoding="utf-8")
    assert "must not directly investigate" in worker
    assert "must not directly investigate\nthe codebase or implement changes" in worker
    assert "Use tools yourself only for orchestration and verification" in worker
    assert "Never trust worker claims without verification" in worker


def test_bad_canonical_hash_is_rejected(tmp_path):
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    source = prompts / "canonical.md"
    source.write_bytes(b"canonical contents")
    manifest = {
        "version": 1,
        "aliases": [{
            "path": "copy.md",
            "source": "canonical.md",
            "sha256": hashlib.sha256(b"different").hexdigest(),
            "mode": "100644",
        }],
    }
    (prompts / "aliases.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(render_prompts.ManifestError, match="sha256 mismatch"):
        render_prompts.validate(prompts)

    render_prompts.refresh(prompts)
    refreshed = json.loads((prompts / "aliases.json").read_text())
    assert refreshed["aliases"][0]["sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    render_prompts.validate(prompts)
