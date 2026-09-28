"""Build the score vector for a path.

Each `_family_*` helper returns its family entries and records located findings in a `Hotspots`. Hotspots are
collected in a fixed order (erosion, cognitive erosion, clones, granularity, structure); ties in the final ranking
keep that order, so do not reorder the calls in `score_path`.
"""

from __future__ import annotations

import platform
from pathlib import Path

from . import __version__, astmetrics, tools
from .astmetrics import Func
from .scoring import ANCHORS_PATH, composite, load_anchors, normalize, weights_for

TOP_HOTSPOTS = 10
CONVENTIONS = (
    "normalized: 1.0 = at/better than good anchor, 0.0 = at/worse than bad anchor. "
    "composite: 100 = all families good. Higher is better."
)


def _norm(value: float, anchor: dict) -> float:
    return normalize(value, anchor["good"], anchor["bad"])


def _family(raw, norm: float | None, source: str, **extra) -> dict:
    return {"raw": raw, "normalized": None if norm is None else round(norm, 4), "source": source, **extra}


def _null_family(reason: str) -> dict:
    return {"raw": None, "normalized": None, "source": None, "note": reason}


class Hotspots:
    """Located findings. `share` is the finding's share of its family's numerator; the family weight is applied
    once weights are known, in `top`."""

    def __init__(self) -> None:
        self._items: list[tuple[dict, float]] = []

    def add(self, file, symbol, start, end, family, detail, share) -> None:
        item = {
            "file": file,
            "symbol": symbol,
            "start_line": start,
            "end_line": end,
            "family": family,
            "detail": detail,
        }
        self._items.append((item, share))

    def top(self, weights: dict[str, float], n: int = TOP_HOTSPOTS) -> list[dict]:
        scored = [(item, weights.get(item["family"], 0.0) * share) for item, share in self._items]
        scored.sort(key=lambda pair: -pair[1])
        return [{**item, "contribution": round(score, 5)} for item, score in scored[:n]]


def _end_line(span: dict, file: str, line: int, fallback: int) -> int:
    fn = span.get((file, line))
    return fn.end if fn else fallback


# ---------------------------------------------------------------- scb-check families
def _family_scb(root: Path, anchors: dict, span: dict, hotspots: Hotspots, errors: dict) -> tuple[dict, int | None]:
    """Erosion, cognitive erosion, verbosity and duplication. Returns (families, total LOC or None on failure)."""
    try:
        scb = tools.scb_json(root)
        found = tools.scb_findings(root, root)
    except tools.ToolError as e:
        errors["scb-check"] = str(e)
        names = ("erosion", "cognitive_erosion", "verbosity", "duplication")
        return {k: _null_family(str(e)) for k in names}, None

    total_loc = scb["total_loc"]
    duplication = scb["clone_loc"] / total_loc if total_loc else 0.0
    fams = {
        "erosion": _family(
            scb["erosion"],
            _norm(scb["erosion"], anchors["erosion"]),
            "scb-check",
            high_cc_functions=scb["high_cc_functions"],
            total_functions=scb["total_functions"],
        ),
        "cognitive_erosion": _family(
            scb["cog_erosion"],
            _norm(scb["cog_erosion"], anchors["cognitive_erosion"]),
            "scb-check",
            note="scb-check cognitive complexity > 10 (plan says 15); anchors uncalibrated",
        ),
        "verbosity": _family(
            scb["verbosity"],
            _norm(scb["verbosity"], anchors["verbosity"]),
            "scb-check",
            flagged_loc=scb["verbosity_flagged_loc"],
            clone_loc=scb["clone_loc"],
            ast_grep_flagged_loc=scb["ast_grep_flagged_loc"],
            structural_rule_loc=scb.get("structural_rule_loc"),
        ),  # absent in scb-check 0.1.3 -> null
        "duplication": _family(
            duplication,
            _norm(duplication, anchors["duplication"]),
            "scb-check",
            note="clone_loc / total_loc; exact+renamed only, no near-miss (Type 3) tier, no exact/renamed split",
        ),
    }

    for key, family, mass, label in (
        ("erosion", "erosion", scb["total_mass"], "CC {c}, {s} SLOC, {p:.0%} of total CC mass"),
        (
            "cog_erosion",
            "cognitive_erosion",
            scb["total_cog_mass"],
            "cognitive complexity {c}, {s} SLOC, {p:.0%} of total cognitive mass",
        ),
    ):
        for f in found[key]:
            share = f["complexity"] * f["sloc"] ** 0.5 / mass if mass else 0
            end = _end_line(span, f["file"], f["line"], f["line"] + f["sloc"])
            hotspots.add(
                f["file"],
                f["symbol"],
                f["line"],
                end,
                family,
                label.format(c=f["complexity"], s=f["sloc"], p=share),
                share,
            )

    for g in found["clones"]:
        share = g["lines"] * g["instances"] / total_loc if total_loc else 0
        (first_file, first_line), *others = g["locations"]
        also = ", ".join(f"{file}:{line}" for file, line in others)
        hotspots.add(
            first_file,
            None,
            first_line,
            first_line + g["lines"] - 1,
            "duplication",
            f"{g['lines']}-line block duplicated {g['instances']}x; also at {also}",
            share,
        )
    return fams, total_loc


# ---------------------------------------------------------------- granularity
def _family_granularity(
    root: Path, anchors: dict, funcs: list[Func], span: dict, hotspots: Hotspots, errors: dict
) -> dict:
    """sloptrack single-use share averaged with the `ast` trivial-wrapper share (wrappers alone if sloptrack fails)."""
    try:
        sloptrack = tools.sloptrack_json(root)
    except tools.ToolError as e:
        errors["sloptrack"] = str(e)
        sloptrack = None

    wrappers = [f for f in funcs if f.trivial_wrapper]
    wrapper_share = len(wrappers) / len(funcs) if funcs else 0.0
    n_wrapper = _norm(wrapper_share, anchors["granularity"]["trivial_wrapper_share"])

    if sloptrack and "granularity" in sloptrack:
        g = sloptrack["granularity"]
        n_single = _norm(g["value"], anchors["granularity"]["single_use_share"])
        fam = _family(
            {"single_use_share": g["value"], "trivial_wrapper_share": round(wrapper_share, 4)},
            (n_single + n_wrapper) / 2,
            "sloptrack (single_use_share) + clrty-spike ast STAND-IN (trivial_wrapper_share)",
            single_use_functions=g["single_use_functions"],
            used_functions=g["used_functions"],
            trivial_wrappers=len(wrappers),
            functions=len(funcs),
            normalized_parts={"single_use_share": round(n_single, 4), "trivial_wrapper_share": round(n_wrapper, 4)},
        )
        used = g["used_functions"] or 1
        for e in g.get("single_use_top", []):
            end = _end_line(span, e["file"], e["line"], e["line"] + e["sloc"] - 1)
            hotspots.add(
                e["file"],
                e["name"],
                e["line"],
                end,
                "granularity",
                "callable with exactly one call site (sloptrack)",
                1 / used,
            )
    else:
        fam = _family(
            {"trivial_wrapper_share": round(wrapper_share, 4)},
            n_wrapper,
            "clrty-spike ast STAND-IN only (sloptrack failed)",
            note=errors.get("sloptrack", "sloptrack returned no granularity"),
        )

    for f in wrappers:
        hotspots.add(
            f.file,
            f.name,
            f.start,
            f.end,
            "granularity",
            "trivial wrapper: body only forwards its params",
            1 / len(funcs),
        )
    return fam


# ---------------------------------------------------------------- structure
def _family_structure(anchors: dict, funcs: list[Func], file_sloc: dict[str, int], hotspots: Hotspots) -> dict:
    """Mean of four `ast` sub-metrics: p95 nesting, p95 function SLOC, many-param share, big-file share."""
    a = anchors["structure"]
    many_params = [f for f in funcs if f.params > 5]
    big_files = {k: v for k, v in file_sloc.items() if v > 500}
    sub = {
        "nesting_p95": astmetrics.p95([f.nesting for f in funcs]),
        "function_sloc_p95": astmetrics.p95([f.sloc for f in funcs]),
        "many_params_share": len(many_params) / len(funcs) if funcs else 0.0,
        "big_file_share": len(big_files) / len(file_sloc) if file_sloc else 0.0,
    }
    parts = {k: _norm(v, a[k]) for k, v in sub.items()}
    fam = _family(
        {
            **{k: round(v, 4) for k, v in sub.items()},
            "functions_gt5_params": len(many_params),
            "files_gt500_sloc": len(big_files),
        },
        sum(parts.values()) / len(parts),
        "clrty-spike ast STAND-IN",
        normalized_parts={k: round(v, 4) for k, v in parts.items()},
    )

    if funcs:
        share = 1 / len(funcs)
        for f in sorted(funcs, key=lambda f: -f.nesting)[:5]:
            if f.nesting > a["nesting_p95"]["good"]:
                hotspots.add(f.file, f.name, f.start, f.end, "structure", f"nesting depth {f.nesting}", share)
        for f in sorted(funcs, key=lambda f: -f.sloc)[:5]:
            if f.sloc > a["function_sloc_p95"]["good"]:
                hotspots.add(f.file, f.name, f.start, f.end, "structure", f"{f.sloc} SLOC function", share)
        for f in many_params:
            hotspots.add(f.file, f.name, f.start, f.end, "structure", f"{f.params} parameters", share)
    for file, sloc in big_files.items():
        hotspots.add(file, None, 1, sloc, "structure", f"file has {sloc} SLOC (> 500)", 1 / max(len(file_sloc), 1))
    return fam


# ---------------------------------------------------------------- radon (informational)
def _radon_info(root: Path, funcs: list[Func], errors: dict) -> dict | None:
    """radon summary plus an erosion cross-check using radon's CC. Not part of the composite."""
    info = None
    try:
        info = tools.radon_summary(root)
        by_fn = {(file, b.lineno): b for file, b in info.pop("_blocks")}
        total = high = 0.0
        for f in funcs:
            b = by_fn.get((f.file, f.start))
            if not b:
                continue
            mass = b.complexity * max(f.sloc, 1) ** 0.5
            total += mass
            high += mass if b.complexity > 10 else 0
        info["erosion_crosscheck"] = round(high / total, 4) if total else 0.0
        info["erosion_crosscheck_note"] = "same formula as SCB erosion but radon CC; informational only"
    except Exception as e:
        errors["radon"] = repr(e)
    return info


def _versions(anchors_path: Path | None) -> dict:
    return {
        "spike": __version__,
        "scb-check": tools.dist_version("scb-check"),
        "radon": tools.dist_version("radon"),
        "sloptrack": tools.dist_version("sloptrack") + " (real tool; granularity single-use only)",
        "granularity_trivial_wrapper": "clrty-spike ast stand-in",
        "structure": "clrty-spike ast stand-in",
        "python": platform.python_version(),
        "anchors": (ANCHORS_PATH if anchors_path is None else Path(anchors_path)).name,
    }


# ---------------------------------------------------------------- entry point
def score_path(path: str | Path, anchors_path: Path | None = None) -> dict:
    root = Path(path).resolve()
    if not root.exists():
        raise FileNotFoundError(root)
    anchors = load_anchors(anchors_path)
    errors: dict = {}
    hotspots = Hotspots()

    funcs, file_sloc, parse_failed = astmetrics.collect(root)
    span = {(f.file, f.start): f for f in funcs}

    fams, loc = _family_scb(root, anchors, span, hotspots, errors)
    fams["granularity"] = _family_granularity(root, anchors, funcs, span, hotspots, errors)
    fams["structure"] = _family_structure(anchors, funcs, file_sloc, hotspots)
    fams["coupling"] = _null_family("not implemented in spike")
    fams["hygiene"] = _null_family("not implemented in spike")
    radon_info = _radon_info(root, funcs, errors)

    present = [k for k, v in fams.items() if v["normalized"] is not None]
    weights = weights_for(present, anchors)
    for k, fam in fams.items():
        fam["weight"] = round(weights[k], 4) if k in weights else None

    out = {
        "versions": _versions(anchors_path),
        "path": str(root),
        "loc": loc if loc is not None else sum(file_sloc.values()),
        "files": {"python_files_parsed": len(file_sloc), "parse_failures": parse_failed},
        "conventions": CONVENTIONS,
        "families": fams,
        "composite": round(composite({k: fams[k]["normalized"] for k in present}, weights), 2),
        "hotspots": hotspots.top(weights),
        "radon": radon_info,
    }
    if errors:
        out["errors"] = errors
    return out
