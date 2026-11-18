"""early-read-whole-01: a broken shared script must still leave the walks check naming its red walks.

Run from the repo root: .venv/bin/python -m pytest -p tests.conftest .scratch/kit-phase-1/findings/scripts/early-read-whole-01.py -q
Takes up to the walks' time limit (about 8 minutes). Red today: the walks check is stopped at 8 minutes
before the runner prints any failure, so its output says only "stopped after 8 minutes".
"""

import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[4]


def test_a_mass_walk_failure_names_its_red_walks_inside_the_time_limit(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    archive = subprocess.run(["git", "archive", "HEAD"], cwd=ROOT, capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", str(repo)], input=archive, check=True)
    (repo / ".venv").symlink_to(ROOT / ".venv")
    git = ["git", "-c", "user.name=r", "-c", "user.email=r@r"]
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "checkout", "-qb", "feature/kit-phase-1"], cwd=repo, check=True)
    with open(repo / "webapp" / "static" / "api.js", "a") as handle:
        handle.write("export const broken = ;\n")  # one shared script broken: every page fails
    subprocess.run(git + ["add", "-A"], cwd=repo, check=True)
    subprocess.run(git + ["commit", "-qm", "broken"], cwd=repo, check=True)

    subprocess.run(["python3", "checks.py", "walks"], cwd=repo)

    output = (repo / ".checks" / "walks.txt").read_text()
    assert "stopped after" not in output, "the walks check was cut off before the runner named a red walk"
    assert "## Result" in output and "red alone" in output
