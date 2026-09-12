#!/usr/bin/env python3
"""Validate the Pipeline plugin's Codex-specific ingestion contract."""

from __future__ import annotations

import argparse
import json
import re
import tomllib
from pathlib import Path, PurePosixPath
from typing import Any


SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")
FORBIDDEN_INSTRUCTION_PATTERNS = {
    "non-Codex vendor branding": re.compile(r"\b(?:claude|anthropic)\b", re.IGNORECASE),
    "Claude Code agent selector": re.compile(r"\bsubagent_type\b", re.IGNORECASE),
    "Claude Code Agent tool": re.compile(r"\bAgent tool\b", re.IGNORECASE),
    "external Claude Code runner": re.compile(r"\bclaude\s+-p\b", re.IGNORECASE),
    "Claude Code background-spawn argument": re.compile(r"\brun_in_background\b", re.IGNORECASE),
    "Claude Code project instructions": re.compile(r"\bCLAUDE\.md\b", re.IGNORECASE),
    "Claude-only skill frontmatter": re.compile(r"(?m)^allowed-tools\s*:"),
    "stale Markdown custom-agent path": re.compile(r"agents/[a-z0-9-]+\.md\b", re.IGNORECASE),
    "Claude model id": re.compile(r"\bclaude-(?:haiku|sonnet|opus|fable)[a-z0-9.-]*\b", re.IGNORECASE),
}
REQUIRED_AGENT_KEYS = {"name", "description", "developer_instructions"}
LEGACY_AGENT_KEYS = {"tools", "color"}
VALID_EFFORTS = {"low", "medium", "high", "xhigh", "max"}


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
    for key in ("name", "version", "description", "skills", "interface", "agents"):
        if not manifest.get(key):
            errors.append(f"plugin.json is missing `{key}`")
    version = manifest.get("version")
    if not isinstance(version, str) or SEMVER_RE.fullmatch(version) is None:
        errors.append("plugin.json `version` must be strict semver")

    errors.extend(validate_agents(root, manifest.get("agents")))
    errors.extend(validate_skills(root))
    errors.extend(validate_instruction_surfaces(root))
    return errors


def validate_agents(root: Path, entries: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(entries, list) or not entries:
        return ["plugin.json `agents` must be a non-empty array"]

    registered: set[Path] = set()
    names: set[str] = set()
    for index, raw_path in enumerate(entries):
        label = f"agents[{index}]"
        if not isinstance(raw_path, str) or not raw_path.strip():
            errors.append(f"{label} must be a non-empty relative path")
            continue
        candidate = PurePosixPath(raw_path.replace("\\", "/"))
        if candidate.is_absolute() or any(part in {"", ".", ".."} for part in candidate.parts):
            errors.append(f"{label} must stay inside the plugin")
            continue
        path = (root / candidate.as_posix()).resolve()
        if not path.is_relative_to(root) or path.suffix != ".toml" or not path.is_file():
            errors.append(f"{label} must point to an existing TOML file inside the plugin")
            continue
        registered.add(path)
        try:
            payload = tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError) as exc:
            errors.append(f"{path.relative_to(root)} is not valid TOML: {exc}")
            continue
        missing = sorted(key for key in REQUIRED_AGENT_KEYS if not isinstance(payload.get(key), str) or not payload[key].strip())
        if missing:
            errors.append(f"{path.relative_to(root)} is missing non-empty keys: {', '.join(missing)}")
        legacy = sorted(LEGACY_AGENT_KEYS & payload.keys())
        if legacy:
            errors.append(f"{path.relative_to(root)} contains Claude-style keys: {', '.join(legacy)}")
        name = payload.get("name")
        if isinstance(name, str):
            if name in names:
                errors.append(f"duplicate agent name `{name}`")
            names.add(name)
        model = payload.get("model")
        if model is not None and (not isinstance(model, str) or not model.startswith("gpt-")):
            errors.append(f"{path.relative_to(root)} `model` must be a Codex gpt-* id")
        effort = payload.get("model_reasoning_effort")
        if effort is not None and effort not in VALID_EFFORTS:
            errors.append(f"{path.relative_to(root)} has invalid model_reasoning_effort")

    discovered = {path.resolve() for path in (root / "agents").glob("*.toml")}
    for path in sorted(discovered - registered):
        errors.append(f"unregistered custom agent: {path.relative_to(root)}")
    for path in sorted(registered - discovered):
        errors.append(f"registered agent is outside agents/: {path.relative_to(root)}")
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
    paths.extend(sorted((root / "agents").glob("*.toml")))
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
