"""Thin wrappers around the three external tools. Each returns plain data; failures raise ToolError."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from importlib import metadata
from pathlib import Path


class ToolError(RuntimeError):
    pass


def _env():
    env = dict(os.environ)
    env["NO_COLOR"] = "1"
    env["SLOPTRACK_IN_UVX"] = "1"  # never let sloptrack re-exec itself under an unpinned uvx env
    return env


def _run(cmd, cwd, ok=(0, 1)):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=_env())
    if r.returncode not in ok:
        raise ToolError(f"{cmd[0]} exit {r.returncode}: {r.stderr.strip()[:500]}")
    if not r.stdout.strip() and r.stderr.strip():
        raise ToolError(f"{cmd[0]} exit {r.returncode}, no output: {r.stderr.strip()[-500:]}")
    return r.stdout


# ---------------------------------------------------------------- versions
def dist_version(name: str) -> str:
    """Version plus git commit if the distribution was installed from a git URL."""
    try:
        d = metadata.distribution(name)
    except metadata.PackageNotFoundError:
        return "not installed"
    v = d.version
    try:
        du = json.loads(d.read_text("direct_url.json") or "{}")
        sha = du.get("vcs_info", {}).get("commit_id")
        if sha:
            v += f"@{sha}"
    except (ValueError, TypeError):
        pass
    return v


# ---------------------------------------------------------------- scb-check
def _scb_cmd():
    exe = Path(sys.executable).parent / "scb-check"
    return [str(exe)] if exe.exists() else [sys.executable, "-P", "-c", "from scb_check.cli import main; main()"]


# SlopCodeBench's own harness (slop_code/metrics/checkpoint/driver.py) always runs
# `scb-check check --report --include-all <snapshot>`. Without --include-all scb-check hides
# "informational" rules and `# scbc` boundary-suppressed findings, which under-reports verbosity
# by ~30-50% on real repos. We match the reference invocation.
SCB_FLAGS = ["--include-all"]


def scb_json(path: Path) -> dict:
    """Run from inside the target dir so scb-check does not pick up the caller's config."""
    cwd = path if path.is_dir() else path.parent
    out = _run(_scb_cmd() + ["check", str(path), "--report"] + SCB_FLAGS, cwd)
    try:
        return json.loads(out)
    except ValueError as e:
        raise ToolError(f"scb-check produced non-JSON output: {out[:200]!r}") from e


_LOC = re.compile(r"┌─ (?P<file>.+?):(?P<line>\d+)(?::\d+)?\s*$")


def scb_findings(path: Path, root: Path) -> dict:
    """Parse scb-check's human output into located findings (its JSON report only has aggregates).

    Returns {"erosion": [...], "cog_erosion": [...], "clones": [...]}; paths are made relative to root.
    """
    cwd = path if path.is_dir() else path.parent
    text = _run(_scb_cmd() + ["check", str(path)] + SCB_FLAGS, cwd)
    base = root if root.is_dir() else root.parent
    res = {"erosion": [], "cog_erosion": [], "clones": []}
    blocks = re.split(r"\n(?=[a-z_-]+(?:\[[^\]]*\])?: )", text)
    for blk in blocks:
        head = blk.splitlines()[0] if blk.strip() else ""
        locs = []
        for ln in blk.splitlines():
            m = _LOC.search(ln.strip())
            if m:
                f = Path(m["file"])
                f = f if f.is_absolute() else (cwd / f)
                try:
                    f = f.resolve().relative_to(base.resolve())
                except ValueError:
                    pass
                locs.append((str(f), int(m["line"])))
        m = re.match(r"(erosion|cog_erosion): function `(.+?)` exceeds", head)
        if m and locs:
            c = re.search(r"complexity: (\d+), sloc: (\d+)", blk)
            if c:
                res[m[1]].append({"file": locs[0][0], "line": locs[0][1], "symbol": m[2],
                                  "complexity": int(c[1]), "sloc": int(c[2])})
            continue
        m = re.match(r"duplicate-structure: duplicated block \((\d+) lines, (\d+) instances\)", head)
        if m and locs:
            res["clones"].append({"lines": int(m[1]), "instances": int(m[2]), "locations": locs})
    return res


# ---------------------------------------------------------------- sloptrack
def sloptrack_json(path: Path) -> dict:
    # -P: we run from inside the target, and `python -m` would put it first on sys.path, so a
    # target module named like a stdlib one (click's types.py) shadows it and sloptrack dies on import.
    cwd = path if path.is_dir() else path.parent
    out = _run([sys.executable, "-P", "-m", "sloptrack", "measure", str(path), "--json", "--no-uvx",
                "--no-git", "--top", "1000"], cwd, ok=(0, 1))
    try:
        return json.loads(out)
    except ValueError as e:
        raise ToolError(f"sloptrack produced non-JSON output: {out[:200]!r}") from e


# ---------------------------------------------------------------- radon
def radon_summary(root: Path) -> dict:
    from radon.complexity import cc_visit
    from radon.metrics import mi_visit
    from radon.raw import analyze

    from .astmetrics import iter_py_files

    base = root if root.is_dir() else root.parent
    blocks, mis = [], []
    raw = {"loc": 0, "lloc": 0, "sloc": 0, "comments": 0, "blank": 0}
    n_files = 0
    for p in iter_py_files(root):
        try:
            src = p.read_text(encoding="utf-8", errors="replace")
            blocks += [(str(p.relative_to(base)), b) for b in cc_visit(src)]
            mis.append((mi_visit(src, multi=True), analyze(src).sloc))
            r = analyze(src)
            for k in raw:
                raw[k] += getattr(r, k)
            n_files += 1
        except Exception:  # radon can choke on odd syntax; skip that file
            continue
    ccs = [b.complexity for _, b in blocks]
    total_sloc = sum(w for _, w in mis) or 1
    return {
        "files": n_files,
        "raw": raw,
        "cc_mean": round(sum(ccs) / len(ccs), 3) if ccs else 0.0,
        "cc_max": max(ccs) if ccs else 0,
        "blocks_cc_gt10": sum(1 for c in ccs if c > 10),
        "mi_mean_sloc_weighted": round(sum(m * w for m, w in mis) / total_sloc, 2) if mis else None,
        "mi_min_file": round(min((m for m, _ in mis), default=0), 2) if mis else None,
        "_blocks": blocks,
    }
