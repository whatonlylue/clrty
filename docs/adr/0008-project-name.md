# 0008. Project and binary name

Date: 2026-09-28
Status: Accepted

## Context

Two naming problems exist:

**(a) Taken on registries:** The name "clarity" is already claimed by unrelated packages on crates.io (Ethereum client by Althea), PyPI (Python logger by singhsays), and npm (string obfuscation utility by DamonOehlman). Using it would create install confusion across these ecosystems.

**(b) Search ambiguity:** "Clarity" is a well-known smart-contract language on the Stacks blockchain. A tool named "clarity" causes ambiguity in developer searches and documentation. The Stacks toolchain installs `clarinet` (testing framework) and `stacks-node`, not a `clarity` binary ([clarinet Cargo.toml](https://github.com/stx-labs/clarinet/blob/main/components/clarinet-cli/Cargo.toml#L30)), so a `clarity` binary does not clash on PATH.

A unique package name is required for distribution. The name should:
- Be short and suggest code quality or clarity
- Be available on crates.io, PyPI, npm, and Homebrew
- Avoid well-known tools with the same name
- Allow the binary to be named `clarity` for user ergonomics, matching the pattern used by ripgrep (package `ripgrep`, binary `rg`) or fd (package `fd-find`, binary `fd`)

## Findings

| Name | crates.io | PyPI | npm | Homebrew | Notes |
|------|-----------|------|-----|----------|-------|
| **clarity** | Taken | Taken | Taken | Available | Ethereum client (althea-net), Python logger (singhsays), string util (DamonOehlman). All active or recent. |
| **clarity-cli** | Available | Taken | Taken | Available | PyPI: test management CLI (cyclarity). Unrelated purpose. |
| **claritee** | Available | Available | Available | Available | Clear + tee. Suggests clarity. Short. |
| **clarify-code** | Available | Available | Available | Available | Explicit intent. More descriptive. |
| **slop-check** | Available | Available | Available | Available | Specific to scoring AI residue. Clear purpose. |
| **clrty** | Available | Available | Available | Available | **CHOSEN.** Vowelless form. No search collision. Short to type. |
| clariti | Available | Available | Available | Available | Misspelling variant. Free. |
| klariti | Available | Available | Available | Available | Misspelling variant. Free. |
| klaritee | Available | Available | Available | Available | Misspelling variant. Free. |
| clarety | Available | Available | Available | Available | Misspelling variant. Free. |
| clarrity | Available | Available | Available | Available | Misspelling variant. Free. |
| klarity | Taken | Taken | Taken | Available | Taken on PyPI and npm. |
| clairity | Available | Available | Taken | Available | Taken on npm. |
| klarify | Available | Taken | Available | Available | Taken on PyPI. |
| slopscore | Available | Taken | Taken | Available | PyPI/npm: "scores AI residue" (existing competitor). |
| unslop | Taken | Taken | Taken | Available | Crates + PyPI + npm: essay/doc linter for AI patterns. Active. |
| desloppify | Available | Taken | Taken | Available | PyPI/npm: "codebase health scanner." Occupied. |

## Decision

**Package name: `clrty`; binary: `clrty`**

`clrty` is a vowelless form following the style of `rg` (ripgrep) and `fd`. It is available on all four registries, eliminates search collision with the Stacks Clarity language, and is short to type. Using the same name for package and binary removes confusion and packaging overhead. The project's prose and display name remains "Clarity" to maintain recognizability in documentation and marketing (e.g., "clrty (Clarity)" on first reference). Trade-off: harder to say aloud and to guess from hearing alone, so documentation should clarify the pronunciation and spelling.

## Consequences

- Users install via `cargo install clrty`, `pip install clrty`, `npm install -g clrty`, or `brew install clrty`
- The binary is invoked as `clrty <command>` everywhere
- Configuration file remains `clarity.toml` unless decided otherwise (rename to `clrty.toml` in later work)
- Workspace crate names remain `clarity-*` for now; rename to `clrty-*` in M1a when workspace is created
- **Package name collision:** Avoided; no registry conflict
- **Search ambiguity:** Eliminated; vowelless form has no overlap with Stacks Clarity language
- **PATH collision:** None; Stacks tools use `clarinet` and `stacks-node`

### Existing competitors to position against

- **slopscore** (PyPI, npm): Heuristic linter scoring AI residue in commits and PRs with evidence
- **unslop** (crates.io): Deterministic linter finding AI writing patterns in essays, posts, email, reports, docs
- **desloppify** (PyPI, npm): Multi-language codebase health scanner and technical debt tracker
