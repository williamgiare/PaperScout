"""INSPIRE query construction for PaperScout.

The builder in this module is deliberately conservative:
- every user-supplied textual term is quoted and escaped
- each logical clause is constructed independently
- date filtering uses ``de`` (date first appeared) to avoid the broader,
  more ambiguous ``date`` field
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from unicodedata import combining, normalize

from .model import SearchField, SearchFilters


_FIELD_ALIASES: dict[SearchField, str] = {
    SearchField.TITLE: "t",
    SearchField.ABSTRACT: "abstracts.value",
    SearchField.KEYWORDS: "k",
}

_MAX_CITATION_SENTINEL = 999_999_999


@dataclass(frozen=True, slots=True)
class BuiltQuery:
    """Fully assembled INSPIRE query plus its component clauses."""

    query: str
    clauses: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.query.strip():
            raise ValueError("Built query cannot be empty.")

        if not self.clauses:
            raise ValueError("Built query must include at least one clause.")

        if any(not clause.strip() for clause in self.clauses):
            raise ValueError("Built query clauses cannot contain empty values.")


class InspireQueryBuilder:
    """Translate normalized search filters into an INSPIRE search query."""

    def build(self, filters: SearchFilters) -> BuiltQuery:
        clauses: list[str] = []

        keyword_clause = self._build_keywords_clause(filters)
        if keyword_clause is not None:
            clauses.append(keyword_clause)

        authors_clause = self._build_authors_clause(filters)
        if authors_clause is not None:
            clauses.append(authors_clause)

        collaboration_clause = self._build_collaboration_clause(filters)
        if collaboration_clause is not None:
            clauses.append(collaboration_clause)

        citation_clause = self._build_min_citations_clause(filters)
        if citation_clause is not None:
            clauses.append(citation_clause)

        date_clauses = self._build_date_clauses(filters)
        clauses.extend(date_clauses)

        if not clauses:
            raise ValueError(
                "Cannot build an INSPIRE query without at least one effective clause."
            )

        return BuiltQuery(
            query=self._join_clauses(clauses, operator="and"),
            clauses=tuple(clauses),
        )

    def _build_keywords_clause(self, filters: SearchFilters) -> str | None:
        if not filters.keywords:
            return None

        per_keyword_clauses = [
            self._build_single_keyword_clause(keyword, filters.search_fields)
            for keyword in filters.keywords
        ]
        operator = "and" if filters.require_all_keywords else "or"
        return self._join_clauses(per_keyword_clauses, operator=operator)

    def _build_single_keyword_clause(
        self,
        keyword: str,
        search_fields: tuple[SearchField, ...],
    ) -> str:
        field_clauses = [
            self._build_text_field_clause(search_field, keyword)
            for search_field in search_fields
        ]
        return self._join_clauses(field_clauses, operator="or")

    def _build_text_field_clause(self, search_field: SearchField, value: str) -> str:
        field_name = _FIELD_ALIASES[search_field]
        variants = [
            f'{field_name}:"{self._escape_literal(variant)}"'
            for variant in self._literal_variants(value)
        ]
        return self._join_clauses(variants, operator="or")

    def _build_authors_clause(self, filters: SearchFilters) -> str | None:
        if not filters.authors:
            return None
        author_clauses = [
            self._join_clauses(
                [
                    f'a:"{self._escape_literal(variant)}"'
                    for variant in self._literal_variants(author)
                ],
                operator="or",
            )
            for author in filters.authors
        ]
        return self._join_clauses(author_clauses, operator="and")

    def _build_collaboration_clause(self, filters: SearchFilters) -> str | None:
        if filters.collaboration is None:
            return None
        collaboration_clauses = [
            f'cn:"{self._escape_literal(variant)}"'
            for variant in self._literal_variants(filters.collaboration)
        ]
        return self._join_clauses(collaboration_clauses, operator="or")

    def _build_min_citations_clause(self, filters: SearchFilters) -> str | None:
        if filters.min_citations is None or filters.min_citations == 0:
            return None

        return f"topcite:{filters.min_citations}->{_MAX_CITATION_SENTINEL}"

    def _build_date_clauses(self, filters: SearchFilters) -> tuple[str, ...]:
        date_range = filters.date_range
        if date_range.is_unbounded:
            return ()

        clauses: list[str] = []
        if date_range.start is not None:
            clauses.append(self._build_date_comparison(">=", date_range.start))

        if date_range.end is not None:
            clauses.append(self._build_date_comparison("<=", date_range.end))

        return tuple(clauses)

    def _build_date_comparison(self, operator: str, value: date) -> str:
        return f"de {operator} {value.isoformat()}"

    def _join_clauses(self, clauses: list[str], *, operator: str) -> str:
        filtered_clauses = [clause.strip() for clause in clauses if clause.strip()]
        if not filtered_clauses:
            raise ValueError("Cannot join an empty clause list.")

        if len(filtered_clauses) == 1:
            return filtered_clauses[0]

        normalized_operator = operator.strip().lower()
        if normalized_operator not in {"and", "or"}:
            raise ValueError("operator must be 'and' or 'or'.")

        separator = f" {normalized_operator} "
        return f"({separator.join(filtered_clauses)})"

    def _escape_literal(self, value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')

    def _literal_variants(self, value: str) -> tuple[str, ...]:
        original = value
        stripped = "".join(
            character
            for character in normalize("NFKD", value)
            if not combining(character)
        )

        variants = [original]
        if stripped != original:
            variants.append(stripped)

        return tuple(dict.fromkeys(variants))
