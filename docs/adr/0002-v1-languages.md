# 0002. v1 languages

Date: 2026-09-28
Status: Accepted

## Context

Clarity's rule packs and analyzers are language-specific. The SlopCodeBench rules for verbosity and erosion are already ported to Python and TypeScript, and tree-sitter grammars exist for many languages. The question is which languages to include in v1 versus deferring to later phases.

## Options considered

**Python + TypeScript (recommended):** Best rule coverage from the SCB port. Python and TypeScript are heavily used in agent-built codebases, and the rule packs are nearest to complete. Elixir deferred to P4.

**Add Elixir early:** Elixir is identified as "the third language for Miru dogfooding" (Build plan › Open questions). Adding it in P1d lets Miru test the tool sooner, but requires parallel rule development and grammar integration, extending P1d timeline.

## Decision

**Python + TypeScript in v1; Elixir as the P4 third language.** Python and TypeScript have the best existing rule coverage: 197 ast-grep rules for Python and 9 for TypeScript, plus Biome's lint support (Project Plan › Research findings › Existing tools). Elixir is pulled forward only if Miru dogfooding timing becomes critical (Build plan › Open questions); otherwise it lands in P4 after v0.1 is shipped.

## Consequences

Full rule coverage and parity checks for two languages in P1. The refactoring recipes and gate rules must handle both Python and TypeScript idioms. Elixir joins after foundation layers stabilize, reducing parallel complexity during P1–P3. If Miru needs it sooner, ADR can be reconsidered around week 8.
