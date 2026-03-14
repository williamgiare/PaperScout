"""Tests for the high-level notebook-friendly API."""

from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from paperscout.api import estimate, preview, save


class ApiTests(unittest.TestCase):
    @patch("paperscout.api.PaperScoutService")
    def test_preview_delegates_to_service(self, service_cls) -> None:
        expected = object()
        service_cls.return_value.prepare_search.return_value = expected

        result = preview(keywords=["inflation"], author=["Starobinsky"])

        self.assertIs(result, expected)
        service_cls.return_value.prepare_search.assert_called_once()

    @patch("paperscout.api.PaperScoutService")
    def test_estimate_delegates_to_service(self, service_cls) -> None:
        expected = object()
        service_cls.return_value.estimate_search.return_value = expected

        result = estimate(keywords=["inflation"], author=["Starobinsky"])

        self.assertIs(result, expected)
        service_cls.return_value.estimate_search.assert_called_once()

    @patch("paperscout.api.BibtexExporter")
    @patch("paperscout.api.PaperScoutService")
    def test_save_writes_file_when_execution_succeeds(self, service_cls, exporter_cls) -> None:
        execution_result = SimpleNamespace(
            execution_plan=SimpleNamespace(
                should_abort=False,
                requires_confirmation=False,
                total_results=2,
            ),
            warnings=(),
            bibtex_content="@article{a,}\n",
        )
        service_cls.return_value.execute_search.return_value = execution_result
        exporter_cls.return_value.save.return_value = Path("output/test.bib")

        result = save(
            output="output/test.bib",
            keywords=["inflation"],
            author=["Starobinsky"],
        )

        self.assertEqual(result.saved_path, Path("output/test.bib"))
        exporter_cls.return_value.save.assert_called_once()

    @patch("paperscout.api.PaperScoutService")
    def test_save_raises_when_confirmation_is_required(self, service_cls) -> None:
        execution_result = SimpleNamespace(
            execution_plan=SimpleNamespace(
                should_abort=False,
                requires_confirmation=True,
                total_results=1001,
            ),
            warnings=("Large result set detected.",),
            bibtex_content="",
        )
        service_cls.return_value.execute_search.return_value = execution_result

        with self.assertRaises(RuntimeError):
            save(
                output="output/test.bib",
                keywords=["inflation"],
                author=["Starobinsky"],
            )


if __name__ == "__main__":
    unittest.main()
