# Hooks Reference

This repo uses the current Codex hook surface for lightweight automation and validation.

## Supported Events

- `SessionStart`
- `PreToolUse`
- `PostToolUse`
- `UserPromptSubmit`
- `Stop`

Hook registration lives in `.codex/hooks.json`. Hook scripts live in `.codex/hooks/`.

On Windows, every handler uses `commandWindows` to call
`scripts/run_hook.py`. The runner locates Git Bash explicitly and intentionally
avoids the WSL relay at `C:\Windows\System32\bash.exe`. Set
`STUDIO_GIT_BASH` only when Git Bash is installed in a non-standard location.

## What Hooks Do in This Repo

- session start hooks provide lightweight repo context
- tool hooks validate or summarize safe runtime behavior where supported
- stop hooks run end-of-turn checks such as asset or skill validation

## Design Rules

- commands should resolve from the git root when they call repo-local scripts
- every shell hook must provide a Windows override through `scripts/run_hook.py`
- hook scripts should fail clearly and avoid silent broken matchers
- only supported Codex hook events should remain wired
- hooks should assist the workflow, not replace explicit skills or approvals

## Validation

The validator checks hook integrity through `scripts/validate_codex_native.py`.

Use it after any hook or config change.
