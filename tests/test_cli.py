import unittest

from modules.cli import parse_arguments, validate_issue_reference


class CliParsingTests(unittest.TestCase):
    def test_accepts_owner_repo_issue_reference(self) -> None:
        options = parse_arguments(["owner/repo#123"])
        self.assertEqual(options.issue_reference, "owner/repo#123")
        self.assertEqual(options.revision_spec, "")

    def test_amend_sets_default_revision_spec(self) -> None:
        options = parse_arguments(["--amend"])
        self.assertEqual(options.revision_spec, "HEAD^..HEAD")

    def test_invalid_issue_reference_raises(self) -> None:
        with self.assertRaises(ValueError):
            validate_issue_reference("owner/repo")

    def test_without_all_option_does_not_include_unstaged(self) -> None:
        options = parse_arguments(["HEAD"])
        self.assertFalse(options.include_unstaged_for_diff)

    def test_with_all_option_includes_unstaged(self) -> None:
        options = parse_arguments(["HEAD", "--all"])
        self.assertTrue(options.include_unstaged_for_diff)


if __name__ == "__main__":
    unittest.main()
