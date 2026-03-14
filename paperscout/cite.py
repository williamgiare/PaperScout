"""Utilities for building LaTeX cite commands from BibTeX files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from re import IGNORECASE, MULTILINE, compile
from typing import Literal


SortMode = Literal["file", "alpha", "date"]

_ENTRY_START_PATTERN = compile(r"@(?P<type>[A-Za-z]+)\s*\{\s*(?P<key>[^,\s]+)\s*,")
_YEAR_PATTERN = compile(r"^\s*year\s*=\s*(?P<value>.+?)\s*,?\s*$", IGNORECASE | MULTILINE)
_MONTH_PATTERN = compile(r"^\s*month\s*=\s*(?P<value>.+?)\s*,?\s*$", IGNORECASE | MULTILINE)

_MONTH_LOOKUP = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


@dataclass(frozen=True, slots=True)
class BibEntry:
    """Minimal BibTeX entry representation needed for cite generation."""

    entry_type: str
    key: str
    raw_entry: str
    year: int | None
    month: int | None
    original_index: int


def cite(
    bib_path: str | Path,
    *,
    sort: SortMode = "file",
) -> str:
    """Build a `\\cite{...}` command from a BibTeX file."""

    entries = parse_bibtex_file(bib_path)
    sorted_entries = sort_bib_entries(entries, sort=sort)
    keys = [entry.key for entry in sorted_entries]
    if not keys:
        raise ValueError("No BibTeX entries were found in the input file.")
    return f"\\cite{{{','.join(keys)}}}"


def parse_bibtex_file(bib_path: str | Path) -> list[BibEntry]:
    """Parse a BibTeX file into minimal entry objects."""

    content = Path(bib_path).read_text(encoding="utf-8")
    return parse_bibtex_text(content)


def parse_bibtex_text(content: str) -> list[BibEntry]:
    """Parse BibTeX text into minimal entry objects."""

    entries: list[BibEntry] = []
    index = 0
    entry_counter = 0

    while True:
        match = _ENTRY_START_PATTERN.search(content, index)
        if match is None:
            break

        start = match.start()
        open_brace_index = content.find("{", start)
        if open_brace_index == -1:
            raise ValueError("Malformed BibTeX entry: missing opening brace.")

        end = _find_entry_end(content, open_brace_index)
        raw_entry = content[start : end + 1]
        entries.append(
            BibEntry(
                entry_type=match.group("type"),
                key=match.group("key").strip(),
                raw_entry=raw_entry,
                year=_extract_year(raw_entry),
                month=_extract_month(raw_entry),
                original_index=entry_counter,
            )
        )
        entry_counter += 1
        index = end + 1

    return entries


def sort_bib_entries(entries: list[BibEntry], *, sort: SortMode = "file") -> list[BibEntry]:
    """Return BibTeX entries sorted by the requested strategy."""

    if sort == "file":
        return sorted(entries, key=lambda entry: entry.original_index)

    if sort == "alpha":
        return sorted(entries, key=lambda entry: (entry.key.casefold(), entry.original_index))

    if sort == "date":
        return sorted(
            entries,
            key=lambda entry: (
                entry.year if entry.year is not None else 9999,
                entry.month if entry.month is not None else 99,
                entry.original_index,
            ),
        )

    raise ValueError("sort must be one of: 'file', 'alpha', 'date'.")


def _find_entry_end(content: str, open_brace_index: int) -> int:
    depth = 0
    in_quotes = False
    escaped = False

    for index in range(open_brace_index, len(content)):
        character = content[index]

        if escaped:
            escaped = False
            continue

        if character == "\\":
            escaped = True
            continue

        if character == '"':
            in_quotes = not in_quotes
            continue

        if in_quotes:
            continue

        if character == "{":
            depth += 1
            continue

        if character == "}":
            depth -= 1
            if depth == 0:
                return index

    raise ValueError("Malformed BibTeX entry: unmatched braces.")


def _extract_year(raw_entry: str) -> int | None:
    match = _YEAR_PATTERN.search(raw_entry)
    if match is None:
        return None

    digits = "".join(character for character in _strip_bib_value(match.group("value")) if character.isdigit())
    if len(digits) < 4:
        return None

    return int(digits[:4])


def _extract_month(raw_entry: str) -> int | None:
    match = _MONTH_PATTERN.search(raw_entry)
    if match is None:
        return None

    value = _strip_bib_value(match.group("value")).casefold()
    if value.isdigit():
        month_value = int(value)
        if 1 <= month_value <= 12:
            return month_value
        return None

    return _MONTH_LOOKUP.get(value)


def _strip_bib_value(value: str) -> str:
    stripped = value.strip().rstrip(",").strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped[1:-1].strip()
    if stripped.startswith('"') and stripped.endswith('"'):
        return stripped[1:-1].strip()
    return stripped
