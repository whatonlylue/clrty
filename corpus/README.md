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
