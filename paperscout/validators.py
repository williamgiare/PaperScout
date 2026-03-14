"""Validation and construction helpers for PaperScout inputs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .model import DateRange, OutputConfig, SearchFilters, SearchLimits, SearchRequest


CURRENT_YEAR = date.today().year
MIN_SUPPORTED_YEAR = 1900


@dataclass(frozen=True, slots=True)
class YearRangeInput:
    """Raw year-only boundaries provided by a caller or CLI layer."""

    from_year: int | None = None
    to_year: int | None = None


def validate_year(year: int, *, field_name: str) -> int:
    """Validate a single year boundary."""

    if year < MIN_SUPPORTED_YEAR:
        raise ValueError(
            f"{field_name} must be greater than or equal to {MIN_SUPPORTED_YEAR}."
        )

    if year > CURRENT_YEAR:
        raise ValueError(f"{field_name} cannot be later than {CURRENT_YEAR}.")

    return year


def build_date_range(*, from_year: int | None = None, to_year: int | None = None) -> DateRange:
    """Build an inclusive DateRange from year-only inputs."""

    start = None
    end = None

    if from_year is not None:
        validated_from_year = validate_year(from_year, field_name="from_year")
        start = date(validated_from_year, 1, 1)

    if to_year is not None:
        validated_to_year = validate_year(to_year, field_name="to_year")
        end = date(validated_to_year, 12, 31)

    return DateRange(start=start, end=end)


def build_search_filters(
    *,
    keywords: list[str] | tuple[str, ...] | None = None,
    author: str | list[str] | tuple[str, ...] | None = None,
    collaboration: str | None = None,
    min_citations: int | None = None,
    from_year: int | None = None,
    to_year: int | None = None,
) -> SearchFilters:
    """Create validated search filters from raw user input."""

    normalized_keywords = tuple(keywords or ())
    if author is None:
        normalized_authors: tuple[str, ...] = ()
    elif isinstance(author, str):
        normalized_authors = (author,)
    else:
        normalized_authors = tuple(author)

    if min_citations is not None and min_citations < 0:
        raise ValueError("min_citations must be greater than or equal to 0.")

    filters = SearchFilters(
        keywords=normalized_keywords,
        authors=normalized_authors,
        collaboration=collaboration,
        min_citations=min_citations,
        date_range=build_date_range(from_year=from_year, to_year=to_year),
    )

    if not filters.has_primary_filter:
        raise ValueError(
            "At least one primary filter is required: keywords, author, or collaboration."
        )

    return filters


def build_output_config(
    destination: str | Path,
    *,
    overwrite: bool = False,
    create_parent_directories: bool = True,
) -> OutputConfig:
    """Create validated output configuration."""

    return OutputConfig(
        destination=Path(destination),
        overwrite=overwrite,
        create_parent_directories=create_parent_directories,
    )


def build_search_limits(
    *,
    page_size: int = 250,
    preflight_warning_threshold: int = 1_000,
    hard_result_limit: int = 5_000,
) -> SearchLimits:
    """Create validated operational search limits."""

    return SearchLimits(
        page_size=page_size,
        preflight_warning_threshold=preflight_warning_threshold,
        hard_result_limit=hard_result_limit,
    )


def build_search_request(
    *,
    destination: str | Path,
    keywords: list[str] | tuple[str, ...] | None = None,
    author: str | list[str] | tuple[str, ...] | None = None,
    collaboration: str | None = None,
    min_citations: int | None = None,
    from_year: int | None = None,
    to_year: int | None = None,
    overwrite: bool = False,
    create_parent_directories: bool = True,
    page_size: int = 250,
    preflight_warning_threshold: int = 1_000,
    hard_result_limit: int = 5_000,
) -> SearchRequest:
    """Build a fully validated SearchRequest from raw parameters."""

    filters = build_search_filters(
        keywords=keywords,
        author=author,
        collaboration=collaboration,
        min_citations=min_citations,
        from_year=from_year,
        to_year=to_year,
    )
    output = build_output_config(
        destination,
        overwrite=overwrite,
        create_parent_directories=create_parent_directories,
    )
    limits = build_search_limits(
        page_size=page_size,
        preflight_warning_threshold=preflight_warning_threshold,
        hard_result_limit=hard_result_limit,
    )

    return SearchRequest(filters=filters, output=output, limits=limits)
