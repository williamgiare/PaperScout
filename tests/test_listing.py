"""Tests for paper listing extraction, formatting, and persistence."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from paperscout.listing import (
    ListedPaper,
    build_listed_paper,
    format_paper_list,
    format_paper_listing,
    save_paper_list,
)


class ListingTests(unittest.TestCase):
    def test_build_listed_paper_prefers_arxiv_over_doi(self) -> None:
        hit = {
            "metadata": {
                "titles": [{"title": "Inflation paper"}],
                "authors": [{"full_name": "A. Author"}, {"full_name": "B. Author"}],
                "arxiv_eprints": [{"value": "2503.12345"}],
                "dois": [{"value": "10.1000/example"}],
                "citation_count": 42,
            }
        }

        paper = build_listed_paper(hit)

        self.assertEqual(paper.title, "Inflation paper")
        self.assertEqual(paper.authors, ("A. Author", "B. Author"))
        self.assertEqual(paper.identifier, "arXiv:2503.12345")
        self.assertEqual(paper.citations, 42)

    def test_build_listed_paper_falls_back_to_doi(self) -> None:
        hit = {
            "metadata": {
                "titles": [{"title": "No arXiv paper"}],
                "authors": [{"full_name": "Only Author"}],
                "dois": [{"value": "10.2000/fallback"}],
            }
        }

        paper = build_listed_paper(hit)

        self.assertEqual(paper.identifier, "DOI:10.2000/fallback")

    def test_format_paper_listing_truncates_authors_with_et_al(self) -> None:
        paper = ListedPaper(
            title="A title",
            authors=("Author A", "Author B", "Author C", "Author D"),
            identifier="arXiv:1234.5678",
            citations=100,
        )

        line = format_paper_listing(paper, max_authors=3, show_citations=True)

        self.assertEqual(
            line,
            '- "A title" (Author A, Author B, Author C, et al.) '
            "arXiv:1234.5678 (cit: 100)",
        )

    def test_format_paper_listing_handles_unknown_authors(self) -> None:
        paper = ListedPaper(title="Untitled", authors=(), identifier=None, citations=None)

        line = format_paper_listing(paper)

        self.assertEqual(line, '- "Untitled" (unknown authors)')

    def test_format_paper_list_returns_friendly_empty_message(self) -> None:
        self.assertEqual(
            format_paper_list(()),
            "No papers matched the current search filters.",
        )

    def test_save_paper_list_writes_txt_file(self) -> None:
        with TemporaryDirectory() as tmpdir:
            destination = Path(tmpdir) / "papers.txt"

            saved_path = save_paper_list('- "Title" (Author)', destination)

            self.assertEqual(saved_path, destination)
            self.assertEqual(destination.read_text(encoding="utf-8"), '- "Title" (Author)\n')

    def test_save_paper_list_rejects_non_txt_extension(self) -> None:
        with TemporaryDirectory() as tmpdir:
            with self.assertRaises(ValueError):
                save_paper_list("text", Path(tmpdir) / "papers.md")


if __name__ == "__main__":
    unittest.main()
