# 0001. Core language

Date: 2026-09-28
Status: Accepted

## Context

Clarity rescores code hundreds of times per session—once after every edit during refactoring. The scoring engine runs in tight loops on every saved file in agent mode, and performance directly affects turnaround time and cost. Additionally, Clarity must ship as a self-contained tool that users invoke locally, and native ecosystem integration matters.

## Options considered

**Rust:** Compile to a single static binary with native tree-sitter and ast-grep integration. Fast, zero external dependencies at runtime, and shares the ecosystem with Ruff, Biome, Oxc, and CodeScene's MCP server.

**Python throughout:** Leverage the existing `scb-check` Python port. Prototyping is faster, but startup time and packaging friction penalize a tool that runs after every edit (Project Plan › Tech stack). The spike would need to wrap `scb-check`, `radon`, and `sloptrack` separately.

## Decision

**Python spike (P0), then Rust engine.** Validate the metric and score accuracy against human judgment using a Python wrapper around `scb-check` (Build plan › Milestones, P0). Once the score passes the E1 agreement test, build the production engine in Rust to achieve the subsecond latency that prevention-mode feedback requires.

## Consequences

The Python spike is archived after P1 once the metric is validated. The Rust engine is then developed and tested via parity jobs (Build plan › Parity + corpus) that run both over the same corpus, ensuring erosion and verbosity match pinned `scb-check` within 0.01. This sequencing trades implementation cost for confidence—shipping the engine only after the metric earns trust. P0 is a 2-week sprint to gather human-agreement data; this eliminates the risk of building a fast scoring engine for a metric that users don't actually agree with.
