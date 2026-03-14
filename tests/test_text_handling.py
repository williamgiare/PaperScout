"""Regression tests for Unicode and special-character handling."""

from __future__ import annotations

import unittest
from unicodedata import normalize

from paperscout.query_builder import InspireQueryBuilder
from paperscout.validators import build_search_filters


class TextHandlingTests(unittest.TestCase):
    def test_author_is_normalized_to_nfc(self) -> None:
        decomposed_name = "Giare\u0300"
        filters = build_search_filters(author=decomposed_name)

        self.assertEqual(filters.authors, (normalize("NFC", decomposed_name),))

    def test_keyword_is_normalized_to_nfc(self) -> None:
        decomposed_keyword = "inflazio\u0301n"
        filters = build_search_filters(keywords=[decomposed_keyword])

        self.assertEqual(filters.keywords, (normalize("NFC", decomposed_keyword),))

    def test_query_builder_preserves_accented_text(self) -> None:
        filters = build_search_filters(author="Giarè", keywords=["inflation"])
        query = InspireQueryBuilder().build(filters)

        self.assertIn('a:"Giarè"', query.query)
        self.assertIn('a:"Giare"', query.query)

    def test_query_builder_escapes_quotes_and_backslashes(self) -> None:
        filters = build_search_filters(
            author='O"Neil\\Test',
            keywords=['effective "field" theory'],
        )
        query = InspireQueryBuilder().build(filters)

        self.assertIn('a:"O\\"Neil\\\\Test"', query.query)
        self.assertIn('t:"effective \\"field\\" theory"', query.query)

    def test_multiple_authors_remain_anded(self) -> None:
        filters = build_search_filters(author=["Linde", "Starobinsky"])
        query = InspireQueryBuilder().build(filters)

        self.assertEqual(query.query, '(a:"Linde" and a:"Starobinsky")')

    def test_collaboration_gets_unaccented_fallback(self) -> None:
        filters = build_search_filters(collaboration="Collabòration")
        query = InspireQueryBuilder().build(filters)

        self.assertIn('cn:"Collabòration"', query.query)
        self.assertIn('cn:"Collaboration"', query.query)


if __name__ == "__main__":
    unittest.main()
