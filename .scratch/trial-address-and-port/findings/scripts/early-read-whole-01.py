"""early-read-whole-01: a program listening on all addresses at the port does not stop run.py.

Uses a free port, never 8765, and holds it the way most other programs do
(all IPv4 addresses, then all IPv6 addresses). The spec says run.py stops with
the busy-port line; it binds 127.0.0.1 beside the holder and serves instead.
"""

import os
import socket
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]


@pytest.mark.parametrize("family,host", [(socket.AF_INET, "0.0.0.0"), (socket.AF_INET6, "::")])
def test_a_port_held_on_all_addresses_stops_run_py_with_the_busy_port_line(tmp_path, family, host):
    holder = socket.socket(family)
    holder.bind((host, 0))
    holder.listen()
    port = holder.getsockname()[1]
    env = {**os.environ, "MONITOR_DB": str(tmp_path / "m.db")}
    proc = subprocess.Popen(
        [sys.executable, str(ROOT / "run.py"), "--no-browser", "--port", str(port)],
        cwd=tmp_path, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    try:
        out, err = proc.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        proc.terminate()
        out, err = proc.communicate()
    finally:
        holder.close()
    assert proc.returncode == 1, f"run.py started anyway and printed: {out!r}"
    assert f"port {port}" in err and "--port" in err
