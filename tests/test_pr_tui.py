import contextlib
import importlib.util
import importlib.machinery
import io
import json
import tempfile
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
LOADER = importlib.machinery.SourceFileLoader("pr_tui", str(ROOT / "pr-tui"))
SPEC = importlib.util.spec_from_loader("pr_tui", LOADER)
pr_tui = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = pr_tui
SPEC.loader.exec_module(pr_tui)


class SearchCommandTests(unittest.TestCase):
    def test_query_is_placed_after_separator(self):
        args = pr_tui.Args(
            owners=[],
            repos=[],
            query="review-requested:@me -is:draft",
            limit=25,
            state="open",
            refresh_seconds=0,
            include_drafts=False,
        )

        command = pr_tui.build_search_command(args)

        self.assertEqual(command[:3], ["gh", "search", "prs"])
        self.assertIn("--json", command)
        self.assertEqual(command[-3:], ["--", "review-requested:@me", "-is:draft"])

    def test_owner_and_repo_filters_are_repeatable(self):
        args = pr_tui.Args(
            owners=["example-org", "personal-user"],
            repos=["example-org/api", "personal-user/dotfiles"],
            query="review-requested:@me",
            limit=50,
            state="open",
            refresh_seconds=300,
            include_drafts=False,
        )

        command = pr_tui.build_search_command(args)

        self.assertEqual(command.count("--owner"), 2)
        self.assertEqual(command.count("--repo"), 2)
        self.assertIn("example-org/api", command)
        self.assertIn("personal-user/dotfiles", command)


class ParsingTests(unittest.TestCase):
    def test_pull_request_from_search_json(self):
        item = {
            "number": 123,
            "repository": {"nameWithOwner": "octo/example"},
            "title": "Improve review flow",
            "url": "https://github.com/octo/example/pull/123",
            "state": "open",
            "isDraft": False,
            "author": {"login": "mona"},
            "updatedAt": "2026-04-26T20:00:00Z",
            "createdAt": "2026-04-25T20:00:00Z",
            "commentsCount": 2,
            "labels": [{"name": "tui"}],
            "assignees": [{"login": "hubot"}],
        }

        pr = pr_tui.PullRequest.from_json(item)

        self.assertEqual(pr.repo, "octo/example")
        self.assertEqual(pr.number, 123)
        self.assertEqual(pr.author, "mona")
        self.assertEqual(pr.labels, ["tui"])
        self.assertEqual(pr.assignees, ["hubot"])

    def test_review_requests_include_users_and_teams(self):
        requests = [
            {"requestedReviewer": {"login": "mona"}},
            {"__typename": "Team", "slug": "octo/platform-reviewers"},
        ]

        self.assertEqual(
            pr_tui.users_from_review_requests(requests),
            ["mona", "octo/platform-reviewers"],
        )

    def test_status_rollup_summary_counts_states(self):
        rollup = [
            {"conclusion": "SUCCESS"},
            {"conclusion": "SUCCESS"},
            {"status": "IN_PROGRESS"},
            {"state": "FAILURE"},
        ]

        self.assertEqual(
            pr_tui.summarize_status_rollup(rollup),
            "FAILURE:1, IN_PROGRESS:1, SUCCESS:2",
        )


class FormattingTests(unittest.TestCase):
    def test_fit_uses_ascii_ellipsis(self):
        self.assertEqual(pr_tui.fit("abcdef", 5), "ab...")
        self.assertEqual(pr_tui.compact("abcdef", 2), "..")


class MarkedPrTests(unittest.TestCase):
    def _make_state(self, prs: list[pr_tui.PullRequest], filter_text: str = "") -> pr_tui.State:
        args = pr_tui.Args(
            owners=[],
            repos=[],
            query="review-requested:@me",
            limit=50,
            state="open",
            refresh_seconds=0,
            include_drafts=False,
        )
        state = pr_tui.State(args=args, prs=prs, filter_text=filter_text)
        return state

    def _pr(self, repo: str, number: int, title: str = "title") -> pr_tui.PullRequest:
        return pr_tui.PullRequest(
            number=number,
            repo=repo,
            title=title,
            url=f"https://github.com/{repo}/pull/{number}",
            state="open",
            is_draft=False,
            author="mona",
            updated_at="2026-04-26T20:00:00Z",
            created_at="2026-04-25T20:00:00Z",
            comments_count=0,
        )

    def test_toggle_mark_adds_and_removes_key(self):
        pr = self._pr("octo/a", 1)
        state = self._make_state([pr])

        state.toggle_mark(pr)
        self.assertEqual(state.marked, {("octo/a", 1)})

        state.toggle_mark(pr)
        self.assertEqual(state.marked, set())

    def test_marked_prs_preserves_filtered_order(self):
        prs = [self._pr("octo/a", 1), self._pr("octo/b", 2), self._pr("octo/c", 3)]
        state = self._make_state(prs)
        state.toggle_mark(prs[2])
        state.toggle_mark(prs[0])

        self.assertEqual(pr_tui.pr_key(prs[0]), ("octo/a", 1))
        self.assertEqual(state.marked_prs(), [prs[0], prs[2]])

    def test_prune_marks_removes_stale_keys(self):
        prs = [self._pr("octo/a", 1), self._pr("octo/b", 2)]
        state = self._make_state(prs)
        state.marked = {("octo/a", 1), ("octo/b", 2), ("octo/gone", 99)}

        state.prune_marks()

        self.assertEqual(state.marked, {("octo/a", 1), ("octo/b", 2)})

    def test_resolve_action_targets_prefers_marked_prs(self):
        prs = [self._pr("octo/a", 1), self._pr("octo/b", 2)]
        state = self._make_state(prs)
        state.selected = 0
        state.toggle_mark(prs[1])

        targets = pr_tui.resolve_action_targets(state)

        self.assertEqual(targets, [prs[1]])

    def test_resolve_action_targets_falls_back_to_current(self):
        prs = [self._pr("octo/a", 1), self._pr("octo/b", 2)]
        state = self._make_state(prs)
        state.selected = 1

        targets = pr_tui.resolve_action_targets(state)

        self.assertEqual(targets, [prs[1]])


class ScopeFilterTests(unittest.TestCase):
    def _pr(self, repo: str, number: int) -> pr_tui.PullRequest:
        return pr_tui.PullRequest(
            number=number,
            repo=repo,
            title="title",
            url=f"https://github.com/{repo}/pull/{number}",
            state="open",
            is_draft=False,
            author="mona",
            updated_at="2026-04-26T20:00:00Z",
            created_at="2026-04-25T20:00:00Z",
            comments_count=0,
        )

    def test_repo_owner_returns_first_path_segment(self):
        pr = self._pr("octo-corp/example", 1)
        self.assertEqual(pr_tui.repo_owner(pr), "octo-corp")

    def test_filter_prs_by_owner(self):
        prs = [
            self._pr("octo/a", 1),
            self._pr("octo/b", 2),
            self._pr("hubot/dotfiles", 3),
        ]
        filtered = pr_tui.filter_prs(prs, filter_owner="octo")
        self.assertEqual([pr.repo for pr in filtered], ["octo/a", "octo/b"])

    def test_filter_prs_by_repo(self):
        prs = [
            self._pr("octo/a", 1),
            self._pr("octo/b", 2),
            self._pr("hubot/dotfiles", 3),
        ]
        filtered = pr_tui.filter_prs(prs, filter_repo="octo/b")
        self.assertEqual([pr.repo for pr in filtered], ["octo/b"])

    def test_scope_and_text_filters_combine(self):
        prs = [
            self._pr("octo/a", 1),
            self._pr("octo/b", 2),
            self._pr("hubot/dotfiles", 3),
        ]
        filtered = pr_tui.filter_prs(prs, filter_owner="octo", filter_text="b")
        self.assertEqual([pr.repo for pr in filtered], ["octo/b"])


class ConfigTests(unittest.TestCase):
    def test_missing_config_returns_defaults(self):
        missing = pathlib.Path(tempfile.gettempdir()) / "pr-tui-config-missing"
        config = pr_tui.load_config(missing)
        self.assertEqual(config, pr_tui.Config())

    def test_load_config_parses_merge_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "config.json"
            path.write_text(
                json.dumps(
                    {
                        "auto_merge": {"method": "squash"},
                        "merge": {"method": "rebase", "delete_branch": True},
                    }
                ),
                encoding="utf-8",
            )
            config = pr_tui.load_config(path)
        self.assertEqual(config.auto_merge_method, "s")
        self.assertEqual(config.merge_method, "r")
        self.assertTrue(config.merge_delete_branch)

    def test_invalid_auto_merge_method_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "config.json"
            path.write_text(
                json.dumps({"auto_merge": {"method": "fast-forward"}}),
                encoding="utf-8",
            )
            with self.assertRaises(pr_tui.ConfigError):
                pr_tui.load_config(path)

    def test_resolve_config_path_prefers_cli_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "custom.json"
            path.touch()
            resolved = pr_tui.resolve_config_path(str(path))
        self.assertEqual(resolved, path)

    def test_default_config_paths_include_xdg_and_home_fallback(self):
        paths = pr_tui.default_config_paths()
        self.assertEqual(paths[0], pathlib.Path.home() / ".config" / "pr-tui" / "config.json")
        self.assertEqual(paths[1], pathlib.Path.home() / ".pr-tui.json")


class SelfUpdateTests(unittest.TestCase):
    def test_default_update_repo_is_configured(self):
        self.assertEqual(pr_tui.DEFAULT_UPDATE_REPO, "c-gerke/pr-tui")

    def test_self_update_reports_missing_target_before_download(self):
        missing = pathlib.Path(tempfile.gettempdir()) / "pr-tui-definitely-missing"
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(pr_tui.self_update(None, str(missing)), 2)


if __name__ == "__main__":
    unittest.main()
