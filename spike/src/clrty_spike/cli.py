from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .score import score_path


def _diff(a: dict, b: dict) -> dict:
    """Per-family raw and normalized deltas from score `a` (before) to `b` (after)."""
    fams = {}
    for k in a["families"]:
        fa, fb = a["families"][k], b["families"].get(k, {})
        na, nb = fa.get("normalized"), fb.get("normalized")
        ra, rb = fa.get("raw"), fb.get("raw")
        fams[k] = {
            "normalized_before": na,
            "normalized_after": nb,
            "normalized_delta": None if na is None or nb is None else round(nb - na, 4),
            "raw_before": ra,
            "raw_after": rb,
            "raw_delta": round(rb - ra, 4) if isinstance(ra, (int, float)) and isinstance(rb, (int, float)) else None,
        }
    return {
        "composite_before": a["composite"],
        "composite_after": b["composite"],
        "composite_delta": round(b["composite"] - a["composite"], 2),
        "loc_before": a["loc"],
        "loc_after": b["loc"],
        "families": fams,
        "versions_match": a["versions"] == b["versions"],
    }


def _num(x) -> str:
    return f"{x:.4f}" if isinstance(x, (int, float)) else "-"


def _print_diff(d: dict) -> None:
    print(
        f"composite  {d['composite_before']:6.2f} -> {d['composite_after']:6.2f}  ({d['composite_delta']:+.2f})   "
        f"loc {d['loc_before']} -> {d['loc_after']}"
    )
    print(
        f"{'family':<18}{'raw before':>12}{'raw after':>12}{'raw d':>10}   {'norm before':>11}{'norm after':>11}"
        f"{'norm d':>9}"
    )
    for name, v in d["families"].items():
        if v["normalized_before"] is None and v["normalized_after"] is None:
            print(f"{name:<18}{'(null)':>12}")
            continue
        nd = v["normalized_delta"]
        print(
            f"{name:<18}{_num(v['raw_before']):>12}{_num(v['raw_after']):>12}{_num(v['raw_delta']):>10}   "
            f"{_num(v['normalized_before']):>11}{_num(v['normalized_after']):>11}"
            f"{'-' if nd is None else f'{nd:+.4f}':>9}"
        )
    print("(normalized: higher is better; composite: higher is better)")
    if not d["versions_match"]:
        print("WARNING: tool versions differ between the two runs; scores are not comparable")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="clrty-spike", description="P0 spike: one JSON score vector for a repo")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("score", help="score a path")
    s.add_argument("path")
    s.add_argument("--json", metavar="OUT", help="also write the JSON to this file (stdout always gets it)")
    s.add_argument("--anchors", help="alternative anchors.toml")
    d = sub.add_parser("diff", help="per-family delta between two paths")
    d.add_argument("before")
    d.add_argument("after")
    d.add_argument("--json", metavar="OUT", help="write the diff JSON to this file")
    d.add_argument("--anchors", help="alternative anchors.toml")
    args = ap.parse_args(argv)
    anchors = Path(args.anchors) if args.anchors else None
    if args.cmd == "score":
        res = score_path(args.path, anchors)
        text = json.dumps(res, indent=2)
        if args.json:
            Path(args.json).write_text(text + "\n")
        print(text)
    else:
        a, b = score_path(args.before, anchors), score_path(args.after, anchors)
        d = _diff(a, b)
        if args.json:
            Path(args.json).write_text(json.dumps({"before": a, "after": b, "diff": d}, indent=2) + "\n")
        _print_diff(d)
    return 0


if __name__ == "__main__":
    sys.exit(main())
