"""High-level Python API for interactive PaperScout usage."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .bibtex_exporter import BibtexExporter
from .cite import cite
from .service import (
    PaperScoutService,
    PreparedSearch,
    SearchEstimateResult,
    SearchExecutionResult,
)
from .validators import build_search_request


_DEFAULT_INTERACTIVE_OUTPUT = Path("paperscout.bib")


@dataclass(frozen=True, slots=True)
class SaveResult:
    """Saved-file result for the high-level Python API."""

    execution_result: SearchExecutionResult
    saved_path: Path | None = None


def preview(
    *,
    keywords: list[str] | tuple[str, ...] | None = None,
    author: str | list[str] | tuple[str, ...] | None = None,
    collaboration: str | None = None,
    min_citations: int | None = None,
    from_year: int | None = None,
    to_year: int | None = None,
    page_size: int = 250,
    warning_threshold: int = 1_000,
    hard_limit: int = 5_000,
) -> PreparedSearch:
    """Prepare a search for interactive inspection without remote execution."""

    request = _build_interactive_request(
        keywords=keywords,
        author=author,
        collaboration=collaboration,
        min_citations=min_citations,
        from_year=from_year,
        to_year=to_year,
        page_size=page_size,
        warning_threshold=warning_threshold,
        hard_limit=hard_limit,
    )
    return PaperScoutService().prepare_search(request)


def estimate(
    *,
    keywords: list[str] | tuple[str, ...] | None = None,
    author: str | list[str] | tuple[str, ...] | None = None,
    collaboration: str | None = None,
    min_citations: int | None = None,
    from_year: int | None = None,
    to_year: int | None = None,
    page_size: int = 250,
    warning_threshold: int = 1_000,
    hard_limit: int = 5_000,
    force: bool = False,
) -> SearchEstimateResult:
    """Estimate matching papers using INSPIRE preflight only."""

    request = _build_interactive_request(
        keywords=keywords,
        author=author,
        collaboration=collaboration,
        min_citations=min_citations,
        from_year=from_year,
        to_year=to_year,
        page_size=page_size,
        warning_threshold=warning_threshold,
        hard_limit=hard_limit,
    )
    return PaperScoutService().estimate_search(request, force=force)


def save(
    *,
    output: str | Path,
    keywords: list[str] | tuple[str, ...] | None = None,
    author: str | list[str] | tuple[str, ...] | None = None,
    collaboration: str | None = None,
    min_citations: int | None = None,
    from_year: int | None = None,
    to_year: int | None = None,
    overwrite: bool = False,
    page_size: int = 250,
    warning_threshold: int = 1_000,
    hard_limit: int = 5_000,
    force: bool = False,
) -> SaveResult:
    """Execute a search, save its BibTeX file, and return the result."""

    request = build_search_request(
        destination=Path(output),
        keywords=keywords,
        author=author,
        collaboration=collaboration,
        min_citations=min_citations,
        from_year=from_year,
        to_year=to_year,
        overwrite=overwrite,
        page_size=page_size,
        preflight_warning_threshold=warning_threshold,
        hard_result_limit=hard_limit,
    )
    execution_result = PaperScoutService().execute_search(request, force=force)

    if execution_result.execution_plan.should_abort:
        warnings_text = " ".join(execution_result.warnings)
        raise RuntimeError(f"Search aborted before saving. {warnings_text}".strip())

    if execution_result.execution_plan.requires_confirmation:
        warnings_text = " ".join(execution_result.warnings)
        raise RuntimeError(
            f"Search requires confirmation or force. {warnings_text}".strip()
        )

    if execution_result.execution_plan.total_results == 0:
        return SaveResult(execution_result=execution_result, saved_path=None)

    saved_path = BibtexExporter().save(execution_result.bibtex_content, request.output)
    return SaveResult(execution_result=execution_result, saved_path=saved_path)


def _build_interactive_request(
    *,
    keywords: list[str] | tuple[str, ...] | None = None,
    author: str | list[str] | tuple[str, ...] | None = None,
    collaboration: str | None = None,
    min_citations: int | None = None,
    from_year: int | None = None,
    to_year: int | None = None,
    page_size: int = 250,
    warning_threshold: int = 1_000,
    hard_limit: int = 5_000,
):
    return build_search_request(
        destination=_DEFAULT_INTERACTIVE_OUTPUT,
        keywords=keywords,
        author=author,
        collaboration=collaboration,
        min_citations=min_citations,
        from_year=from_year,
        to_year=to_year,
        page_size=page_size,
        preflight_warning_threshold=warning_threshold,
        hard_result_limit=hard_limit,
    )
