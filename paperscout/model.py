"""Core domain models for PaperScout.

These models are intentionally strict: they normalize harmless input
differences early and reject inconsistent states before any HTTP query
or file output is attempted.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from pathlib import Path
from typing import Iterable
from unicodedata import normalize


def _normalize_text_value(value: str, *, field_name: str) -> str:
    normalized = normalize("NFC", " ".join(value.split()).strip())
    if not normalized:
        raise ValueError(f"{field_name} cannot be empty or whitespace only.")
    return normalized


def _normalize_optional_text(value: str | None, *, field_name: str) -> str | None:
    if value is None:
        return None

    return _normalize_text_value(value, field_name=field_name)


def _normalize_keywords(
    keywords: Iterable[str],
    *,
    allow_empty: bool = False,
) -> tuple[str, ...]:
    normalized_keywords: list[str] = []
    seen: set[str] = set()

    for raw_keyword in keywords:
        normalized = _normalize_text_value(raw_keyword, field_name="keyword")
        dedupe_key = normalized.casefold()
        if dedupe_key in seen:
            continue

        seen.add(dedupe_key)
        normalized_keywords.append(normalized)

    if not normalized_keywords and not allow_empty:
        raise ValueError("At least one keyword is required.")

    return tuple(normalized_keywords)


def _normalize_text_collection(
    values: Iterable[str],
    *,
    field_name: str,
    allow_empty: bool = False,
) -> tuple[str, ...]:
    normalized_values: list[str] = []
    seen: set[str] = set()

    for raw_value in values:
        normalized = _normalize_text_value(raw_value, field_name=field_name)
        dedupe_key = normalized.casefold()
        if dedupe_key in seen:
            continue

        seen.add(dedupe_key)
        normalized_values.append(normalized)

    if not normalized_values and not allow_empty:
        raise ValueError(f"At least one {field_name} value is required.")

    return tuple(normalized_values)


class SearchField(StrEnum):
    """Supported metadata fields for keyword matching."""

    TITLE = "title"
    ABSTRACT = "abstract"
    KEYWORDS = "keywords"


@dataclass(frozen=True, slots=True)
class DateRange:
    """Inclusive temporal boundaries for a search."""

    start: date | None = None
    end: date | None = None

    def __post_init__(self) -> None:
        if self.start and self.end and self.start > self.end:
            raise ValueError("DateRange.start cannot be later than DateRange.end.")

    @property
    def is_unbounded(self) -> bool:
        return self.start is None and self.end is None


@dataclass(frozen=True, slots=True)
class SearchFilters:
    """User-facing search filters, normalized into stable internal types."""

    keywords: tuple[str, ...]
    authors: tuple[str, ...] = ()
    collaboration: str | None = None
    min_citations: int | None = None
    date_range: DateRange = field(default_factory=DateRange)
    search_fields: tuple[SearchField, ...] = (
        SearchField.TITLE,
        SearchField.ABSTRACT,
        SearchField.KEYWORDS,
    )
    require_all_keywords: bool = True

    def __post_init__(self) -> None:
        normalized_keywords = _normalize_keywords(self.keywords, allow_empty=True)
        normalized_authors = _normalize_text_collection(
            self.authors,
            field_name="authors",
            allow_empty=True,
        )
        normalized_collaboration = _normalize_optional_text(
            self.collaboration,
            field_name="collaboration",
        )

        if self.min_citations is not None and self.min_citations < 0:
            raise ValueError("min_citations cannot be negative.")

        if not self.search_fields:
            raise ValueError("At least one search field is required.")

        normalized_search_fields = tuple(dict.fromkeys(self.search_fields))
        if any(not isinstance(field, SearchField) for field in normalized_search_fields):
            raise TypeError("search_fields must contain SearchField values only.")

        object.__setattr__(self, "keywords", normalized_keywords)
        object.__setattr__(self, "authors", normalized_authors)
        object.__setattr__(self, "collaboration", normalized_collaboration)
        object.__setattr__(self, "search_fields", normalized_search_fields)

    @property
    def has_person_filter(self) -> bool:
        return bool(self.authors) or self.collaboration is not None

    @property
    def has_primary_filter(self) -> bool:
        return bool(self.keywords) or self.has_person_filter


@dataclass(frozen=True, slots=True)
class OutputConfig:
    """Configuration for BibTeX output persistence."""

    destination: Path
    overwrite: bool = False
    create_parent_directories: bool = True

    def __post_init__(self) -> None:
        destination = Path(self.destination).expanduser()

        if destination.name in {"", ".", ".."}:
            raise ValueError("Output destination must be a concrete file path.")

        if destination.suffix.lower() != ".bib":
            raise ValueError("Output destination must use the .bib extension.")

        object.__setattr__(self, "destination", destination)


@dataclass(frozen=True, slots=True)
class SearchLimits:
    """Operational safety limits for remote execution."""

    page_size: int = 250
    preflight_warning_threshold: int = 1_000
    hard_result_limit: int = 5_000

    def __post_init__(self) -> None:
        if not 1 <= self.page_size <= 1_000:
            raise ValueError("page_size must be between 1 and 1000.")

        if self.preflight_warning_threshold < 1:
            raise ValueError("preflight_warning_threshold must be positive.")

        if self.hard_result_limit < self.preflight_warning_threshold:
            raise ValueError(
                "hard_result_limit cannot be smaller than preflight_warning_threshold."
            )


@dataclass(frozen=True, slots=True)
class SearchRequest:
    """Complete request object consumed by the application service layer."""

    filters: SearchFilters
    output: OutputConfig
    limits: SearchLimits = field(default_factory=SearchLimits)
