import contextlib
import importlib.util
import importlib.machinery
import io
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


class SelfUpdateTests(unittest.TestCase):
    def test_default_update_repo_is_configured(self):
        self.assertEqual(pr_tui.DEFAULT_UPDATE_REPO, "c-gerke/pr-tui")

    def test_self_update_reports_missing_target_before_download(self):
        missing = pathlib.Path(tempfile.gettempdir()) / "pr-tui-definitely-missing"
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(pr_tui.self_update(None, str(missing)), 2)


if __name__ == "__main__":
    unittest.main()
