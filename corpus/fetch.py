#!/usr/bin/env python3
"""Fetch the clrty evaluation corpus described by corpus/manifest.toml.

Stdlib only, Python 3.12. Run: `uv run corpus/fetch.py` or `python3 corpus/fetch.py [name ...]`.
Git entries: git init + `fetch --depth 1 origin <sha>` + checkout (works for any SHA).
Archive entries (`archive` + `sha256` keys): download, verify, extract. Idempotent.
"""

import hashlib
import io
import subprocess
import sys
import tarfile
import tomllib
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEST = HERE / "repos"
STAMP = ".clrty-rev"


def git(cwd: Path, *args: str) -> str:
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"git {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout.strip()


def fetch_git(entry: dict, dest: Path) -> None:
    rev = entry["rev"]
    if (dest / ".git").exists():
        try:
            if git(dest, "rev-parse", "HEAD") == rev and not git(dest, "status", "--porcelain"):
                return
        except RuntimeError:
            pass
    dest.mkdir(parents=True, exist_ok=True)
    if not (dest / ".git").exists():
        git(dest, "init", "-q")
    if subprocess.run(["git", "remote", "get-url", "origin"], cwd=dest, capture_output=True).returncode:
        git(dest, "remote", "add", "origin", entry["url"])
    else:
        git(dest, "remote", "set-url", "origin", entry["url"])
    git(dest, "fetch", "-q", "--depth", "1", "origin", rev)
    git(dest, "-c", "advice.detachedHead=false", "checkout", "-q", "--force", rev)
    git(dest, "clean", "-fdq")


def fetch_archive(entry: dict, dest: Path) -> None:
    if (dest / STAMP).exists() and (dest / STAMP).read_text().strip() == entry["sha256"]:
        return
    with urllib.request.urlopen(entry["archive"]) as resp:
        data = resp.read()
    digest = hashlib.sha256(data).hexdigest()
    if digest != entry["sha256"]:
        raise RuntimeError(f"sha256 mismatch: expected {entry['sha256']}, got {digest}")
    dest.mkdir(parents=True, exist_ok=True)
    if entry["archive"].endswith(".zip"):
        zipfile.ZipFile(io.BytesIO(data)).extractall(dest)
    else:
        with tarfile.open(fileobj=io.BytesIO(data)) as tf:
            tf.extractall(dest, filter="data")
    (dest / STAMP).write_text(digest)


def python_loc(root: Path) -> tuple[int, int]:
    """(non-blank lines, files) over *.py under root, skipping .git."""
    loc = files = 0
    for p in root.rglob("*.py"):
        if ".git" in p.relative_to(root).parts or not p.is_file():
            continue
        files += 1
        loc += sum(1 for line in p.read_text(errors="replace").splitlines() if line.strip())
    return loc, files


def main(argv: list[str]) -> int:
    manifest = tomllib.loads((HERE / "manifest.toml").read_text())
    entries = [e for e in manifest.get("repo", []) if not argv or e["name"] in argv]
    failed = 0
    rows = []
    for e in entries:
        dest = DEST / e["name"]
        try:
            if "archive" in e:
                fetch_archive(e, dest)
            else:
                fetch_git(e, dest)
            scored = dest / e.get("subdir", "")
            if not scored.is_dir():
                raise RuntimeError(f"subdir {e.get('subdir')!r} missing")
            loc, n = python_loc(scored)
            rows.append((e["name"], e["kind"], e.get("rev", e.get("sha256", ""))[:12], n, loc))
        except Exception as exc:  # report and continue
            failed += 1
            print(f"FAIL {e['name']}: {exc}", file=sys.stderr)
    print(f"{'name':<20}{'kind':<16}{'rev':<14}{'files':>6}{'py_loc':>9}")
    for r in rows:
        print(f"{r[0]:<20}{r[1]:<16}{r[2]:<14}{r[3]:>6}{r[4]:>9}")
    print(f"{len(rows)}/{len(entries)} entries ok")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
