#!/usr/bin/env python3
"""Resolve the Codex executable used by studio automation."""

from __future__ import annotations

from collections.abc import Mapping
import os
from pathlib import Path
import shutil


def _desktop_managed_codex(local_app_data: Path) -> Path | None:
    """Return the newest executable managed by Codex Desktop, if present."""
    bin_root = local_app_data / "OpenAI" / "Codex" / "bin"
    candidates = [path for path in bin_root.glob("*/codex.exe") if path.is_file()]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime_ns)


def resolve_codex_executable(
    *,
    platform: str = os.name,
    environ: Mapping[str, str] | None = None,
    local_app_data: Path | None = None,
    which=shutil.which,
) -> Path:
    """Prefer explicit overrides, then Codex Desktop, then PATH fallbacks.

    Codex Desktop keeps its active CLI under LocalAppData. On Windows this must
    win over an older npm ``codex.cmd`` installation. The Windows Store package
    resource is intentionally not searched because direct process launches can
    fail with access denied.
    """
    env = os.environ if environ is None else environ
    for variable in ("CODEX_BIN", "CODEX_CLI_PATH"):
        override = env.get(variable)
        if not override:
            continue
        path = Path(override).expanduser()
        if path.is_file():
            return path.resolve()
        raise FileNotFoundError(f"{variable} does not point to a file: {path}")

    if platform == "nt":
        local_root = local_app_data
        if local_root is None and env.get("LOCALAPPDATA"):
            local_root = Path(env["LOCALAPPDATA"])
        if local_root is not None:
            managed = _desktop_managed_codex(local_root)
            if managed is not None:
                return managed.resolve()

        candidates = ("codex.cmd", "codex.exe")
    else:
        candidates = ("codex",)

    for candidate in candidates:
        resolved = which(candidate)
        if resolved:
            return Path(resolved)
    raise FileNotFoundError(
        "Could not locate an executable Codex CLI. Install Codex or set CODEX_BIN."
    )
