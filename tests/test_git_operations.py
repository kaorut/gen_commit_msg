import unittest

from modules.git_operations import (
    _resolve_revision_diff_target,
    _should_include_unstaged_diff,
    parse_owner_repo_from_remote_url,
)


class GitOperationsTests(unittest.TestCase):
    def test_single_revision_maps_to_one_commit_range(self) -> None:
        target = _resolve_revision_diff_target("HEAD", original_revision_spec="HEAD")
        self.assertEqual(target, "HEAD^..HEAD")

    def test_two_dot_revision_is_preserved(self) -> None:
        target = _resolve_revision_diff_target("a..b", original_revision_spec="a..b")
        self.assertEqual(target, "a..b")

    def test_three_dot_revision_is_preserved(self) -> None:
        target = _resolve_revision_diff_target("a...b", original_revision_spec="a...b")
        self.assertEqual(target, "a...b")

    def test_unstaged_included_only_when_flag_is_true(self) -> None:
        self.assertFalse(_should_include_unstaged_diff(include_unstaged=False))
        self.assertTrue(_should_include_unstaged_diff(include_unstaged=True))

    def test_parses_ssh_remote_url(self) -> None:
        owner, repo = parse_owner_repo_from_remote_url("git@github.com:octocat/hello-world.git")
        self.assertEqual((owner, repo), ("octocat", "hello-world"))

    def test_parses_https_remote_url(self) -> None:
        owner, repo = parse_owner_repo_from_remote_url("https://github.com/octocat/hello-world.git")
        self.assertEqual((owner, repo), ("octocat", "hello-world"))


if __name__ == "__main__":
    unittest.main()
