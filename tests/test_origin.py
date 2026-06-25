import unittest

from parrot.origin import OriginMessage, analyze_origin, is_exact_match


class OriginTest(unittest.TestCase):
	def test_analyze_origin_tracks_exact_use_and_mutations(self) -> None:
		report = analyze_origin(
			"Deltacobell",
			[
				OriginMessage(
					id=100,
					author_id=1,
					content="my actual fuck voted del taco bell",
				),
				OriginMessage(id=200, author_id=1, content="Deltacobell"),
				OriginMessage(id=300, author_id=2, content="Del Taco Bell"),
				OriginMessage(id=400, author_id=2, content="Deltacobellian"),
				OriginMessage(id=500, author_id=3, content="unrelated"),
			],
		)

		self.assertEqual(
			report.precursor.content,
			"my actual fuck voted del taco bell",
		)
		self.assertEqual(report.first_exact.content, "Deltacobell")
		self.assertEqual(
			[message.content for message in report.descendants],
			["Del Taco Bell", "Deltacobellian"],
		)
		self.assertEqual(report.custodian_ids, (2, 1))

	def test_reports_best_precursor_when_exact_missing(self) -> None:
		report = analyze_origin(
			"Deltacobell",
			[
				OriginMessage(id=100, author_id=1, content="Del Taco Bell"),
				OriginMessage(id=200, author_id=2, content="unrelated"),
			],
		)

		self.assertEqual(report.precursor.content, "Del Taco Bell")
		self.assertIsNone(report.first_exact)
		self.assertEqual(report.descendants, ())
		self.assertEqual(report.custodian_ids, ())

	def test_exact_match_respects_alphanumeric_boundaries(self) -> None:
		self.assertTrue(is_exact_match("Deltacobell", "wow, deltacobell!"))
		self.assertFalse(is_exact_match("Deltacobell", "Deltacobellian"))


if __name__ == "__main__":
	unittest.main()
