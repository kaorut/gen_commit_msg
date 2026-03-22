import unittest

from ai_commit import normalize_generated_message


class CommitNormalizationModeTests(unittest.TestCase):
    def test_strict_mode_applies_conventional_normalization(self) -> None:
        message = "Fix bug in parser"
        normalized = normalize_generated_message(
            message,
            issue_reference="",
            normalization_mode="strict",
        )
        self.assertTrue(normalized.startswith("chore:"))

    def test_loose_mode_keeps_subject_shape(self) -> None:
        message = "Fix bug in parser"
        normalized = normalize_generated_message(
            message,
            issue_reference="",
            normalization_mode="loose",
        )
        self.assertEqual(normalized, "Fix bug in parser")


if __name__ == "__main__":
    unittest.main()
