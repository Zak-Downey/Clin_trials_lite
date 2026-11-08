"""Start the Trial Change Monitor: a local web server and your browser.

    python run.py [--port N] [--no-browser]

The database is MONITOR_DB if set, else monitor.db in the folder you start from.
Copy that file to back it up. The server listens on 127.0.0.1 only.
"""

from __future__ import annotations

import argparse
import os
import sys
import webbrowser

from webapp import instance
from webapp.server import make_server


def database_path(environ=None, cwd=None) -> str:
    environ = os.environ if environ is None else environ
    return environ.get("MONITOR_DB") or os.path.join(cwd or os.getcwd(), "monitor.db")


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, default=0, help="port to listen on (default: a free one)")
    parser.add_argument("--no-browser", action="store_true", help="do not open the browser")
    args = parser.parse_args(argv)

    db = database_path()
    folder = os.path.dirname(os.path.abspath(db))
    if not os.path.isdir(folder):
        sys.exit(f"The database folder {folder} does not exist. Create it, or set MONITOR_DB to a file in a folder that does.")
    claimed = instance.claim(db)
    if not isinstance(claimed, instance.Claim):
        if claimed is None:
            sys.exit(f"Another Trial Change Monitor is using {db}, but it has not said where. Try again in a moment.")
        print(f"Trial Change Monitor is already running at {claimed}", flush=True)
        if not args.no_browser:
            webbrowser.open(claimed)
        return
    try:
        server = make_server(db, port=args.port)
    except OSError as err:
        sys.exit(f"Cannot listen on port {args.port}: {err.strerror}. Choose another with --port, or leave it out.")
    address = f"http://127.0.0.1:{server.server_address[1]}/"
    claimed.publish(address)
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
