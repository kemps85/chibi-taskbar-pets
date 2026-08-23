# GPT-5.6 Model Routing

This studio uses a tiered GPT-5.6 hierarchy. The goal is to keep one strong
technical authority at the front door while assigning most execution to the
cost-efficient specialist tier.

## Reception Layer

| Responsibility | Model | Effort |
|---|---|---|
| Primary Technical Director / Studio Lead | `gpt-5.6-sol` | `max` |

The primary Sol session receives every user prompt. It clarifies requirements,
selects the workflow, chooses roles, resolves conflicts, and synthesizes the
final response. It delegates implementation instead of acting as every
department at once.

## Director Layer

The following configured agents use `gpt-5.6-sol` with `max` reasoning:

- `technical-director`
- `creative-director`
- `producer`

Use them for binding project-level decisions, difficult tradeoffs, and final
phase gates.

## Lead Layer

The following configured agents use `gpt-5.6-terra` with `max` reasoning:

- `game-designer`
- `lead-programmer`
- `art-director`
- `audio-director`
- `narrative-director`
- `qa-lead`
- `release-manager`
- `localization-lead`

Leads turn a director decision into a coherent domain plan and review specialist
output before it returns to Sol.

## Specialist Layer

All other project agents use `gpt-5.6-luna` with `xhigh` reasoning and priority
service tier. This is the only layer that uses Fast/Priority speed. It includes
programmers, engine specialists, QA execution, design specialists, operations,
analytics, accessibility, security, publishing, and content roles.

Luna is the default spawned-agent model in `.codex/config.toml`, so generic
workers also stay on the specialist tier unless a named role overrides it. Every
named role pins `service_tier` in its own `.codex/agents/*.toml` file: Luna uses
`priority`, while Sol and Terra use `default`. The compatibility dispatcher and
live runners enforce the same rule.

## Escalation Rules

1. Start with the lowest layer that owns the decision.
2. Escalate from Luna to a Terra lead when the result crosses domain boundaries,
   fails validation, or requires a domain-level tradeoff.
3. Escalate to Sol when the choice constrains architecture, schedule, game
   identity, release safety, or multiple departments.
4. Do not rerun work on a more expensive model merely because it exists. Require
   a concrete quality gap or authority boundary.
5. Parallelize read-heavy review and testing. Give write-heavy work explicit,
   non-overlapping file ownership.

## Runtime Compatibility

Codex custom-agent selection can differ between client versions and multi-agent
tool variants. `scripts/studio_dispatch.py` is the compatibility path: it runs
exactly one requested role as an isolated delegated Codex process, loads that
role's model/reasoning tier and developer instructions, and sends the bounded
task through stdin. Native multi-agent delegation remains preferred when it is
working. On Windows, studio automation prefers the executable managed by Codex
Desktop under `%LOCALAPPDATA%\OpenAI\Codex\bin` before an older npm shim on
`PATH`; `CODEX_BIN` or `CODEX_CLI_PATH` can explicitly override that choice.
