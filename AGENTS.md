# AGENTS.md

clrty scores code for agent-style degradation (erosion, verbosity, duplication, ...) and, later, runs a behavior-preserving refactoring loop. We are in milestone M0: a Python spike validates the score before the Rust engine is built.

## Setup (fresh container)

You need a Rust toolchain (edition 2024, so Rust >= 1.85) and `uv`. uv installs Python 3.13 itself.

```sh
# Rust, skip if `cargo --version` already works
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal
. "$HOME/.cargo/env"

# uv, skip if `uv --version` already works
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

# spike dependencies (scb-check and sloptrack install from GitHub at pinned SHAs, so network is required)
(cd spike && uv sync)
```

`mise.toml` is the maintainer's local tool config. Cloud agents don't need it.

## Verify

```sh
(cd clrty && cargo build)                      # Rust crate (a stub until M1a)
(cd spike && uv run pytest -q)                 # spike tests
(cd spike && uv run ruff check .. && uv run ruff format --check ..)  # lint + format, config in ruff.toml
python3 eval/ranking/tally.py --selftest       # ranking tally, stdlib only
```

Optional: `python3 corpus/fetch.py` clones the pinned evaluation repos (click, aiohttp, rich) into `corpus/repos/`, which is gitignored. Score one with `(cd spike && uv run clrty-spike score ../corpus/repos/click)`, or only its library code with `../corpus/repos/click/src/click` (the manifest's `subdir`). The two scopes give very different numbers; see `corpus/README.md`.

## Layout

| Path | What |
|---|---|
| `clrty/` | Rust crate; becomes the `clrty-*` workspace in M1a |
| `spike/` | P0 Python scorer wrapping scb-check, radon, sloptrack |
| `corpus/` | Pinned repo manifest, fetch script and baseline scores |
| `eval/ranking/` | Blind-ranking page and tally for experiments E1/E5 |
| `docs/adr/` | Architecture decisions. Read these before changing a decision they record |
| `ruff.toml` | Python lint and format config shared by `spike/`, `eval/` and `corpus/` |

## Rules

- The project name is `clrty` in code, commands, paths and prose. "Clarity" means only the unrelated Stacks language.
- Don't commit `corpus/repos/`, `target/`, `.venv/` or caches.
- Refactors of the spike must not change scores. Save `clrty-spike score` output for the fixtures and corpus before, rerun after, and diff.
- Don't tune anchors or weights in `spike/anchors.toml` to make a result look better. Changes need evidence from the corpus.
- The maintainer uses jj (colocated with git) locally. Plain git commits work fine from a cloud container.
- License: Apache-2.0.
