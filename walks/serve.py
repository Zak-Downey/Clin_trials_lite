"""Start the app's server against the stand-in registry, for a walk.

    python walks/serve.py <database> <registry base url>

Prints the address on one line. The registry functions are the app's own defaults
(ctgov), pointed at the stand-in by changing ctgov.BASE; nothing else differs
from run.py's server.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import ctgov  # noqa: E402
from webapp.server import make_server  # noqa: E402

if __name__ == "__main__":
    db, registry = sys.argv[1], sys.argv[2]
    ctgov.BASE = registry.rstrip("/") + "/api/v2"
    server = make_server(db)
    print(f"http://127.0.0.1:{server.server_address[1]}/", flush=True)
    server.serve_forever()
