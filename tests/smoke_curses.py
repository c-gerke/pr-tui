#!/usr/bin/env python3
import os
import pathlib
import pty
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]


def main() -> int:
    os.environ["TERM"] = "xterm-256color"
    status = pty.spawn([str(ROOT / "pr-tui"), "--smoke-test"])
    return os.waitstatus_to_exitcode(status)


if __name__ == "__main__":
    sys.exit(main())
