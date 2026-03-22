import unittest

from modules.config import GitHubResource
from modules.github_issue_client import IssueRef, _resolve_issue_references, select_github_token


class GitHubIssueClientTests(unittest.TestCase):
    def test_resolve_issue_references_supports_owner_repo_and_repo_short_form(self) -> None:
        refs = list(
            _resolve_issue_references(
                "#1 repo2#2 owner3/repo3#3",
                default_owner="owner1",
                default_repo="repo1",
            )
        )

        self.assertEqual(
            [(ref.owner, ref.repo, ref.number) for ref in refs],
            [("owner1", "repo1", 1), ("owner1", "repo2", 2), ("owner3", "repo3", 3)],
        )

    def test_select_github_token_prefers_first_on_same_priority(self) -> None:
        ref = IssueRef(owner="owner", repo="repo", number=1, original_reference="owner/repo#1")
        resources = (
            GitHubResource(name="owner/*", api_key="TOKEN_FIRST"),
            GitHubResource(name="owner/*", api_key="TOKEN_SECOND"),
        )

        token = select_github_token(ref, resources)
        self.assertEqual(token, "TOKEN_FIRST")


if __name__ == "__main__":
    unittest.main()
