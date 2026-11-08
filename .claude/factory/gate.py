#!/usr/bin/env python3
"""The factory gate's entry point: `python3 .claude/factory/gate.py <command>`.

The gate is the package beside this file (`gate/`); `python3 gate.py` with no command prints the usage.
Python 3.9+, standard library only.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gate.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(sys.argv))
