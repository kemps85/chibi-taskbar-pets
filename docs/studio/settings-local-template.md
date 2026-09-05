# Local Codex Config Template

Use this document as a starting point when creating your own `~/.codex/config.toml`.
It is a personal reference, not a shared repo file.

## Optional Personal Pattern

These are examples only. Pick any model available in your Codex installation;
the Game repo will not override that choice.

```toml
model = "gpt-5.6-sol"
model_reasoning_effort = "high"
service_tier = "default"
web_search = "live"

[profiles.fast]
model = "gpt-5.6-luna"
model_reasoning_effort = "xhigh"
service_tier = "priority"

[profiles.deep]
model = "gpt-5.6-sol"
model_reasoning_effort = "high"
service_tier = "default"
```

## Use Personal Config For

- default model choice
- personal profiles
- local tool preferences
- user-specific integrations and experiments

Keep project behavior in the repo-local `.codex/` files instead.
