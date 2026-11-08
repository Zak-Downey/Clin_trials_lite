"""The documented start command, run for real in a subprocess.

Lacks: opening a browser (--no-browser), and the live registry (nothing here
asks for a study).
"""

import os
import subprocess
import sys
import urllib.request

import pathlib

import run

ROOT = pathlib.Path(__file__).resolve().parent.parent


def test_the_database_is_monitor_db_in_the_start_folder_unless_monitor_db_is_set():
    assert run.database_path({}, "/here") == os.path.join("/here", "monitor.db")
    assert run.database_path({"MONITOR_DB": "/else/x.db"}, "/here") == "/else/x.db"


def test_run_py_serves_the_page_on_localhost_only_and_prints_the_address(tmp_path):
    env = {**os.environ, "MONITOR_DB": str(tmp_path / "m.db")}
    proc = subprocess.Popen(
        [sys.executable, str(ROOT / "run.py"), "--no-browser"],
        cwd=tmp_path, env=env, stdout=subprocess.PIPE, text=True,
    )
    try:
        line = proc.stdout.readline()
        address = line.split(" at ")[1].strip()
        assert address.startswith("http://127.0.0.1:")
        with urllib.request.urlopen(address, timeout=10) as page:
            html = page.read().decode()
        assert "Trial Change Monitor" in html
        assert (tmp_path / "m.db").exists()
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def test_the_server_refuses_to_bind_beyond_the_local_machine(tmp_path):
    import pytest
    from webapp.server import make_server

    with pytest.raises(ValueError):
        make_server(str(tmp_path / "x.db"), host="0.0.0.0")


def test_the_shell_and_its_assets_are_served_and_nothing_outside_static_is(api):
    for route, kind in (("/", "text/html"), ("/static/app.js", "javascript"), ("/static/style.css", "text/css")):
        with urllib.request.urlopen(api.base + route, timeout=10) as resp:
            assert kind in resp.headers["Content-Type"]
    status, body = api.get("/static/../server.py")
    assert status == 404 and body["error"]["kind"] == "not_found"
