"""review-server-and-checks-01: a break proved by a check that passes its time limit leaves the check running.

prove.py stops a run past its limit with SIGKILL to the process group it started. For a break proved
by a check, that group is `checks.py <name>`, and checks.py starts the check itself in a new session
of its own; SIGKILL gives checks.py no chance to stop it, so the check (here pytest, and its child)
keeps running after the proof has ended. Red while a process the proof started outlives it.
Run: .venv/bin/python -m pytest -p tests.conftest .scratch/kit-phase-2/findings/scripts/review-server-and-checks-01.py -q
"""

from __future__ import annotations

import os
import time

import prove
from tests.test_prove_runs import TESTS, entry, small_repo


def test_a_check_past_its_limit_does_not_outlive_the_proof(tmp_path):
    pid_file = tmp_path / "child.pid"
    slow = TESTS + ("\n\ndef test_slow():\n    import os, time\n"
                    f"    open({str(pid_file)!r}, 'w').write(str(os.getpid()))\n    time.sleep(60)\n")
    root = small_repo(tmp_path, [entry(test=None, check="unit")], tests=slow)
    code = prove.prove(root, minutes=0.05, out=lambda *_: None)
    assert code == 1
    pid = int(pid_file.read_text())
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.05)
    os.kill(pid, 9)
    raise AssertionError("the check's pytest outlived the proof that started it")
