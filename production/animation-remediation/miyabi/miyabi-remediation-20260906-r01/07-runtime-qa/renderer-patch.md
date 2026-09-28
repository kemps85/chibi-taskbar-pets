# Renderer patch rationale

Independent runtime-only patch, not an art workaround:

- Before: Miyabi selected `imageSmoothingEnabled = true` and quality `high`.
- After: all taskbar-pet frames use `imageSmoothingEnabled = false` and quality `low`, matching the hard nearest-neighbor art contract. Firefly was already false/low, so its setting is unchanged.
- Scoped original backup: `00-baseline/renderer.js.prepatch`.
- Current renderer SHA-256: `71b179f07d3eb4852027e821b63f17ed91a512e8f316bb05c94a6677a87550b4`; pre-patch SHA-256: `6f69e847f03b250e36fb44c6fb2dcb622a89056a25fe31f0b4edaa29cac99799`.
- Regression evidence: `tests/taskbar-pet/renderer-contract.test.mjs`; final `npm.cmd test` result 38/38 PASS.
- Stable pack/behavior assets were not regenerated or replaced.
