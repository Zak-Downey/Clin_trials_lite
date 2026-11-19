"""The unit suite's test server stops at once, so a teardown does not wait on it."""

import time

from conftest import serve_in_background
from webapp.server import make_server


def test_the_test_server_started_as_the_api_fixture_starts_it_stops_in_under_a_fifth_of_a_second(tmp_path):
    server = make_server(str(tmp_path / "api.db"), fetch=lambda nct_id: {}, find=lambda **params: [])
    thread = serve_in_background(server)
    time.sleep(0.05)

    started = time.perf_counter()
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)
    took = time.perf_counter() - started

    assert not thread.is_alive()
    assert took < 0.2, f"stopping the test server took {took:.2f} s"
