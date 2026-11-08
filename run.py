"""Start the Trial Change Monitor: a local web server and your browser.

    python run.py [--port N] [--no-browser]

The database is MONITOR_DB if set, else monitor.db in the folder you start from.
Copy that file to back it up. The server listens on 127.0.0.1 only.
"""

from __future__ import annotations

import argparse
import os
import webbrowser

from webapp.server import make_server


def database_path(environ=None, cwd=None) -> str:
    environ = os.environ if environ is None else environ
    return environ.get("MONITOR_DB") or os.path.join(cwd or os.getcwd(), "monitor.db")


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, default=0, help="port to listen on (default: a free one)")
    parser.add_argument("--no-browser", action="store_true", help="do not open the browser")
    args = parser.parse_args(argv)

    server = make_server(database_path(), port=args.port)
    address = f"http://127.0.0.1:{server.server_address[1]}/"
    print(f"Trial Change Monitor is running at {address}", flush=True)
    if not args.no_browser:
        webbrowser.open(address)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
