# Blind ranking tool (E1, E5)

Raters see two code versions side by side, never told which is the original, and pick the clearer one.
E1: 40 before/after pairs, 3-4 raters; the score must agree with the majority on at least 75% of pairs.
E5: 30 accepted commits (parent vs. accepted) judged better / same / worse; bars are at least 80% better, under 5% worse.

## Files

- `pairs.schema.json`, `pairs.example.json`: pairs format and 5 sample pairs.
- `index.html`: the rating page (one file, no build; highlight.js loads from cdnjs, the page still works without it).
- `tally.py`: stdlib-only analysis. `example-results/` holds 3 fake results files for trying it out.

## 1. Prepare pairs

Write a JSON file following `pairs.schema.json`. Per pair: `id`, `language`, optional `context` (what the code is for; do not hint at what changed), and code strings `a` and `b`. Put the truth in `meta`:

    "meta": { "before": "a", "score_delta": 0.42 }

`before` says which side is the original. `score_delta` is score(after) - score(before), signed so positive means the score judges "after" clearer (0 = tie). E5 needs only `meta.before` (set `score_delta` to 0). Randomize which of a/b holds "before" when you generate the file, though the page also randomizes sides per rater.

Keep this full file private. Make the public copy without meta:

    python3 tally.py --strip pairs.json > pairs.public.json

## 2. Send it to raters

- Local file: send `index.html` and `pairs.public.json`. The rater opens `index.html`, picks the JSON via the file picker.
- Static host (GitHub Pages, Netlify, any web server): upload both files side by side and share `https://host/path/index.html?pairs=pairs.public.json`. (`?pairs=` needs http(s); from `file://` browsers block the fetch, so use the picker.)

The rater enters a name, then per pair chooses "Left is clearer" / "About the same" / "Right is clearer" (keys `1`/`2`/`3` or Left/Down/Right arrows; `B` goes back), with an optional comment. Order and left/right sides are shuffled per rater from a random seed that is saved in the output. Progress is stored in that browser's localStorage, so a refresh resumes where they left off (same browser, same name, same pairs file). At the end (or any time) they click "Download results" and send you `results-<name>.json`. The page never shows before/after or scores.

## 3. Tally

    python3 tally.py pairs.json results-*.json          # E1
    python3 tally.py --e5 pairs.json results-*.json     # E5
    python3 tally.py --bar 0.8 pairs.json results-*.json  # different E1 bar

Use the full pairs file (with meta). Results are mapped to before/after via meta, not via the raters' files.

E1 output: per-pair majority (before/after/tie votes; a split with no unique plurality counts as tie), score direction vs. majority, agreement rate against the 75% bar (all pairs, where a majority tie matches a zero delta; also shown excluding majority ties), Fleiss' kappa over pairs rated by every rater (undefined with fewer than 2 raters), and the list of disagreeing pairs.

The score counts as a tie when `|score_delta| < T` (`--tie-threshold T`, default 0.25, the gate's epsilon), since real composite deltas are never exactly 0; the threshold is printed in the report header.

E5 output: % better / same / worse per commit majority (plus pooled votes) against the bars.
