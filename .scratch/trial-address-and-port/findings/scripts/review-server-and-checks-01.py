"""review-server-and-checks-01: the 8765 test's "someone already holds it" branch is also reached by a port
left in TIME_WAIT by a copy that just stopped, and then run.py serves on the port.

Mirrors tests/test_run.py::test_a_plain_start_uses_port_8765_and_stops_with_a_plain_line_when_it_is_taken
on a free port, never 8765: a first run.py serves a few pages and stops (as the owner's copy does when
they press Ctrl+C), then the test's holder fails to bind with EADDRINUSE, the test takes that to mean a
program is listening, and expects the next start to stop with the busy-port line. It starts instead.
"""

import errno
import os
import socket
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _start(tmp_path, port):
    env = {**os.environ, "MONITOR_DB": str(tmp_path / "m.db")}
    return subprocess.Popen(
        [sys.executable, str(ROOT / "run.py"), "--no-browser", "--port", str(port)],
        cwd=tmp_path, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )


def test_a_holder_that_cannot_bind_means_the_next_start_stops(tmp_path):
    port = _free_port()
    first = _start(tmp_path, port)
    address = first.stdout.readline().split(" at ")[1].strip()
    for _ in range(3):
        urllib.request.urlopen(address, timeout=5).read()
    first.terminate()
    first.wait(timeout=10)

    holder = socket.socket()
    try:
        try:
            holder.bind(("127.0.0.1", port))
            holder.listen()
        except OSError as err:
            assert err.errno == errno.EADDRINUSE  # the 8765 test accepts this as "a copy is running"
        proc = _start(tmp_path, port)
        try:
            out, err = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            out, err = proc.communicate()
    finally:
        holder.close()
    assert proc.returncode == 1, f"run.py served on the port the test meant to keep it off: {out!r}"
