from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = PLUGIN_ROOT / ".github" / "scripts" / "validate_plugin.py"
SPEC = importlib.util.spec_from_file_location("pipeline_plugin_validator", VALIDATOR_PATH)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class PluginValidationTests(unittest.TestCase):
    def validate_mutation(self, mutate) -> list[str]:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "plugin"
            shutil.copytree(PLUGIN_ROOT, root, ignore=shutil.ignore_patterns(".git", "__pycache__"))
            mutate(root)
            return VALIDATOR.validate_plugin(root)

    def test_repository_is_valid(self) -> None:
        self.assertEqual([], VALIDATOR.validate_plugin(PLUGIN_ROOT))

    def test_rejects_claude_agent_selector(self) -> None:
        def mutate(root: Path) -> None:
            path = root / "skills" / "run" / "SKILL.md"
            path.write_text(path.read_text(encoding="utf-8") + "\nsubagent_type\n", encoding="utf-8")

        self.assertTrue(any("agent selector" in error for error in self.validate_mutation(mutate)))

    def test_rejects_unregistered_agent(self) -> None:
        def mutate(root: Path) -> None:
            path = root / ".codex-plugin" / "plugin.json"
            manifest = json.loads(path.read_text(encoding="utf-8"))
            manifest["agents"].pop()
            path.write_text(json.dumps(manifest), encoding="utf-8")

        self.assertTrue(any("unregistered custom agent" in error for error in self.validate_mutation(mutate)))

    def test_rejects_claude_agent_toml_keys(self) -> None:
        def mutate(root: Path) -> None:
            path = root / "agents" / "step-executor.toml"
            path.write_text(path.read_text(encoding="utf-8") + '\ntools = ["Agent"]\n', encoding="utf-8")

        self.assertTrue(any("Claude-style keys" in error for error in self.validate_mutation(mutate)))

    def test_rejects_non_codex_branding_in_readme(self) -> None:
        def mutate(root: Path) -> None:
            path = root / "README.md"
            path.write_text(path.read_text(encoding="utf-8") + "\nhttps://claude.example\n", encoding="utf-8")

        self.assertTrue(any("vendor branding" in error for error in self.validate_mutation(mutate)))


if __name__ == "__main__":
    unittest.main()
