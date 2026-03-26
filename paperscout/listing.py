"""Helpers for turning INSPIRE JSON hits into readable paper listings."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


_UNKNOWN_AUTHORS = "unknown authors"
_UNTITLED_PAPER = "Untitled paper"


@dataclass(frozen=True, slots=True)
class ListedPaper:
    """Minimal paper metadata for human-readable search listings."""

    title: str
    authors: tuple[str, ...]
    identifier: str | None = None
    citations: int | None = None

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("title cannot be empty.")

        if any(not author.strip() for author in self.authors):
            raise ValueError("authors cannot contain empty names.")

        if self.identifier is not None and not self.identifier.strip():
            raise ValueError("identifier cannot be empty when provided.")

        if self.citations is not None and self.citations < 0:
            raise ValueError("citations cannot be negative.")


def build_listed_papers(hits: list[dict[str, Any]] | tuple[dict[str, Any], ...]) -> tuple[ListedPaper, ...]:
    """Convert raw INSPIRE search hits into normalized ListedPaper objects."""

    return tuple(build_listed_paper(hit) for hit in hits)


def build_listed_paper(hit: dict[str, Any]) -> ListedPaper:
    """Build one listed paper from an INSPIRE hit payload."""

    metadata = _extract_metadata(hit)
    return ListedPaper(
        title=_extract_title(metadata),
        authors=_extract_authors(metadata),
        identifier=_extract_identifier(metadata),
        citations=_extract_citations(metadata),
    )


def format_paper_listing(
    paper: ListedPaper,
    *,
    max_authors: int = 3,
    show_citations: bool = False,
) -> str:
    """Format one paper as a single human-readable list item."""

    if max_authors < 1:
        raise ValueError("max_authors must be at least 1.")

    displayed_authors = _format_authors(paper.authors, max_authors=max_authors)
    parts = [f'- "{paper.title}" ({displayed_authors})']

    if paper.identifier is not None:
        parts.append(paper.identifier)

    if show_citations and paper.citations is not None:
        parts.append(f"(cit: {paper.citations})")

    return " ".join(parts)


def format_paper_list(
    papers: list[ListedPaper] | tuple[ListedPaper, ...],
    *,
    max_authors: int = 3,
    show_citations: bool = False,
) -> str:
    """Format many listed papers as terminal-friendly plain text."""

    if not papers:
        return "No papers matched the current search filters."

    return "\n".join(
        format_paper_listing(
            paper,
            max_authors=max_authors,
            show_citations=show_citations,
        )
        for paper in papers
    )


def save_paper_list(
    content: str,
    destination: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Persist formatted paper listings as a plain-text file."""

    if not content.strip():
        raise ValueError("Cannot save empty listing content.")

    output_path = Path(destination).expanduser()
    if output_path.suffix.lower() != ".txt":
        raise ValueError("Listing output must use the .txt extension.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing file: {output_path}")

    output_path.write_text(content.rstrip() + "\n", encoding="utf-8")
    return output_path


def _extract_metadata(hit: dict[str, Any]) -> dict[str, Any]:
    metadata = hit.get("metadata")
    if isinstance(metadata, dict):
        return metadata
    return hit


def _extract_title(metadata: dict[str, Any]) -> str:
    titles = metadata.get("titles")
    if isinstance(titles, list):
        for item in titles:
            if isinstance(item, dict):
                title = item.get("title")
                if isinstance(title, str) and title.strip():
                    return title.strip()

    title = metadata.get("title")
    if isinstance(title, str) and title.strip():
        return title.strip()

    return _UNTITLED_PAPER


def _extract_authors(metadata: dict[str, Any]) -> tuple[str, ...]:
    authors = metadata.get("authors")
    if not isinstance(authors, list):
        return ()

    normalized_authors: list[str] = []
    for item in authors:
        if not isinstance(item, dict):
            continue
        author_name = item.get("full_name") or item.get("name")
        if isinstance(author_name, str):
            stripped_name = author_name.strip()
            if stripped_name:
                normalized_authors.append(stripped_name)

    return tuple(normalized_authors)


def _extract_identifier(metadata: dict[str, Any]) -> str | None:
    arxiv_value = _extract_identifier_value(metadata.get("arxiv_eprints"))
    if arxiv_value is not None:
        return f"arXiv:{arxiv_value.removeprefix('arXiv:')}"

    doi_value = _extract_identifier_value(metadata.get("dois"))
    if doi_value is not None:
        return f"DOI:{doi_value}"

    doi_field = metadata.get("doi")
    if isinstance(doi_field, str) and doi_field.strip():
        return f"DOI:{doi_field.strip()}"

    return None


def _extract_identifier_value(raw_value: Any) -> str | None:
    if isinstance(raw_value, list):
        for item in raw_value:
            if isinstance(item, dict):
                value = item.get("value")
                if isinstance(value, str) and value.strip():
                    return value.strip()
            elif isinstance(item, str) and item.strip():
                return item.strip()

    if isinstance(raw_value, str) and raw_value.strip():
        return raw_value.strip()

    return None


def _extract_citations(metadata: dict[str, Any]) -> int | None:
    citation_count = metadata.get("citation_count")
    if isinstance(citation_count, int):
        return citation_count
    return None


def _format_authors(authors: tuple[str, ...], *, max_authors: int) -> str:
    if not authors:
        return _UNKNOWN_AUTHORS

    if len(authors) <= max_authors:
        return ", ".join(authors)

    displayed = ", ".join(authors[:max_authors])
    return f"{displayed}, et al."
