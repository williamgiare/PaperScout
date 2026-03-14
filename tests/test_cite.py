"""Tests for LaTeX cite generation from BibTeX files."""

from __future__ import annotations

import unittest

from paperscout.cite import cite, parse_bibtex_text, sort_bib_entries


SAMPLE_BIB = """@article{Zeta2022,
  author = {Zeta, A.},
  title = {Paper Z},
  year = {2022},
  month = {nov}
}

@article{Alpha2024,
  author = {Alpha, A.},
  title = {Paper A},
  year = {2024},
  month = {feb}
}

@article{Beta2024,
  author = {Beta, B.},
  title = {Paper B},
  year = {2024},
  month = {jan}
}
"""


class CiteTests(unittest.TestCase):
    def test_parse_bibtex_text_extracts_keys_and_dates(self) -> None:
        entries = parse_bibtex_text(SAMPLE_BIB)

        self.assertEqual([entry.key for entry in entries], ["Zeta2022", "Alpha2024", "Beta2024"])
        self.assertEqual(entries[0].year, 2022)
        self.assertEqual(entries[0].month, 11)

    def test_sort_alpha_orders_by_key(self) -> None:
        entries = parse_bibtex_text(SAMPLE_BIB)
        sorted_entries = sort_bib_entries(entries, sort="alpha")

        self.assertEqual([entry.key for entry in sorted_entries], ["Alpha2024", "Beta2024", "Zeta2022"])

    def test_sort_date_orders_by_recent_year_then_month(self) -> None:
        entries = parse_bibtex_text(SAMPLE_BIB)
        sorted_entries = sort_bib_entries(entries, sort="date")

        self.assertEqual([entry.key for entry in sorted_entries], ["Zeta2022", "Beta2024", "Alpha2024"])

    def test_build_latex_cite_uses_file_order_by_default(self) -> None:
        with self.assertRaises(FileNotFoundError):
            cite("missing-file.bib")

    def test_build_latex_cite_from_temp_file(self) -> None:
        from pathlib import Path
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as tmpdir:
            bib_path = Path(tmpdir) / "sample.bib"
            bib_path.write_text(SAMPLE_BIB, encoding="utf-8")

            self.assertEqual(
                cite(bib_path),
                r"\cite{Zeta2022,Alpha2024,Beta2024}",
            )
            self.assertEqual(
                cite(bib_path, sort="alpha"),
                r"\cite{Alpha2024,Beta2024,Zeta2022}",
            )
            self.assertEqual(
                cite(bib_path, sort="date"),
                r"\cite{Zeta2022,Beta2024,Alpha2024}",
            )


if __name__ == "__main__":
    unittest.main()
