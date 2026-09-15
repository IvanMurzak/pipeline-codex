#!/usr/bin/env python3
"""Validate the Pipeline plugin's Codex-specific ingestion contract."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")
FORBIDDEN_INSTRUCTION_PATTERNS = {
    "non-Codex vendor branding": re.compile(r"\b(?:claude|anthropic)\b", re.IGNORECASE),
    "Claude Code agent selector": re.compile(r"\bsubagent_type\b", re.IGNORECASE),
    "plugin custom-agent selector": re.compile(r"\bagent_type\b", re.IGNORECASE),
    "Claude Code Agent tool": re.compile(r"\bAgent tool\b", re.IGNORECASE),
    "external Claude Code runner": re.compile(r"\bclaude\s+-p\b", re.IGNORECASE),
    "Claude Code background-spawn argument": re.compile(r"\brun_in_background\b", re.IGNORECASE),
    "Claude Code project instructions": re.compile(r"\bCLAUDE\.md\b", re.IGNORECASE),
    "Claude-only skill frontmatter": re.compile(r"(?m)^allowed-tools\s*:"),
    "Claude model id": re.compile(r"\bclaude-(?:haiku|sonnet|opus|fable)[a-z0-9.-]*\b", re.IGNORECASE),
}
def validate_plugin(plugin_root: Path) -> list[str]:
    root = plugin_root.resolve()
    errors: list[str] = []
    manifest_path = root / ".codex-plugin" / "plugin.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot load .codex-plugin/plugin.json: {exc}"]

    if not isinstance(manifest, dict):
        return [".codex-plugin/plugin.json must contain an object"]
    for key in ("name", "version", "description", "skills", "interface"):
        if not manifest.get(key):
            errors.append(f"plugin.json is missing `{key}`")
    version = manifest.get("version")
    if not isinstance(version, str) or SEMVER_RE.fullmatch(version) is None:
        errors.append("plugin.json `version` must be strict semver")

    if "agents" in manifest:
        errors.append("plugin.json must not declare unsupported `agents`")
    errors.extend(validate_roles(root))
    errors.extend(validate_skills(root))
    errors.extend(validate_instruction_surfaces(root))
    return errors


def validate_roles(root: Path) -> list[str]:
    names = (
        "pipeline-disambiguator",
        "pipeline-improver",
        "pipeline-manager",
        "pipeline-script-creator",
        "step-executor",
    )
    errors: list[str] = []
    for name in names:
        path = root / "skills" / "run" / "references" / "roles" / f"{name}.md"
        if not path.is_file() or not path.read_text(encoding="utf-8").strip():
            errors.append(f"missing bundled role brief: {path.relative_to(root)}")
    return errors


def validate_skills(root: Path) -> list[str]:
    errors: list[str] = []
    skills_root = root / "skills"
    skill_files = sorted(skills_root.glob("*/SKILL.md"))
    if not skill_files:
        return ["no skills/*/SKILL.md files found"]
    for path in skill_files:
        contents = path.read_text(encoding="utf-8")
        if not contents.startswith("---\n") or "\n---\n" not in contents[4:]:
            errors.append(f"{path.relative_to(root)} has invalid YAML frontmatter boundaries")
            continue
        frontmatter = contents.split("\n---\n", 1)[0][4:]
        for key in ("name", "description"):
            if re.search(rf"(?m)^{key}:\s*\S", frontmatter) is None:
                errors.append(f"{path.relative_to(root)} is missing frontmatter `{key}`")
    return errors


def validate_instruction_surfaces(root: Path) -> list[str]:
    errors: list[str] = []
    paths = [root / "README.md"]
    paths.extend(sorted((root / "skills").glob("**/*.md")))
    saw_spawn_agent = False
    for path in paths:
        contents = path.read_text(encoding="utf-8")
        saw_spawn_agent = saw_spawn_agent or "spawn_agent" in contents
        for label, pattern in FORBIDDEN_INSTRUCTION_PATTERNS.items():
            if pattern.search(contents):
                errors.append(f"{path.relative_to(root)} contains forbidden {label}")
    if not saw_spawn_agent:
        errors.append("Codex instruction surfaces do not reference native `spawn_agent`")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("plugin_path", nargs="?", default=".")
    args = parser.parse_args()
    errors = validate_plugin(Path(args.plugin_path))
    if errors:
        print("Plugin validation failed:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print(f"Plugin validation passed: {Path(args.plugin_path).resolve()}")


if __name__ == "__main__":
    main()
