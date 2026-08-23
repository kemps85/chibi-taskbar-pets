#!/usr/bin/env python3
"""Run a repository shell hook with an explicit, Windows-safe Bash runtime."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Callable


REPO_ROOT = Path(__file__).resolve().parents[1]
HOOKS_DIR = REPO_ROOT / ".codex" / "hooks"


def resolve_bash(
    *,
    platform: str = sys.platform,
    which: Callable[[str], str | None] = shutil.which,
    exists: Callable[[Path], bool] = Path.exists,
) -> Path:
    override = os.environ.get("STUDIO_GIT_BASH")
    if override:
        path = Path(override)
        if exists(path):
            return path
        raise FileNotFoundError(f"STUDIO_GIT_BASH does not exist: {path}")

    if platform == "win32":
        candidates = [
            Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Git" / "bin" / "bash.exe",
            Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Git" / "usr" / "bin" / "bash.exe",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Git" / "bin" / "bash.exe",
        ]
        git = which("git.exe") or which("git")
        if git:
            git_path = Path(git).resolve()
            candidates.extend(
                [
                    git_path.parents[1] / "bin" / "bash.exe",
                    git_path.parents[1] / "usr" / "bin" / "bash.exe",
                ]
            )
        for candidate in candidates:
            if exists(candidate):
                return candidate
        raise FileNotFoundError(
            "Git Bash was not found. Install Git for Windows or set STUDIO_GIT_BASH. "
            "The Windows WSL relay at C:\\Windows\\System32\\bash.exe is intentionally ignored."
        )

    bash = which("bash")
    if bash:
        return Path(bash)
    raise FileNotFoundError("Bash was not found on PATH")


def resolve_hook(script_name: str) -> Path:
    if Path(script_name).name != script_name or not script_name.endswith(".sh"):
        raise ValueError(f"Invalid hook script name: {script_name}")
    hook = (HOOKS_DIR / script_name).resolve()
    if hook.parent != HOOKS_DIR.resolve() or not hook.is_file():
        raise FileNotFoundError(f"Hook script not found: {hook}")
    return hook


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: run_hook.py <hook-script.sh>", file=sys.stderr)
        return 2
    try:
        bash = resolve_bash()
        hook = resolve_hook(sys.argv[1])
    except (FileNotFoundError, ValueError) as exc:
        print(f"STUDIO_HOOK_ERROR: {exc}", file=sys.stderr)
        return 2

    completed = subprocess.run(
        [str(bash), str(hook)],
        cwd=REPO_ROOT,
        input=sys.stdin.buffer.read(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    sys.stdout.buffer.write(completed.stdout)
    sys.stderr.buffer.write(completed.stderr)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
