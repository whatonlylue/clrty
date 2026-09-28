# clrty

clrty scores code for the ways AI agents tend to degrade it (erosion, verbosity, duplication, granularity, structure) and, later, will run a behavior-preserving refactoring loop that only accepts changes the score says are better.

**Status: milestone M0.** A throwaway Python spike checks that the score tracks human judgment before the Rust engine is built. See [ADR 0001](docs/adr/0001-core-language.md).

## Layout

| Path | What |
|---|---|
| [`spike/`](spike/README.md) | P0 Python scorer wrapping scb-check, radon and sloptrack |
| [`corpus/`](corpus/README.md) | Pinned evaluation repos, fetch script, baseline scores |
| [`eval/ranking/`](eval/ranking/README.md) | Blind-ranking page and tally for experiments E1 and E5 |
| [`docs/adr/`](docs/adr/README.md) | Architecture decisions |
| `clrty/` | Rust crate, a stub until M1a |

## Quick start

```sh
(cd spike && uv sync)
python3 corpus/fetch.py
(cd spike && uv run clrty-spike score ../corpus/repos/click/src/click)
```

Setup from scratch, verify steps and project rules are in [AGENTS.md](AGENTS.md).

## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
