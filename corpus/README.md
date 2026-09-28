# clrty evaluation corpus

Pinned code used to calibrate and evaluate clrty's SCB-style metrics (erosion, verbosity).

## Contents

| name | kind | pinned rev | subdir | files | Python LOC (non-blank) |
|---|---|---|---|---|---|
| click | human-oss | `8b19813f2bfca99f1018a587a8cf54fc959f2e5d` (8.5.0) | src/click | 17 | 10,292 |
| aiohttp | human-oss | `5e392ce0456f5235a4ee6ad46f0e806df2f15873` (v3.14.3) | aiohttp | 55 | 23,143 |
| rich | human-oss | `6ac483cbea39cab124dfd3483bba70ffafb71050` (v15.0.0) | rich | 100 | 35,180 |

Human repos give the low-erosion/low-verbosity side (SCB human means: erosion 0.31, verbosity 0.15). Domains: CLI, HTTP client/server, terminal rendering.

**SCB agent checkpoints: none yet.** SlopCodeBench (arXiv 2603.24755, github.com/SprocketLab/slop-code-bench) does not publish agent outputs or trajectories. The HF dataset `gabeorlanski/slopcodebench` (rev `5d067d6c497180081949cb9c0dc4502c9d750b1b`) holds only problem specs plus test runners, and the leaderboard has no per-trial artifacts. To add agent code, run `slop-code` yourself, publish a snapshot (git repo or sha256-pinned archive), and add a `kind = "scb-checkpoint"` entry; `fetch.py` supports both. Hidden tests live in the HF dataset `tests` column and github.com/gabeorlanski/scb-problems (`<problem>/tests/`); never copy them here.

## Fetch

    uv run corpus/fetch.py        # or: python3 corpus/fetch.py [name ...]

Stdlib only (Python 3.12). Idempotent; checkouts land in `corpus/repos/<name>/` (git-ignored). Prints Python LOC per entry (non-blank lines in `subdir`).

## Baseline scores (spike)

`clrty-spike score` at scb-check 0.1.3 (`adf82d88`), sloptrack 0.1.0 (`4ddd8693`), radon 6.0.1, Python 3.13, the committed `anchors.toml`. "whole" is the repo checkout, "lib" is `subdir` only. Raw values are lower-is-better; normalized (in parentheses) and composite are higher-is-better.

| repo | scope | LOC | composite | erosion | cog. erosion | verbosity | duplication | granularity (n) | structure (n) |
|---|---|---|---|---|---|---|---|---|---|
| click | whole | 17,615 | 81.21 | 0.290 (1.00) | 0.701 (0.50) | 0.127 (1.00) | 0.051 (0.91) | 0.84 | 0.66 |
| click | lib | 6,847 | 62.70 | 0.472 (0.74) | 0.762 (0.38) | 0.243 (0.70) | 0.066 (0.84) | 0.73 | 0.47 |
| aiohttp | whole | 69,241 | 71.84 | 0.257 (1.00) | 0.748 (0.40) | 0.209 (0.81) | 0.137 (0.51) | 0.97 | 0.73 |
| aiohttp | lib | 19,163 | 57.05 | 0.546 (0.62) | 0.843 (0.21) | 0.258 (0.65) | 0.073 (0.81) | 0.78 | 0.59 |
| rich | whole | 41,187 | 61.59 | 0.460 (0.76) | 0.879 (0.14) | 0.197 (0.85) | 0.030 (1.00) | 0.95 | 0.53 |
| rich | lib | 31,397 | 51.80 | 0.592 (0.55) | 0.887 (0.13) | 0.226 (0.75) | 0.015 (1.00) | 0.85 | 0.38 |

Scope matters more than repo. Whole-repo erosion for click and aiohttp lands at the SCB human mean (0.29 and 0.26 vs 0.31; rich 0.46) because tests and examples add many small flat functions; library-only erosion is 0.47-0.59 for all three. The SCB panel scored repos at HEAD, so "whole" is the like-for-like comparison with its human means, but E1 raters will judge library code. Pick one scope before building E1 pairs and score both sides of every pair with it.

Before the `-P` fix in `spike/src/clrty_spike/tools.py`, library-only scoring of click and rich silently fell back to the stand-in for granularity: both ship stdlib-named modules (click's `types.py`, rich's `abc.py`, `json.py` and `logging.py`) that shadowed the stdlib inside sloptrack. click lib scored 63.92 and rich lib 51.89. Repeated runs give identical scores.
