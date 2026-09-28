"""Build the score vector for a path."""
from __future__ import annotations

import platform
from pathlib import Path

from . import __version__, astmetrics, tools
from .scoring import ANCHORS_PATH, composite, load_anchors, normalize, weights_for


def _fam(raw, norm, source, **extra):
    d = {"raw": raw, "normalized": None if norm is None else round(norm, 4), "source": source}
    d.update(extra)
    return d


def _null(reason):
    return {"raw": None, "normalized": None, "source": None, "note": reason}


def score_path(path: str | Path, anchors_path: Path | None = None) -> dict:
    root = Path(path).resolve()
    if not root.exists():
        raise FileNotFoundError(root)
    A = load_anchors(anchors_path)
    fams: dict = {}
    errors: dict = {}
    hotspots: list[dict] = []
    contrib_w = {}  # filled after weights known; hotspots store raw share, weight applied later

    def hs(file, symbol, start, end, family, detail, share):
        hotspots.append({"file": file, "symbol": symbol, "start_line": start, "end_line": end,
                         "family": family, "detail": detail, "_share": share})

    funcs, file_sloc, parse_failed = astmetrics.collect(root)
    span = {(f.file, f.start): f for f in funcs}
    n_funcs = len(funcs)

    # ---- scb-check: erosion, cognitive erosion, verbosity, duplication
    scb = None
    try:
        scb = tools.scb_json(root)
        found = tools.scb_findings(root, root)
    except tools.ToolError as e:
        errors["scb-check"] = str(e)
        found = {"erosion": [], "cog_erosion": [], "clones": []}
    loc = scb["total_loc"] if scb else sum(file_sloc.values())
    if scb:
        a = A["erosion"]
        fams["erosion"] = _fam(scb["erosion"], normalize(scb["erosion"], a["good"], a["bad"]), "scb-check",
                               high_cc_functions=scb["high_cc_functions"], total_functions=scb["total_functions"])
        a = A["cognitive_erosion"]
        fams["cognitive_erosion"] = _fam(
            scb["cog_erosion"], normalize(scb["cog_erosion"], a["good"], a["bad"]), "scb-check",
            note="scb-check cognitive complexity > 10 (plan says 15); anchors uncalibrated")
        a = A["verbosity"]
        fams["verbosity"] = _fam(scb["verbosity"], normalize(scb["verbosity"], a["good"], a["bad"]), "scb-check",
                                 flagged_loc=scb["verbosity_flagged_loc"], clone_loc=scb["clone_loc"],
                                 ast_grep_flagged_loc=scb["ast_grep_flagged_loc"],
                                 structural_rule_loc=scb["structural_rule_loc"])
        dup = scb["clone_loc"] / scb["total_loc"] if scb["total_loc"] else 0.0
        a = A["duplication"]
        fams["duplication"] = _fam(dup, normalize(dup, a["good"], a["bad"]), "scb-check",
                                   note="clone_loc / total_loc; exact+renamed only, no near-miss (Type 3) tier, "
                                        "no exact/renamed split")
        tm, tc = scb["total_mass"], scb["total_cog_mass"]
        for f in found["erosion"]:
            share = f["complexity"] * f["sloc"] ** 0.5 / tm if tm else 0
            fn = span.get((f["file"], f["line"]))
            hs(f["file"], f["symbol"], f["line"], fn.end if fn else f["line"] + f["sloc"], "erosion",
               f"CC {f['complexity']}, {f['sloc']} SLOC, {share:.0%} of total CC mass", share)
        for f in found["cog_erosion"]:
            share = f["complexity"] * f["sloc"] ** 0.5 / tc if tc else 0
            fn = span.get((f["file"], f["line"]))
            hs(f["file"], f["symbol"], f["line"], fn.end if fn else f["line"] + f["sloc"], "cognitive_erosion",
               f"cognitive complexity {f['complexity']}, {f['sloc']} SLOC, {share:.0%} of total cognitive mass",
               share)
        for g in found["clones"]:
            share = g["lines"] * g["instances"] / scb["total_loc"] if scb["total_loc"] else 0
            (f0, l0), *others = g["locations"]
            hs(f0, None, l0, l0 + g["lines"] - 1, "duplication",
               f"{g['lines']}-line block duplicated {g['instances']}x; also at "
               + ", ".join(f"{f}:{l}" for f, l in others), share)
    else:
        for k in ("erosion", "cognitive_erosion", "verbosity", "duplication"):
            fams[k] = _null(errors["scb-check"])

    # ---- granularity: sloptrack single-use share + ast trivial wrappers
    st = None
    try:
        st = tools.sloptrack_json(root)
    except tools.ToolError as e:
        errors["sloptrack"] = str(e)
    wrappers = [f for f in funcs if f.trivial_wrapper]
    wshare = len(wrappers) / n_funcs if n_funcs else 0.0
    aw = A["granularity"]["trivial_wrapper_share"]
    n_w = normalize(wshare, aw["good"], aw["bad"])
    if st and "granularity" in st:
        g = st["granularity"]
        sshare = g["value"]
        asu = A["granularity"]["single_use_share"]
        n_s = normalize(sshare, asu["good"], asu["bad"])
        fams["granularity"] = _fam(
            {"single_use_share": sshare, "trivial_wrapper_share": round(wshare, 4)}, (n_s + n_w) / 2,
            "sloptrack (single_use_share) + clrty-spike ast STAND-IN (trivial_wrapper_share)",
            single_use_functions=g["single_use_functions"], used_functions=g["used_functions"],
            trivial_wrappers=len(wrappers), functions=n_funcs,
            normalized_parts={"single_use_share": round(n_s, 4), "trivial_wrapper_share": round(n_w, 4)})
        used = g["used_functions"] or 1
        for e in g.get("single_use_top", []):
            fn = span.get((e["file"], e["line"]))
            hs(e["file"], e["name"], e["line"], fn.end if fn else e["line"] + e["sloc"] - 1, "granularity",
               "callable with exactly one call site (sloptrack)", 1 / used)
    else:
        fams["granularity"] = _fam({"trivial_wrapper_share": round(wshare, 4)}, n_w,
                                   "clrty-spike ast STAND-IN only (sloptrack failed)",
                                   note=errors.get("sloptrack", "sloptrack returned no granularity"))
    for f in wrappers:
        hs(f.file, f.name, f.start, f.end, "granularity", "trivial wrapper: body only forwards its params",
           1 / n_funcs)

    # ---- structure (ast)
    nest = astmetrics.p95([f.nesting for f in funcs])
    fsloc = astmetrics.p95([f.sloc for f in funcs])
    many = [f for f in funcs if f.params > 5]
    big = {k: v for k, v in file_sloc.items() if v > 500}
    S = A["structure"]
    sub = {
        "nesting_p95": nest,
        "function_sloc_p95": fsloc,
        "many_params_share": len(many) / n_funcs if n_funcs else 0.0,
        "big_file_share": len(big) / len(file_sloc) if file_sloc else 0.0,
    }
    nparts = {k: normalize(v, S[k]["good"], S[k]["bad"]) for k, v in sub.items()}
    fams["structure"] = _fam(
        {**{k: round(v, 4) for k, v in sub.items()}, "functions_gt5_params": len(many), "files_gt500_sloc": len(big)},
        sum(nparts.values()) / len(nparts), "clrty-spike ast STAND-IN",
        normalized_parts={k: round(v, 4) for k, v in nparts.items()})
    if n_funcs:
        deep = sorted(funcs, key=lambda f: -f.nesting)[:5]
        for f in deep:
            if f.nesting > S["nesting_p95"]["good"]:
                hs(f.file, f.name, f.start, f.end, "structure", f"nesting depth {f.nesting}", 1 / n_funcs)
        for f in sorted(funcs, key=lambda f: -f.sloc)[:5]:
            if f.sloc > S["function_sloc_p95"]["good"]:
                hs(f.file, f.name, f.start, f.end, "structure", f"{f.sloc} SLOC function", 1 / n_funcs)
        for f in many:
            hs(f.file, f.name, f.start, f.end, "structure", f"{f.params} parameters", 1 / n_funcs)
    for k, v in big.items():
        hs(k, None, 1, v, "structure", f"file has {v} SLOC (> 500)", 1 / max(len(file_sloc), 1))

    fams["coupling"] = _null("not implemented in spike")
    fams["hygiene"] = _null("not implemented in spike")

    # ---- radon: informational block + cross-check erosion (not part of the composite)
    radon_info = None
    try:
        radon_info = tools.radon_summary(root)
        blocks = radon_info.pop("_blocks")
        by_fn = {(f, b.lineno): b for f, b in blocks}
        tot = hi = 0.0
        for f in funcs:
            b = by_fn.get((f.file, f.start))
            if not b:
                continue
            m = b.complexity * max(f.sloc, 1) ** 0.5
            tot += m
            hi += m if b.complexity > 10 else 0
        radon_info["erosion_crosscheck"] = round(hi / tot, 4) if tot else 0.0
        radon_info["erosion_crosscheck_note"] = "same formula as SCB erosion but radon CC; informational only"
    except Exception as e:  # noqa: BLE001
        errors["radon"] = repr(e)

    # ---- composite
    present = [k for k, v in fams.items() if v["normalized"] is not None]
    weights = weights_for(present, A)
    comp = composite({k: fams[k]["normalized"] for k in present}, weights)
    for k in fams:
        fams[k]["weight"] = round(weights.get(k, 0.0), 4) if k in weights else None
    for h in hotspots:
        h["_score"] = weights.get(h["family"], 0.0) * h.pop("_share")
    hotspots.sort(key=lambda h: -h["_score"])
    top = []
    for h in hotspots[:10]:
        h["contribution"] = round(h.pop("_score"), 5)
        top.append(h)

    out = {
        "versions": {
            "spike": __version__,
            "scb-check": tools.dist_version("scb-check"),
            "radon": tools.dist_version("radon"),
            "sloptrack": tools.dist_version("sloptrack") + " (real tool; granularity single-use only)",
            "granularity_trivial_wrapper": "clrty-spike ast stand-in",
            "structure": "clrty-spike ast stand-in",
            "python": platform.python_version(),
            "anchors": str(ANCHORS_PATH.name if anchors_path is None else Path(anchors_path).name),
        },
        "path": str(root),
        "loc": loc,
        "files": {"python_files_parsed": len(file_sloc), "parse_failures": parse_failed},
        "conventions": "normalized: 1.0 = at/better than good anchor, 0.0 = at/worse than bad anchor. "
                       "composite: 100 = all families good. Higher is better.",
        "families": fams,
        "composite": round(comp, 2),
        "hotspots": top,
        "radon": radon_info,
    }
    if errors:
        out["errors"] = errors
    return out
