"""Stand-in metrics implemented with Python's `ast`: structure family, trivial wrappers, function spans."""
from __future__ import annotations

import ast
import math
from dataclasses import dataclass
from pathlib import Path

SKIP_DIRS = {".git", ".hg", ".venv", "venv", "env", "node_modules", "__pycache__", "build", "dist",
             ".tox", ".mypy_cache", ".pytest_cache", ".ruff_cache", "site-packages", ".eggs"}
NEST_NODES = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try, ast.With, ast.AsyncWith, ast.Match)
try:  # py3.11+
    NEST_NODES += (ast.TryStar,)
except AttributeError:  # pragma: no cover
    pass
FUNC_NODES = (ast.FunctionDef, ast.AsyncFunctionDef)


@dataclass
class Func:
    file: str          # path relative to repo root
    name: str          # qualified-ish name (Class.method)
    start: int
    end: int
    sloc: int
    params: int
    nesting: int
    trivial_wrapper: bool


def iter_py_files(root: Path):
    if root.is_file():
        yield root
        return
    for p in sorted(root.rglob("*.py")):
        rel = p.relative_to(root).parts
        if any(part in SKIP_DIRS or part.startswith(".") for part in rel[:-1]):
            continue
        yield p


def _sloc(lines: list[str], start: int, end: int) -> int:
    n = 0
    for ln in lines[start - 1:end]:
        s = ln.strip()
        if s and not s.startswith("#"):
            n += 1
    return n


def _max_nesting(node: ast.AST, depth: int = 0) -> int:
    """Max depth of nested control-flow blocks inside a function; nested defs are excluded (own functions)."""
    best = depth
    for child in ast.iter_child_nodes(node):
        if isinstance(child, FUNC_NODES + (ast.ClassDef, ast.Lambda)):
            continue
        d = depth + 1 if isinstance(child, NEST_NODES) else depth
        best = max(best, _max_nesting(child, d))
    return best


def _param_names(fn) -> list[str]:
    a = fn.args
    names = [x.arg for x in a.posonlyargs + a.args + a.kwonlyargs]
    if a.vararg:
        names.append(a.vararg.arg)
    if a.kwarg:
        names.append(a.kwarg.arg)
    return names


def _is_trivial_wrapper(fn) -> bool:
    """Body (minus docstring) is a single `return f(...)` / `f(...)` that only forwards the function's own params."""
    body = list(fn.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) \
            and isinstance(body[0].value.value, str):
        body = body[1:]
    if len(body) != 1:
        return False
    stmt = body[0]
    call = stmt.value if isinstance(stmt, (ast.Return, ast.Expr)) else None
    if not isinstance(call, ast.Call):
        return False
    params = [p for p in _param_names(fn) if p not in ("self", "cls")]
    if not params:
        return False  # zero-arg forwarders are not "forwarding the params"
    passed: list[str] = []
    for arg in call.args:
        arg = arg.value if isinstance(arg, ast.Starred) else arg
        if not isinstance(arg, ast.Name):
            return False
        passed.append(arg.id)
    for kw in call.keywords:
        if not isinstance(kw.value, ast.Name):
            return False
        passed.append(kw.value.id)
    return set(passed) == set(params)


def _walk_funcs(tree: ast.AST, prefix: str = ""):
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, FUNC_NODES):
            yield node, prefix + node.name
            yield from _walk_funcs(node, prefix + node.name + ".")
        elif isinstance(node, ast.ClassDef):
            yield from _walk_funcs(node, prefix + node.name + ".")
        else:
            yield from _walk_funcs(node, prefix)


def collect(root: Path):
    """Return (funcs, file_sloc) where file_sloc maps relative file -> SLOC. Unparseable files are listed."""
    base = root if root.is_dir() else root.parent
    funcs: list[Func] = []
    file_sloc: dict[str, int] = {}
    failed: list[str] = []
    for p in iter_py_files(root):
        rel = str(p.relative_to(base))
        try:
            src = p.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(src)
        except (SyntaxError, ValueError, RecursionError):
            failed.append(rel)
            continue
        lines = src.splitlines()
        file_sloc[rel] = _sloc(lines, 1, len(lines))
        for fn, qname in _walk_funcs(tree):
            end = fn.end_lineno or fn.lineno
            params = [x for x in _param_names(fn) if x not in ("self", "cls")]
            funcs.append(Func(rel, qname, fn.lineno, end, _sloc(lines, fn.lineno, end), len(params),
                              _max_nesting(fn), _is_trivial_wrapper(fn)))
    return funcs, file_sloc, failed


def p95(values: list[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = max(0, math.ceil(0.95 * len(s)) - 1)  # nearest-rank
    return float(s[k])
