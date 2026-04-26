# pr-tui

`pr-tui` is a small macOS-friendly terminal UI for working through GitHub pull
requests that need your review. It uses the installed `gh` CLI for all GitHub
auth, search, browser, CI, review, and merge actions.

## Requirements

- macOS or another terminal with Python 3 and curses support
- GitHub CLI authenticated with the accounts/orgs you need:

```sh
gh auth status
```

## Install

Releases publish a standalone `pr-tui` script plus `install.sh`. The installer
targets `/usr/local/bin/pr-tui` by default and refuses to continue if
`/usr/local/bin` is not already in `PATH`.

For the latest public release:

```sh
curl -fsSL https://github.com/c-gerke/pr-tui/releases/latest/download/install.sh | sh
```

For a private repository or org release, use authenticated `gh`:

```sh
tmp="$(mktemp -d)" && gh release download -R c-gerke/pr-tui -p install.sh -O "$tmp/install.sh" && sh "$tmp/install.sh"
```

Confirm the installed PATH location:

```sh
command -v pr-tui
```

If you want a different confirmed PATH directory:

```sh
curl -fsSL https://github.com/c-gerke/pr-tui/releases/latest/download/install.sh | INSTALL_DIR="$HOME/.local/bin" sh
```

## Update

Update an installed copy from the latest GitHub release:

```sh
pr-tui --self-update
```

Or pass the repository as a flag:

```sh
pr-tui --self-update --update-repo c-gerke/pr-tui
```

## Run

```sh
./pr-tui
```

By default it searches open PRs requesting your review:

```sh
gh search prs review-requested:@me --state open
```

Limit the search to specific orgs, users, or repositories:

```sh
./pr-tui --owner my-org --owner my-user
./pr-tui --repo my-org/service-a --repo my-user/dotfiles
```

Use a different GitHub search query when you want a broader queue:

```sh
./pr-tui --query "review-requested:@me -is:draft"
./pr-tui --query "involves:@me review:required"
```

## Hotkeys

| Key | Action |
| --- | --- |
| `j` / `k` | Move selection |
| `J` / `K` | Page selection |
| `g` / `G` | Jump to top/bottom |
| `v` / `Enter` | Load PR details |
| `c` | Load latest CI checks |
| `w` | Open CI checks in browser |
| `o` | Open PR in browser |
| `a` | Approve selected PR |
| `e` | Enable auto-merge for selected PR, with merge method prompt |
| `m` | Merge selected PR: squash, merge commit, rebase, or auto |
| `/` | Filter the loaded PR list locally |
| `r` / `F5` | Refresh PRs |
| `Tab` | Cycle the focused pane |
| `q` / `Esc` | Quit |

## Useful Options

```text
--owner OWNER           Limit search to an owner/org. Repeatable.
--repo OWNER/REPO       Limit search to a repository. Repeatable.
--query QUERY           GitHub PR search query.
--limit N               Maximum PRs to fetch. Default: 50.
--state open|closed     PR state. Default: open.
--refresh-seconds N     Auto-refresh interval. Default: 300. Use 0 to disable.
--include-drafts        Include draft PRs in the list.
--self-update           Update this executable from the latest GitHub release.
--update-repo OWNER/REPO
                        Repository to update from.
```

## Development

Run the same local checks used by CI:

```sh
python3 -m py_compile pr-tui
python3 -m unittest discover -s tests
./pr-tui --help
python3 tests/smoke_curses.py
sh -n install.sh
```

Releases are published by `.github/workflows/release.yml` when a `v*` tag is
pushed, or manually through the workflow dispatch input.
