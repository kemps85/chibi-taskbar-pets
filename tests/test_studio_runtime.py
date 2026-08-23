from __future__ import annotations

import importlib
import json
from pathlib import Path
import tomllib

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]

DIRECTORS = {"creative-director", "producer", "technical-director"}
LEADS = {
    "art-director",
    "audio-director",
    "game-designer",
    "lead-programmer",
    "localization-lead",
    "narrative-director",
    "qa-lead",
    "release-manager",
}

SPECIALISTS = 39


def _load_toml(path: Path) -> dict:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def test_studio_config_primary_receiver_uses_sol_high_and_modern_keys() -> None:
    # Arrange
    config_path = REPO_ROOT / ".codex" / "config.toml"

    # Act
    config = _load_toml(config_path)

    # Assert
    assert config["model"] == "gpt-5.6-sol"
    assert config["model_reasoning_effort"] == "high"
    assert config["service_tier"] == "default"
    assert config["agents"]["default_subagent_model"] == "gpt-5.6-luna"
    assert config["agents"]["default_subagent_reasoning_effort"] == "xhigh"
    assert config["agents"]["max_concurrent_threads_per_session"] == 6
    assert config["features"]["hooks"] is True
    assert config["features"]["multi_agent"] is True
    assert "codex_hooks" not in config["features"]
    assert "apply_patch_freeform" not in config["features"]
    assert "max_depth" not in config["agents"]


def test_agent_models_roster_assigns_sol_directors_terra_leads_luna_specialists() -> None:
    # Arrange
    agent_paths = sorted((REPO_ROOT / ".codex" / "agents").glob("*.toml"))

    # Act
    assignments = {
        path.stem: (
            _load_toml(path)["model"],
            _load_toml(path)["model_reasoning_effort"],
            _load_toml(path)["service_tier"],
        )
        for path in agent_paths
    }

    # Assert
    assert len(assignments) == 50
    for name, assignment in assignments.items():
        if name in DIRECTORS:
            assert assignment == ("gpt-5.6-sol", "high", "default")
        elif name in LEADS:
            assert assignment == ("gpt-5.6-terra", "high", "default")
        else:
            assert assignment == ("gpt-5.6-luna", "xhigh", "priority")
    assert sum(
        assignment == ("gpt-5.6-luna", "xhigh", "priority")
        for assignment in assignments.values()
    ) == SPECIALISTS


def test_global_bootstrapper_uses_luna_xhigh_priority() -> None:
    # Arrange / Act
    config = _load_toml(REPO_ROOT / "global-pack" / "agents" / "studio-bootstrapper.toml")

    # Assert
    assert config["model"] == "gpt-5.6-luna"
    assert config["model_reasoning_effort"] == "xhigh"
    assert config["service_tier"] == "priority"


def test_hooks_windows_commands_use_cross_platform_runner() -> None:
    # Arrange
    hooks_path = REPO_ROOT / ".codex" / "hooks.json"

    # Act
    hooks = json.loads(hooks_path.read_text(encoding="utf-8"))["hooks"]
    command_handlers = [
        handler
        for handlers in hooks.values()
        for group in handlers
        for handler in group["hooks"]
        if handler["type"] == "command"
    ]

    # Assert
    assert command_handlers
    for handler in command_handlers:
        assert "commandWindows" in handler
        assert "run_hook.py" in handler["commandWindows"]


def test_dispatcher_known_role_builds_direct_role_codex_command(tmp_path: Path) -> None:
    # Arrange
    dispatcher = importlib.import_module("scripts.studio_dispatch")
    output_path = tmp_path / "technical-director.txt"

    # Act
    command = dispatcher.build_codex_exec_command(
        repo_root=REPO_ROOT,
        role_name="technical-director",
        task="Review the architecture.",
        codex_executable=Path("codex.exe"),
        output_path=output_path,
    )
    rendered = " ".join(str(part) for part in command)

    # Assert
    assert command[0] == "codex.exe"
    assert "gpt-5.6-sol" in command
    assert 'model_reasoning_effort="high"' in command
    assert command[-1] == "-"
    assert 'service_tier="default"' in command
    assert "agents.technical-director.config_file" not in rendered
    assert "fork_context=false" not in rendered

    prompt = dispatcher.build_dispatch_prompt(
        role_name="technical-director",
        task="Review the architecture.",
        repo_root=REPO_ROOT,
    )
    assert "Technical Director" in prompt
    assert "Do not spawn other agents" in prompt
    assert str(output_path) in command


def test_dispatcher_unknown_role_raises_clear_error() -> None:
    # Arrange
    dispatcher = importlib.import_module("scripts.studio_dispatch")

    # Act / Assert
    with pytest.raises(ValueError, match="Unknown studio role"):
        dispatcher.load_role(REPO_ROOT, "not-a-real-role")


def test_hook_runner_windows_prefers_explicit_git_bash() -> None:
    # Arrange
    hook_runner = importlib.import_module("scripts.run_hook")
    expected = Path(r"C:\Program Files\Git\bin\bash.exe")

    # Act
    resolved = hook_runner.resolve_bash(
        platform="win32",
        which=lambda _: None,
        exists=lambda path: path == expected,
    )

    # Assert
    assert resolved == expected


def test_live_runner_windows_prefers_desktop_managed_runtime_over_old_shell_shim(
    tmp_path: Path,
) -> None:
    # Arrange
    live_runner = importlib.import_module("scripts.run_codex_e2e")
    expected = tmp_path / "OpenAI" / "Codex" / "bin" / "current" / "codex.exe"
    expected.parent.mkdir(parents=True)
    expected.touch()
    old_npm = r"C:\Users\ASUS\AppData\Roaming\npm\codex.cmd"

    # Act
    resolved = live_runner.resolve_codex_executable(
        platform="nt",
        environ={},
        local_app_data=tmp_path,
        which=lambda name: old_npm if name == "codex.cmd" else None,
    )

    # Assert
    assert Path(resolved) == expected


def test_live_runner_windows_falls_back_to_shell_shim_when_desktop_runtime_is_missing(
    tmp_path: Path,
) -> None:
    # Arrange
    live_runner = importlib.import_module("scripts.run_codex_e2e")
    expected = r"C:\Users\ASUS\AppData\Roaming\npm\codex.cmd"

    # Act
    resolved = live_runner.resolve_codex_executable(
        platform="nt",
        environ={},
        local_app_data=tmp_path,
        which=lambda name: expected if name == "codex.cmd" else None,
    )

    # Assert
    assert resolved == expected


def test_live_runner_agent_probe_registers_role_and_disables_full_history(tmp_path: Path) -> None:
    # Arrange
    live_runner = importlib.import_module("scripts.run_codex_e2e")
    json_path = tmp_path / "agent.jsonl"
    message_path = tmp_path / "agent.txt"

    # Act
    command = live_runner.build_codex_command(
        kind="agent",
        name="technical-director",
        prompt=live_runner.agent_prompt("technical-director"),
        json_path=json_path,
        message_path=message_path,
        model="gpt-5.6-sol",
        reasoning_effort="high",
    )
    rendered = " ".join(command)

    # Assert
    assert command[0].lower().endswith(("codex.exe", "codex.cmd", "codex"))
    assert "--enable hooks" in rendered
    assert 'service_tier="default"' in rendered
    assert "agents.technical-director.config_file" in rendered
    assert "fork_context=false" in rendered


def test_live_runner_accepts_powershell_project_gap_probes_as_benign() -> None:
    # Arrange
    live_runner = importlib.import_module("scripts.run_codex_e2e")
    command = (
        "Get-ChildItem -LiteralPath 'production\\sprints','production\\milestones' "
        "-File -Recurse (exit=-1)"
    )

    # Act / Assert
    assert live_runner.is_benign_project_gap_command(command)


def test_live_runner_recognizes_current_cli_subagent_hook_evidence() -> None:
    # Arrange
    live_runner = importlib.import_module("scripts.run_codex_e2e")
    stderr = (
        "WARN codex_core::hook_runtime: failed to resolve parent transcript path "
        "for subagent hook parent_thread_id=01a02df1-f9b3-73d1-9620-39984be9d7f9"
    )

    # Act / Assert
    assert live_runner.has_subagent_runtime_evidence(stderr)
    assert live_runner.filter_stderr(stderr) == []


def test_live_runner_uses_priority_only_for_luna() -> None:
    # Arrange
    live_runner = importlib.import_module("scripts.run_codex_e2e")
    json_path = REPO_ROOT / "tmp-agent.jsonl"
    message_path = REPO_ROOT / "tmp-agent.txt"

    # Act
    sol_command = live_runner.build_codex_command(
        kind="agent",
        name="technical-director",
        prompt="Reply exactly READY.",
        json_path=json_path,
        message_path=message_path,
        model="gpt-5.6-sol",
        reasoning_effort="high",
    )
    luna_command = live_runner.build_codex_command(
        kind="agent",
        name="accessibility-specialist",
        prompt="Reply exactly READY.",
        json_path=json_path,
        message_path=message_path,
        model="gpt-5.6-luna",
        reasoning_effort="xhigh",
    )

    # Assert
    assert 'service_tier="default"' in " ".join(sol_command)
    assert 'service_tier="priority"' in " ".join(luna_command)
