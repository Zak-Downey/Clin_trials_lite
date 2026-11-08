"""One server per database: ADR 0003 rests on one process serializing every write.

The first `run.py` takes an exclusive lock on `<database>.lock` for as long as it
lives (the operating system drops it if the process dies) and writes its
address there. A second start finds the lock held and reads the address instead.
"""

from __future__ import annotations

import fcntl
import os
import time


class Claim:
    def __init__(self, handle):
        self._handle = handle

    def publish(self, address: str) -> None:
        self._handle.seek(0)
        self._handle.truncate()
        self._handle.write(address)
        self._handle.flush()


def claim(db_path: str, wait: float = 3.0):
    """A Claim if this process is the only server on `db_path`, else the running server's address."""
    handle = open(db_path + ".lock", "a+")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        deadline = time.monotonic() + wait
        while True:
            handle.seek(0)
            address = handle.read().strip()
            if address or time.monotonic() >= deadline:
                handle.close()
                return address or None
            time.sleep(0.05)
    return Claim(handle)
