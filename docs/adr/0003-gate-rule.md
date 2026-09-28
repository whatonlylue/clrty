# 0003. Gate rule

Date: 2026-09-28
Status: Accepted

## Context

Every refactoring step must pass a gate before the commit is accepted. The gate compares the new score to the baseline and decides whether the change improves code quality or merely reshapes it. The rule must be strict enough to reject cosmetic edits that don't improve the score, yet permissive enough to allow real progress.

## Options considered

**Vector gate (ε = 0.25, δ = 1.0):** The composite score must rise by at least ε points, AND no individual family may drop by more than δ points (Project Plan › Agent mode › Gate, cheapest check first).

**Composite-only:** Accept steps that raise the composite alone, ignoring individual family scores. Simpler to implement but allows gaming: the plan notes "Erosion rewards splitting big functions; granularity punishes single-use helpers. Keeping both in the vector outlaws the cheapest trick, shattering everything into three-line helpers" (Project Plan › Built-in tension against gaming).

## Decision

**Vector gate with ε = 0.25 and δ = 1.0.** Both thresholds are required. The composite must improve, but no family may degrade significantly. This design prevents the most common gaming strategy (over-partitioning), enforced by the opposing tension between erosion and granularity families.

## Consequences

The gate runs in order (G0–G6, cheapest checks first; first failure stops acceptance) with architectural defenses: frozen paths, suppression ban, cognitive-complexity and line-length guards, plus lint and test results (Project Plan › Built-in tension against gaming). The δ = 1.0 and ε = 0.25 thresholds are tunable per project config; stricter requirements lower δ and/or raise ε. E5 (the blind readability review) will validate that accepted changes genuinely improve code; the pass bar is ≥80% judged better, <5% judged worse (Project Plan › Evaluation).
