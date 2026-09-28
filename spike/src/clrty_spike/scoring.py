"""Anchors, normalisation, composite."""

from __future__ import annotations

import math
import tomllib
from pathlib import Path

ANCHORS_PATH = Path(__file__).resolve().parents[2] / "anchors.toml"


def load_anchors(path: Path | None = None) -> dict:
    with open(path or ANCHORS_PATH, "rb") as f:
        return tomllib.load(f)


def normalize(m: float, good: float, bad: float) -> float:
    """n = clamp((b - m) / (b - g), 0, 1) as written in the plan.

    NOTE: as literally written this is 1 when m == g (good) and 0 when m == b (bad), i.e. HIGHER IS BETTER.
    The plan's composite takes ln(max(n, 0.01)), which only penalises when n is small, so the plan's n is a
    goodness fraction. We keep that convention: normalized 1.0 = good, 0.0 = bad; composite 100 = all good.
    """
    if bad == good:
        return 1.0
    return min(1.0, max(0.0, (bad - m) / (bad - good)))


def weights_for(present: list[str], anchors: dict) -> dict[str, float]:
    explicit = {k: v for k, v in anchors["weights"].items() if k in present}
    rest = [f for f in present if f not in explicit]
    remaining = max(0.0, 1.0 - sum(explicit.values()))
    w = dict(explicit)
    for f in rest:
        w[f] = remaining / len(rest) if rest else 0.0
    total = sum(w.values()) or 1.0
    return {k: v / total for k, v in w.items()}


def composite(norms: dict[str, float], weights: dict[str, float]) -> float:
    s = sum(weights[f] * math.log(max(norms[f], 0.01)) for f in norms)
    return 100.0 * math.exp(s)
