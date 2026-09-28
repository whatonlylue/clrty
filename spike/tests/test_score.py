from pathlib import Path

import pytest

from clrty_spike import astmetrics
from clrty_spike.cli import _diff
from clrty_spike.score import score_path
from clrty_spike.scoring import composite, load_anchors, normalize, weights_for

FIX = Path(__file__).parent / "fixtures"
FAMILIES = ["erosion", "cognitive_erosion", "verbosity", "duplication", "granularity", "structure"]


@pytest.fixture(scope="module")
def clean():
    return score_path(FIX / "clean")


@pytest.fixture(scope="module")
def sloppy():
    return score_path(FIX / "sloppy")


@pytest.mark.parametrize("family", FAMILIES)
def test_sloppy_scores_worse_per_family(clean, sloppy, family):
    c, s = clean["families"][family], sloppy["families"][family]
    assert c["normalized"] is not None and s["normalized"] is not None, (c, s)
    assert s["normalized"] < c["normalized"], f"{family}: sloppy {s} not worse than clean {c}"


def test_raw_direction(clean, sloppy):
    # raw metrics are lower-is-better
    for fam in ("erosion", "cognitive_erosion", "verbosity", "duplication"):
        assert sloppy["families"][fam]["raw"] > clean["families"][fam]["raw"]
    assert sloppy["families"]["structure"]["raw"]["nesting_p95"] > clean["families"]["structure"]["raw"]["nesting_p95"]


def test_composite_and_shape(clean, sloppy):
    assert sloppy["composite"] < clean["composite"]
    assert 0 <= sloppy["composite"] <= 100 and 0 <= clean["composite"] <= 100
    # scb-check 0.1.3's trivial-wrapper rule flags idiomatic one-line returns (clean scores ~77)
    assert clean["composite"] > 70
    for k in ("versions", "path", "loc", "families", "composite", "hotspots"):
        assert k in clean
    assert clean["families"]["coupling"]["normalized"] is None
    assert "@" in clean["versions"]["scb-check"]  # pinned sha recorded
    assert 0 < len(sloppy["hotspots"]) <= 10
    h = sloppy["hotspots"][0]
    assert {"file", "symbol", "start_line", "end_line", "family", "detail"} <= set(h)


def test_sloppy_hotspots_cover_expected(sloppy):
    fams = {h["family"] for h in sloppy["hotspots"]}
    assert {"erosion", "duplication", "granularity"} <= fams


def test_normalize_and_weights():
    assert normalize(0.31, 0.31, 0.88) == 1.0
    assert normalize(0.88, 0.31, 0.88) == 0.0
    assert normalize(5, 0.31, 0.88) == 0.0 and normalize(-1, 0.31, 0.88) == 1.0
    assert normalize(0.595, 0.31, 0.88) == pytest.approx(0.5)
    A = load_anchors()
    fams = ["erosion", "cognitive_erosion", "verbosity", "duplication", "granularity", "structure"]
    w = weights_for(fams, A)
    assert sum(w.values()) == pytest.approx(1.0)
    assert w["erosion"] == w["verbosity"] == 0.2 and w["duplication"] == 0.15
    assert w["structure"] == pytest.approx(0.15)
    w2 = weights_for(["erosion", "verbosity"], A)  # renormalised when few families present
    assert sum(w2.values()) == pytest.approx(1.0)
    assert composite({f: 1.0 for f in fams}, w) == pytest.approx(100.0)
    assert composite({f: 0.0 for f in fams}, w) == pytest.approx(1.0)  # floor 0.01 -> 100*0.01


def test_trivial_wrapper_detection(tmp_path):
    (tmp_path / "m.py").write_text(
        "def a(x, y):\n    return b(y, x)\n"
        "def c(x):\n    return c2(x + 1)\n"  # not a pure forward
        "def d(x):\n    '''doc'''\n    return e.f(x)\n"
        "def g(x):\n    y = x\n    return h(y)\n"  # two statements
    )
    funcs, _, _ = astmetrics.collect(tmp_path)
    got = {f.name: f.trivial_wrapper for f in funcs}
    assert got == {"a": True, "c": False, "d": True, "g": False}


def test_diff(clean, sloppy):
    d = _diff(sloppy, clean)
    assert d["composite_delta"] > 0
    assert all(v["normalized_delta"] >= 0 for k, v in d["families"].items() if v["normalized_delta"] is not None)


def test_target_module_does_not_shadow_stdlib():
    # a target with its own types.py (like click) must not break sloptrack's imports
    g = score_path(FIX / "shadow")["families"]["granularity"]
    assert "sloptrack failed" not in g["source"], g
