# AGENTS.md

## Project Overview

This repository contains `pr-tui`, a dependency-free Python/curses TUI for
reviewing GitHub pull requests through the GitHub CLI.

## Constraints

- Keep the app runnable on macOS with the system/developer Python and `gh`.
- Do not add third-party runtime dependencies unless the user explicitly asks.
- Use `gh` as the integration boundary for GitHub auth, org access, browser
  opening, PR review, CI inspection, and merge operations.
- Preserve keyboard-first workflows. Any new behavior should have a discoverable
  hotkey and should be reflected in `README.md`.
- Avoid destructive behavior without an explicit confirmation prompt.
- Default install/update/release repository is `c-gerke/pr-tui`. Keep override
  flags/env vars working for forks and private copies.

## Verification

Run these checks after editing:

```sh
python3 -m py_compile pr-tui
python3 -m unittest discover -s tests
./pr-tui --help
python3 tests/smoke_curses.py
sh -n install.sh
```

Manual GitHub actions such as approving and merging require a real PR and should
not be exercised in automated checks.
