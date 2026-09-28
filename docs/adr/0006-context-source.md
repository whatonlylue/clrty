# 0006. Context source

Date: 2026-09-28
Status: Accepted

## Context

The refactoring agent needs code context to make safe edits. Context can be a call-graph slice (callers and callees), or a more sophisticated approach like TopoCTX that prioritizes context by relevance. Simpler context reduces token cost and latency; sophisticated context may reduce mistakes.

## Options considered

**Call-graph slices for v1:** Provide the function, its direct callers, and its direct callees. Simple, fast to compute from the repo-wide call graph. The worker recipe includes "Context is the finding, its file, callers and callees from the call graph, the recipe and the rules" (Build plan › Agent loop internals › Worker toolset).

**TopoCTX behind a trait later:** A more sophisticated context-selection method that prioritizes by relevance graph. Deferred until both TopoCTX and Clarity's architecture stabilize.

## Decision

**Plain call-graph slices for v1; TopoCTX behind a trait later.** Ship with direct neighbors first. The architecture (Build plan › Repository layout) keeps dependencies one-way: `clarity-core ← clarity-lang ← clarity-analyze ← clarity-score ← (clarity-toolchain, clarity-report, clarity-agent, clarity-mcp) ← clarity-cli`, so context-provider implementations can be swapped behind a trait without coupling the loop logic.

## Consequences

Lower token cost and faster context assembly in v1. TopoCTX becomes an optional enhancement behind a trait—available for P3 or later if users want finer prioritization. The call graph is already computed in clarity-analyze for the granularity and coupling analyzers (Build plan › Milestones, P1d), so this decision adds zero new infrastructure.
