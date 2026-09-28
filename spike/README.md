# clrty-spike (P0, throwaway)

Wraps three existing tools and emits ONE JSON score vector for a path. Purpose: test whether the clrty
score tracks human judgment before any engine is built. Correctness and transparency over polish.

## Install / run

```bash
cd spike
uv sync                                   # installs pinned deps (Python 3.12/3.13; scb-check needs >=3.12)
uv run clrty-spike score <path> [--json out.json]
uv run clrty-spike diff <before_path> <after_path> [--json out.json]
uv run pytest -q
```

`score` prints the JSON (and also writes it to `--json`). `diff` prints per-family raw and normalized deltas plus
the composite delta, and warns if tool versions differ between the two runs.

## Pins (recorded in every report under `versions`)

| Tool | Pin | Source |
|---|---|---|
| scb-check 0.2.0 | git `a8618228939def726c2ec48b354693e5aa1999d5` | github.com/gabeorlanski/scb-check (not on PyPI) |
| sloptrack 0.1.0 | git `4ddd8693f66912fba85e74acd5467f564896043a` | github.com/kennyfrc/sloptrack (not on PyPI) |
| radon | 6.0.1 | PyPI |

Bumping any pin, `anchors.toml`, or the stand-in code changes scores: do not compare across versions.

## Score conventions

- Raw metrics are lower-is-better. `normalized = clamp((b - m) / (b - g), 0, 1)` (plan formula), so
  **1.0 = at/better than the good anchor, 0.0 = at/worse than the bad anchor**. Higher is better.
- `composite = 100 * exp(sum w_i * ln(max(n_i, 0.01)))`; 100 = all families good, floor is 1.
- Weights: erosion 0.2, verbosity 0.2, duplication 0.15; remaining weight split evenly across the other
  *present* families; all renormalised to sum to 1. Null families are excluded.
- Anchors live in `anchors.toml`; each is marked calibrated or UNCALIBRATED.
- Hotspots: top 10 located findings, ranked by `contribution` = family weight x the finding's share of that
  family's numerator (e.g. its share of total CC mass). Rough, but comparable across families.

## Families

| Family | Measures | Source | Status |
|---|---|---|---|
| erosion | share of CC-mass (`CC*sqrt(SLOC)`) in functions with CC > 10 | scb-check | real |
| cognitive_erosion | same with cognitive complexity > 10 (plan says 15; scb-check uses 10) | scb-check | real, anchors uncalibrated |
| verbosity | (ast-grep-rule-flagged UNION clone lines) / LOC | scb-check | real |
| duplication | clone_loc / LOC (scb-check clone detector) | scb-check | real, but only Type 1/2-ish; no near-miss tier, no exact/renamed split |
| granularity | mean of: share of used callables with exactly one call site (sloptrack) and share of trivial wrappers (`return f(params...)`) | sloptrack + `ast` | single-use share real; trivial-wrapper share is a clrty-spike `ast` STAND-IN (sloptrack has no wrapper detector) |
| structure | mean of: p95 nesting depth, p95 function SLOC, share of functions with >5 params, share of files >500 SLOC (counts also reported) | `ast` | STAND-IN, anchors uncalibrated |
| coupling | | | null (not implemented) |
| hygiene | | | null (not implemented) |

radon is reported in an informational `radon` block (raw LOC/SLOC, mean/max CC, maintainability index, and an
erosion cross-check using radon's CC). It does not feed the composite.

## Known gaps

- Cognitive erosion deviates from the plan: scb-check's threshold is cognitive complexity > 10, the plan says 15.
- Anchors other than erosion/verbosity are placeholders. The erosion bad anchor is 0.936 (0.68+1.28*0.20), not the
  0.88 quoted in the brief; edit `anchors.toml` to change it.
- scb-check is run with `--include-all`, exactly as SlopCodeBench's own harness runs it (it pins scb-check 0.1.3;
  we pin a later git SHA). Without the flag, informational rules and `# scbc`-suppressed findings are hidden and
  verbosity drops by roughly 30-50% on real repos. `--include-all` also scans gitignored files, while the `ast`
  passes skip hidden/venv/build dirs, so an in-tree `.venv` would be seen by scb-check only.
- Tests and vendored code inside a repo are scored like any other code.
- scb-check has no per-finding JSON, so hotspot locations are parsed from its human-readable output (brittle
  across scb-check versions; the pin protects us).
- sloptrack is run with `--no-uvx --no-git`; grammars come from scb-check's pinned tree-sitter deps rather than
  sloptrack's default unpinned throwaway uvx environment.
- Python only. Single-use detection is sloptrack's name-based call graph (ambiguous names can be miscounted).
- Structure and trivial-wrapper thresholds are a guess; nothing here has been validated against human judgment yet.
