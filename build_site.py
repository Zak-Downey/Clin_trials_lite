"""Assemble the static site the app is published as.

    python build_site.py            # into site/
    python -m http.server -d site   # then open http://localhost:8000

The site is one page and the Python modules it mounts, copied flat so that a
locally served copy and the published one have the same shape: what works here
is what works there.

Nothing here decides *what* ships. The page itself names the modules it mounts,
and this reads that list, so there is one list rather than two that can drift.
A file the page does not name is a file that does not travel -- including the
working database, the issue tracker, the tests and the simulator, none of which
belong on a public URL.
"""

from __future__ import annotations

import os
import pathlib
import re
import shutil
import stat
import sys

ROOT = pathlib.Path(__file__).resolve().parent
PAGE = ROOT / "web" / "index.html"
SITE = ROOT / "site"

# The page's own list of what it mounts, which is a JavaScript array of paths.
# Read rather than re-stated: a list read from the page can fall short of the
# app and be caught by a failed import, where a second list kept alongside it
# could quietly ship something the page never asked for.
LISTED = re.compile(r"const sources = \[(.*?)\];", re.DOTALL)
QUOTED = re.compile(r'"([^"]+)"')


def published() -> list[str]:
    """The modules the page mounts, in the order it names them."""
    listed = LISTED.search(PAGE.read_text(encoding="utf-8"))
    if not listed:
        raise ValueError(f"{PAGE} does not name the modules it mounts")
    return QUOTED.findall(listed.group(1))


def _make_writable(dest: pathlib.Path) -> None:
    """Let the last build be deleted, whatever a synced drive did to it.

    A folder inside a synced drive comes back marked read-only, and refuses to
    be removed. That matters more than it sounds: a stale file left behind by a
    clean-out that gave up is a file that ships without being named.
    """
    for path in [dest, *dest.rglob("*")]:
        os.chmod(path, path.stat().st_mode | stat.S_IWUSR)


def build(dest: pathlib.Path = SITE) -> list[pathlib.Path]:
    """Write the site to `dest`, replacing whatever was there. Returns what it wrote.

    Emptied first rather than written over, so a module dropped from the page's
    list stops being published rather than lingering from the last build.
    """
    if dest.exists():
        _make_writable(dest)
        shutil.rmtree(dest)
    written = []
    for source in ["index.html", *published()]:
        origin = PAGE if source == "index.html" else ROOT / source
        target = dest / source
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(origin, target)
        written.append(target)
    return written


if __name__ == "__main__":
    dest = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else SITE
    written = build(dest)
    print(f"{len(written)} files into {dest}")
