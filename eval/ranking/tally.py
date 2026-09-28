#!/usr/bin/env python3
"""Tally blind-ranking results for clrty experiments E1 and E5. Stdlib only.

  tally.py pairs.json results-*.json            # E1: score vs. human majority
  tally.py --e5 pairs.json results-*.json       # E5: % better / % worse
  tally.py --strip pairs.json > public.json     # remove hidden meta before sending
"""
import argparse
import json
import sys

CATS = ("before", "after", "tie")


def load_pairs(path):
    with open(path) as f:
        data = json.load(f)
    return {p["id"]: p for p in data["pairs"]}


def votes_from(path, pairs):
    """Return (rater, {pair_id: 'before'|'after'|'tie'}). Uses meta, not the file's own 'better'."""
    with open(path) as f:
        doc = json.load(f)
    out = {}
    for r in doc["results"]:
        p = pairs.get(r["id"])
        if p is None:
            print(f"warning: {path}: unknown pair id {r['id']!r}, skipped", file=sys.stderr)
            continue
        before = p["meta"]["before"]
        w = r["winner"]
        out[r["id"]] = "tie" if w == "tie" else ("before" if w == before else "after")
    return doc.get("rater", path), out


def majority(counts):
    """Strict plurality among before/after/tie; any tie for first place counts as 'tie'."""
    top = max(counts.values())
    leaders = [c for c in CATS if counts[c] == top]
    return leaders[0] if len(leaders) == 1 else "tie"


def fleiss_kappa(rows):
    """rows: list of {cat: count}, every row with the same rater total n."""
    N = len(rows)
    if N == 0:
        return None
    n = sum(rows[0].values())
    if n < 2:
        return None
    p_j = [sum(r[c] for r in rows) / (N * n) for c in CATS]
    P_i = [(sum(r[c] * r[c] for c in CATS) - n) / (n * (n - 1)) for r in rows]
    P_bar = sum(P_i) / N
    P_e = sum(p * p for p in p_j)
    if P_e == 1:
        return None
    return (P_bar - P_e) / (1 - P_e)


TIE_THRESHOLD = 0.25


def score_dir(delta, tie=None):
    """Score direction; |delta| < tie threshold counts as a tie."""
    t = TIE_THRESHOLD if tie is None else tie
    if abs(delta) < t:
        return "tie"
    return "after" if delta > 0 else "before"


def pct(x, n):
    return f"{100 * x / n:.1f}%" if n else "n/a"


def cmd_strip(args):
    with open(args.pairs) as f:
        data = json.load(f)
    for p in data["pairs"]:
        p.pop("meta", None)
    json.dump(data, sys.stdout, indent=2)
    print()


def main():
    global TIE_THRESHOLD
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pairs", nargs="?", help="pairs file (with meta)")
    ap.add_argument("results", nargs="*", help="results files, one per rater")
    ap.add_argument("--e5", action="store_true", help="E5 mode: report %% better / %% worse")
    ap.add_argument("--strip", action="store_true", help="print the pairs file without meta and exit")
    ap.add_argument("--tie-threshold", type=float, default=TIE_THRESHOLD, metavar="T",
                    help="score counts as a tie when |score_delta| < T (default 0.25, the gate's epsilon)")
    ap.add_argument("--selftest", action="store_true", help="run the built-in unit tests and exit")
    ap.add_argument("--bar", type=float, default=0.75, help="E1 agreement pass bar (default 0.75)")
    args = ap.parse_args()

    if args.selftest:
        import unittest
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(SelfTest)
        sys.exit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())
    if not args.pairs:
        ap.error("pairs file required")
    TIE_THRESHOLD = args.tie_threshold
    if args.strip:
        return cmd_strip(args)
    if not args.results:
        ap.error("need at least one results file")

    pairs = load_pairs(args.pairs)
    raters = {}
    for path in args.results:
        name, v = votes_from(path, pairs)
        if name in raters:
            name = f"{name} ({path})"
        raters[name] = v

    print(f"Score tie threshold: |score_delta| < {TIE_THRESHOLD} counts as tie")
    print(f"Raters ({len(raters)}): " + ", ".join(f"{n} [{len(v)}/{len(pairs)} pairs]" for n, v in raters.items()))

    # per-pair vote counts over the raters who answered it
    counts = {}
    for pid in pairs:
        c = {k: 0 for k in CATS}
        for v in raters.values():
            if pid in v:
                c[v[pid]] += 1
        if sum(c.values()):
            counts[pid] = c
    unrated = len(pairs) - len(counts)
    if unrated:
        print(f"Pairs with no votes (excluded): {unrated}")
    maj = {pid: majority(c) for pid, c in counts.items()}

    if args.e5:
        return report_e5(counts, maj)
    return report_e1(pairs, raters, counts, maj, args.bar)


def report_e1(pairs, raters, counts, maj, bar):
    print(f"Pairs judged: {len(counts)}\n")
    print("Per-pair majority (before / after / tie votes):")
    for pid, c in counts.items():
        delta = pairs[pid]["meta"].get("score_delta")
        s = score_dir(delta) if delta is not None else "n/a"
        print(f"  {pid:<12} {c['before']}/{c['after']}/{c['tie']}  majority={maj[pid]:<6} score={s:<6} (delta={delta})")

    scored = [pid for pid in counts if pairs[pid]["meta"].get("score_delta") is not None]
    agree = [pid for pid in scored if score_dir(pairs[pid]["meta"]["score_delta"]) == maj[pid]]
    dis = [pid for pid in scored if pid not in agree]
    decisive = [pid for pid in scored if maj[pid] != "tie"]
    agree_dec = [pid for pid in decisive if score_dir(pairs[pid]["meta"]["score_delta"]) == maj[pid]]

    print(f"\nMajority: before better {sum(m == 'before' for m in maj.values())}, "
          f"after better {sum(m == 'after' for m in maj.values())}, tie {sum(m == 'tie' for m in maj.values())}")
    n = len(scored)
    rate = len(agree) / n if n else 0.0
    print(f"\nScore vs. majority agreement (all pairs, tie matches tie): {len(agree)}/{n} = {pct(len(agree), n)}")
    print(f"Score vs. majority agreement (excluding majority ties):    {len(agree_dec)}/{len(decisive)} = {pct(len(agree_dec), len(decisive))}")
    print(f"Pass bar {bar:.0%} on all-pairs agreement: {'PASS' if n and rate >= bar else 'FAIL'}")

    # Fleiss' kappa over pairs rated by every rater
    full = [c for pid, c in counts.items() if sum(c.values()) == len(raters)]
    k = fleiss_kappa(full) if len(raters) >= 2 else None
    if k is None:
        print(f"\nFleiss' kappa: n/a (need >=2 raters and non-degenerate votes; {len(full)} pairs rated by all)")
    else:
        print(f"\nFleiss' kappa: {k:.3f} over {len(full)} pairs rated by all {len(raters)} raters ({kappa_label(k)})")

    print(f"\nDisagreeing pairs ({len(dis)}):")
    for pid in dis:
        c = counts[pid]
        print(f"  {pid}: score says {score_dir(pairs[pid]['meta']['score_delta'])}, humans say {maj[pid]} "
              f"(before {c['before']}, after {c['after']}, tie {c['tie']})")
    if not dis:
        print("  none")


def kappa_label(k):
    for lim, lab in ((0, "poor"), (0.2, "slight"), (0.4, "fair"), (0.6, "moderate"), (0.8, "substantial")):
        if k <= lim:
            return lab
    return "almost perfect"


def report_e5(counts, maj):
    n = len(counts)
    better = sum(m == "after" for m in maj.values())
    worse = sum(m == "before" for m in maj.values())
    same = n - better - worse
    print(f"Commits judged: {n}  (per-commit majority; ties count as 'same')")
    print(f"  better: {better} ({pct(better, n)})   same: {same} ({pct(same, n)})   worse: {worse} ({pct(worse, n)})")
    tot = {k: sum(c[k] for c in counts.values()) for k in CATS}
    t = sum(tot.values())
    print(f"Pooled individual votes ({t}): better {pct(tot['after'], t)}, same {pct(tot['tie'], t)}, worse {pct(tot['before'], t)}")
    ok_b = n and better / n >= 0.80
    ok_w = n and worse / n < 0.05
    print(f"Bar >=80% better: {'PASS' if ok_b else 'FAIL'}")
    print(f"Bar <5% worse:    {'PASS' if ok_w else 'FAIL'}")
    bad = [pid for pid, m in maj.items() if m == "before"]
    print(f"Commits judged worse: {', '.join(bad) if bad else 'none'}")
    print("(E5 note: side 'before' = parent commit, 'after' = accepted commit.)")


import unittest


class SelfTest(unittest.TestCase):
    def _e1(self, delta, votes):
        """Run report_e1 on one pair; return (agree_count, printed text)."""
        import io
        from contextlib import redirect_stdout
        pairs = {"p": {"meta": {"before": "a", "score_delta": delta}}}
        c = {k: votes.count(k) for k in CATS}
        buf = io.StringIO()
        with redirect_stdout(buf):
            report_e1(pairs, {r: {} for r in "xyz"}, {"p": c}, {"p": majority(c)}, 0.75)
        return buf.getvalue()

    def test_tie_majority_small_delta_agrees(self):
        out = self._e1(0.1, ["tie", "tie", "after"])
        self.assertIn("1/1 = 100.0%", out)
        self.assertIn("Disagreeing pairs (0)", out)

    def test_humans_disagree_with_score(self):
        out = self._e1(0.6, ["before", "before", "after"])
        self.assertIn("0/1 = 0.0%", out)
        self.assertIn("Disagreeing pairs (1)", out)

    def test_threshold_boundary(self):
        self.assertEqual(score_dir(0.25, 0.25), "after")
        self.assertEqual(score_dir(-0.24, 0.25), "tie")


if __name__ == "__main__":
    main()
