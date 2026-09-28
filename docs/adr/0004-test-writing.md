# 0004. Test writing

Date: 2026-09-28
Status: Accepted

## Context

Refactoring uncovered code is risky; behavior is harder to verify if tests don't exercise the changes. The planner ranks findings by coverage and skips uncovered code unless the characterization phase is on (Build plan › Agent loop internals › Preflight). The question is whether Clarity should author tests to enable refactoring sparse-coverage hotspots.

## Options considered

**Opt-in characterization phase, off by default:** When a hotspot has thin coverage, a separate agent writes tests into a dedicated directory. Tests must pass against the original code before they freeze. The refactoring agent never edits tests, maintaining separation of concerns (Project Plan › Agent mode › Characterization phase).

**Never let Clarity author tests:** Pure refactoring only; skip all uncovered code. Simpler but leaves refactoring opportunities on the table if coverage gaps exist.

## Decision

**Opt-in characterization phase, off by default. The refactoring agent never edits tests.** Users can enable characterization via config to improve coverage for targeted hotspots. Tests written in this phase are frozen and immutable by the main refactoring loop, preventing test corruption (Project Plan › Agent mode › Characterization phase).

## Consequences

Adds an optional P4 feature without complicating the v1 loop. Covered code gets refactored faster; users who need to handle sparse coverage enable characterization explicitly. The frozen-test guarantee means one agent writes them, another never touches them—a clear contract that avoids test-data erosion.
