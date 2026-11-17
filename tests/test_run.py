"""The documented start command, run for real in a subprocess.

Lacks: opening a browser (--no-browser), and the live registry (nothing here
asks for a study).
"""

import errno
import os
import socket
import subprocess
import sys
import urllib.request

import pathlib

import pytest

import run

ROOT = pathlib.Path(__file__).resolve().parent.parent


def test_the_database_is_monitor_db_in_the_start_folder_unless_monitor_db_is_set():
    """test_the_database_is_monitor_db_in_the_start_folder_unless_monitor_db_is_set"""
    assert run.database_path({}, "/here") == os.path.join("/here", "monitor.db")
    assert run.database_path({"MONITOR_DB": "/else/x.db"}, "/here") == "/else/x.db"


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_run_py_serves_the_page_on_localhost_only_and_prints_the_address(tmp_path):
    """test_run_py_serves_the_page_on_localhost_only_and_prints_the_address"""
    env = {**os.environ, "MONITOR_DB": str(tmp_path / "m.db")}
    port = _free_port()
    proc = subprocess.Popen(
        [sys.executable, str(ROOT / "run.py"), "--no-browser", "--port", str(port)],
        cwd=tmp_path, env=env, stdout=subprocess.PIPE, text=True,
    )
    try:
        line = proc.stdout.readline()
        address = line.split(" at ")[1].strip()
        assert address == f"http://127.0.0.1:{port}/"
        with urllib.request.urlopen(address, timeout=10) as page:
            html = page.read().decode()
        assert "Trial Change Monitor" in html
        assert (tmp_path / "m.db").exists()
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def test_the_server_refuses_to_bind_beyond_the_local_machine(tmp_path):
    """test_the_server_refuses_to_bind_beyond_the_local_machine"""
    import pytest
    from webapp.server import make_server

    with pytest.raises(ValueError):
        make_server(str(tmp_path / "x.db"), host="0.0.0.0")


def test_the_shell_and_its_assets_are_served_and_nothing_outside_static_is(api):
    """test_the_shell_and_its_assets_are_served_and_nothing_outside_static_is"""
    for route, kind in (("/", "text/html"), ("/static/app.js", "javascript"), ("/static/style.css", "text/css")):
        with urllib.request.urlopen(api.base + route, timeout=10) as resp:
            assert kind in resp.headers["Content-Type"]
    status, body = api.get("/static/../server.py")
    assert status == 404 and body["error"]["kind"] == "not_found"


def _start(tmp_path, *args):
    env = {**os.environ, "MONITOR_DB": str(tmp_path / "m.db")}
    return subprocess.Popen(
        [sys.executable, str(ROOT / "run.py"), "--no-browser", *args],
        cwd=tmp_path, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )


def test_a_second_run_on_the_same_database_points_at_the_running_server(tmp_path):
    """test_a_second_run_on_the_same_database_points_at_the_running_server"""
    first = _start(tmp_path, "--port", str(_free_port()))
    try:
        address = first.stdout.readline().split(" at ")[1].strip()
        second = _start(tmp_path)
        out, _ = second.communicate(timeout=20)
        assert second.returncode == 0
        assert "already running" in out and address in out
    finally:
        first.terminate()
        first.wait(timeout=10)


def test_a_busy_port_or_a_missing_folder_is_a_plain_line_not_a_traceback(tmp_path):
    """test_a_busy_port_or_a_missing_folder_is_a_plain_line_not_a_traceback"""
    import socket

    with socket.socket() as taken:
        taken.bind(("127.0.0.1", 0))
        taken.listen()
        proc = _start(tmp_path, "--port", str(taken.getsockname()[1]))
        _, err = proc.communicate(timeout=20)
    assert proc.returncode == 1 and "Traceback" not in err and "port" in err

    env = {**os.environ, "MONITOR_DB": str(tmp_path / "nope" / "m.db")}
    proc = subprocess.run([sys.executable, str(ROOT / "run.py"), "--no-browser", "--port", str(_free_port())],
                          cwd=tmp_path, env=env,
                          capture_output=True, text=True, timeout=20)
    assert proc.returncode == 1 and "Traceback" not in proc.stderr and "folder" in proc.stderr


def _a_start_kept_off(tmp_path, monkeypatch, port, *args):
    """Start run.py with `args`, where it would listen on `port`, without letting it serve there.

    Returns (returncode, stdout, stderr). When the test can hold `port` with a
    listening socket of its own, run.py runs for real and stops with the
    busy-port line. When it cannot (a copy of the app runs there, or a copy that
    just stopped left the port lingering with nothing listening, which run.py
    would reuse), run.py's main runs in this process with a server that is
    never made: it records the port asked for and answers that it is busy, so
    nothing serves on `port` and nothing fights the copy there.
    """
    holder = socket.socket()
    try:
        try:
            holder.bind(("127.0.0.1", port))
            holder.listen()
        except OSError as err:
            assert err.errno == errno.EADDRINUSE
            holder.close()
            return _main_without_a_server(tmp_path, monkeypatch, port, args)
        proc = _start(tmp_path, *args)
        try:
            out, err = proc.communicate(timeout=20)
        except subprocess.TimeoutExpired:
            proc.kill()
            out, err = proc.communicate()
    finally:
        holder.close()
    return proc.returncode, out, err


def _main_without_a_server(tmp_path, monkeypatch, port, args):
    asked = []

    def busy(db, port):
        asked.append(port)
        raise OSError(errno.EADDRINUSE, os.strerror(errno.EADDRINUSE))

    monkeypatch.setenv("MONITOR_DB", str(tmp_path / "m.db"))
    monkeypatch.setattr(run, "make_server", busy)
    with pytest.raises(SystemExit) as stopped:
        run.main(["--no-browser", *args])
    assert asked == [port]
    return 1, "", str(stopped.value.code)


def test_a_plain_start_uses_port_8765_and_stops_with_a_plain_line_when_it_is_taken(tmp_path, monkeypatch):
    """test_a_plain_start_uses_port_8765_and_stops_with_a_plain_line_when_it_is_taken

    Never serves on 8765 and never fights a copy of the app running there.
    """
    code, out, err = _a_start_kept_off(tmp_path, monkeypatch, 8765)
    assert code == 1 and out == "" and "Traceback" not in err
    assert "port 8765" in err and "--port" in err


def test_a_port_a_stopped_copy_just_served_on_is_still_kept_from_run_py(tmp_path, monkeypatch):
    """test_a_port_a_stopped_copy_just_served_on_is_still_kept_from_run_py

    review-server-and-checks-01. After the owner stops their copy, its port lingers:
    nothing listens, yet a plain hold of it fails, and run.py (which reuses the
    address) would start there over an empty database. The 8765 test's way of
    keeping run.py off the port must hold for that case too. Uses a free port,
    never 8765.
    """
    port = _free_port()
    first = _start(tmp_path, "--port", str(port))
    try:
        address = first.stdout.readline().split(" at ")[1].strip()
        for _ in range(3):
            urllib.request.urlopen(address, timeout=5).read()
    finally:
        first.terminate()
        first.wait(timeout=10)
    code, out, err = _a_start_kept_off(tmp_path, monkeypatch, port, "--port", str(port))
    assert code == 1, f"run.py served on the port the test meant to keep it off: {out!r}"
    assert out == "" and "Traceback" not in err
    assert f"port {port}" in err and "--port" in err


@pytest.mark.parametrize("family,host", [(socket.AF_INET, "0.0.0.0"), (socket.AF_INET6, "::")])
def test_a_port_held_on_all_addresses_stops_run_py_with_the_busy_port_line(tmp_path, family, host):
    """test_a_port_held_on_all_addresses_stops_run_py_with_the_busy_port_line

    early-read-whole-01. Most programs listen on all addresses; on macOS the
    reuse-address option let a bind to 127.0.0.1 succeed beside one and take
    its browser requests. Uses a free port, never 8765.
    """
    holder = socket.socket(family)
    try:
        holder.bind((host, 0))
        holder.listen()
        port = holder.getsockname()[1]
        proc = _start(tmp_path, "--port", str(port))
        try:
            out, err = proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            proc.terminate()
            out, err = proc.communicate()
    finally:
        holder.close()
    assert proc.returncode == 1, f"run.py started anyway and printed: {out!r}"
    assert out == "" and "Traceback" not in err
    assert f"port {port}" in err and "--port" in err
