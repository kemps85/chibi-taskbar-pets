#!/usr/bin/env python3
"""Run one bounded Codex Game Studios role through a compatible dispatcher."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import tomllib

try:
    from scripts.codex_runtime import resolve_codex_executable
except ModuleNotFoundError:  # Direct execution: python scripts/studio_dispatch.py
    from codex_runtime import resolve_codex_executable


REPO_ROOT = Path(__file__).resolve().parents[1]
AGENTS_DIR = REPO_ROOT / ".codex" / "agents"
@dataclass(frozen=True)
class StudioRole:
    name: str
    description: str
    model: str
    model_reasoning_effort: str
    service_tier: str
    sandbox_mode: str
    developer_instructions: str
    config_path: Path


def _toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def service_tier_for_model(model: str) -> str:
    """Use Fast/Priority only for Luna specialist work."""
    return "priority" if model == "gpt-5.6-luna" else "default"


def load_role(repo_root: Path, role_name: str) -> StudioRole:
    config_path = repo_root / ".codex" / "agents" / f"{role_name}.toml"
    if not config_path.is_file():
        available = ", ".join(path.stem for path in sorted((repo_root / ".codex" / "agents").glob("*.toml")))
        raise ValueError(f"Unknown studio role '{role_name}'. Available roles: {available}")

    with config_path.open("rb") as handle:
        config = tomllib.load(handle)

    required = (
        "name",
        "description",
        "model",
        "model_reasoning_effort",
        "service_tier",
        "developer_instructions",
    )
    missing = [key for key in required if not config.get(key)]
    if missing:
        raise ValueError(f"Role '{role_name}' is missing required fields: {', '.join(missing)}")

    configured_name = str(config["name"])
    if configured_name != role_name:
        raise ValueError(
            f"Role filename '{role_name}' does not match configured name '{configured_name}'"
        )

    return StudioRole(
        name=configured_name,
        description=str(config["description"]),
        model=str(config["model"]),
        model_reasoning_effort=str(config["model_reasoning_effort"]),
        service_tier=str(config["service_tier"]),
        sandbox_mode=str(config.get("sandbox_mode", "workspace-write")),
        developer_instructions=str(config["developer_instructions"]),
        config_path=config_path.resolve(),
    )


def list_roles(repo_root: Path = REPO_ROOT) -> list[StudioRole]:
    return [load_role(repo_root, path.stem) for path in sorted((repo_root / ".codex" / "agents").glob("*.toml"))]


def build_dispatch_prompt(*, repo_root: Path, role_name: str, task: str) -> str:
    role = load_role(repo_root, role_name)
    return (
        f"You are the delegated `{role.name}` role for a larger Codex game "
        "studio. Follow the role instructions below for this bounded task. "
        "Do not spawn other agents and do not invoke scripts/studio_dispatch.py; "
        "this process is already the delegated worker. Return only your final "
        "answer to the task.\n\n"
        "<role-instructions>\n"
        f"{role.developer_instructions}\n"
        "</role-instructions>\n\n"
        f"<studio-task>\n{task}\n</studio-task>"
    )


def build_codex_exec_command(
    *,
    repo_root: Path,
    role_name: str,
    task: str,
    codex_executable: Path,
    output_path: Path,
) -> list[str]:
    role = load_role(repo_root, role_name)
    return [
        str(codex_executable),
        "exec",
        "-C",
        str(repo_root.resolve()),
        "--enable",
        "hooks",
        "--skip-git-repo-check",
        "--ephemeral",
        "--ignore-user-config",
        "--color",
        "never",
        "-m",
        role.model,
        "-c",
        f'model_reasoning_effort="{role.model_reasoning_effort}"',
        "-c",
        f'service_tier="{role.service_tier}"',
        "-s",
        role.sandbox_mode,
        "-o",
        str(output_path),
        "-",
    ]


def _task_from_args(args: argparse.Namespace) -> str:
    if args.task and args.task_file:
        raise ValueError("Use either --task or --task-file, not both")
    if args.task_file:
        task = Path(args.task_file).read_text(encoding="utf-8")
    elif args.task:
        task = args.task
    elif not sys.stdin.isatty():
        task = sys.stdin.read()
    else:
        raise ValueError("Provide --task, --task-file, or pipe a task on stdin")
    if not task.strip():
        raise ValueError("Studio task must not be empty")
    return task.strip()


def run_role(args: argparse.Namespace) -> int:
    task = _task_from_args(args)
    role = load_role(REPO_ROOT, args.role)
    codex_executable = resolve_codex_executable()
    output_path = (
        Path(args.output).resolve()
        if args.output
        else Path(tempfile.gettempdir()) / "codex-game-studio" / f"{role.name}-{int(time.time())}.txt"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = build_codex_exec_command(
        repo_root=REPO_ROOT,
        role_name=role.name,
        task=task,
        codex_executable=codex_executable,
        output_path=output_path,
    )
    prompt = build_dispatch_prompt(repo_root=REPO_ROOT, role_name=role.name, task=task)

    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            input=prompt,
            encoding="utf-8",
            timeout=args.timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        result = {
            "status": "error",
            "summary": f"Role {role.name} timed out after {args.timeout}s",
            "next_actions": ["Retry with a narrower task or a larger --timeout"],
            "artifacts": [str(output_path)],
        }
        print(json.dumps(result, ensure_ascii=False, indent=2), file=sys.stderr)
        return 124

    final_message = output_path.read_text(encoding="utf-8").strip() if output_path.exists() else ""
    status = "success" if completed.returncode == 0 and final_message and not final_message.startswith("STUDIO_DISPATCH_ERROR:") else "error"
    result = {
        "status": status,
        "summary": final_message or f"Codex exited with code {completed.returncode} without a final message",
        "role": role.name,
        "role_model": role.model,
        "role_reasoning_effort": role.model_reasoning_effort,
        "role_service_tier": role.service_tier,
        "duration_seconds": round(time.monotonic() - started, 2),
        "next_actions": [] if status == "success" else ["Inspect stderr and verify the custom-role registration path"],
        "artifacts": [str(output_path)],
        "stderr_tail": completed.stderr.splitlines()[-12:],
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif final_message:
        print(final_message)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2), file=sys.stderr)
    return 0 if status == "success" else (completed.returncode or 1)


def doctor() -> int:
    issues: list[str] = []
    try:
        codex_path = resolve_codex_executable()
    except FileNotFoundError as exc:
        codex_path = None
        issues.append(str(exc))

    roles = list_roles()
    config_path = REPO_ROOT / ".codex" / "config.toml"
    with config_path.open("rb") as handle:
        config = tomllib.load(handle)
    if config.get("model") != "gpt-5.6-sol":
        issues.append("Primary model is not gpt-5.6-sol")
    if config.get("model_reasoning_effort") != "max":
        issues.append("Primary reasoning effort is not max")
    if config.get("service_tier") != "default":
        issues.append("Studio default service tier is not standard")
    for role in roles:
        expected_tier = service_tier_for_model(role.model)
        if role.service_tier != expected_tier:
            issues.append(
                f"Role {role.name} uses service tier {role.service_tier}; expected {expected_tier}"
            )

    result = {
        "status": "success" if not issues else "error",
        "summary": f"Validated {len(roles)} studio roles",
        "next_actions": [] if not issues else issues,
        "artifacts": [str(config_path), str(AGENTS_DIR)],
        "codex_executable": str(codex_path) if codex_path else None,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not issues else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List configured studio roles")
    list_parser.add_argument("--json", action="store_true")

    subparsers.add_parser("doctor", help="Validate the local dispatcher and model policy")

    run_parser = subparsers.add_parser("run", help="Run one bounded studio role")
    run_parser.add_argument("role")
    run_parser.add_argument("--task")
    run_parser.add_argument("--task-file")
    run_parser.add_argument("--output")
    run_parser.add_argument("--timeout", type=int, default=600)
    run_parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.command == "doctor":
            return doctor()
        if args.command == "list":
            roles = list_roles()
            if args.json:
                print(json.dumps([asdict(role) | {"config_path": str(role.config_path)} for role in roles], ensure_ascii=False, indent=2))
            else:
                for role in roles:
                    print(
                        f"{role.name:34} {role.model:16} "
                        f"{role.model_reasoning_effort:5} {role.service_tier}"
                    )
            return 0
        return run_role(args)
    except (FileNotFoundError, OSError, ValueError, tomllib.TOMLDecodeError) as exc:
        print(f"STUDIO_DISPATCH_ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
