"""HTTP client for the INSPIRE literature API.

This client intentionally uses the Python standard library only.
It focuses on a narrow, testable contract:
- perform a lightweight JSON preflight to read the total number of hits
- fetch JSON pages when metadata is needed
- fetch BibTeX pages for export
"""

from __future__ import annotations

from dataclasses import dataclass, field
from json import JSONDecodeError, loads
from time import sleep
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .query_builder import BuiltQuery
from .selector import PreflightSummary


DEFAULT_API_BASE_URL = "https://inspirehep.net/api/literature"
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_MAX_RETRIES = 4
DEFAULT_RETRY_BACKOFF_SECONDS = 1.0
DEFAULT_USER_AGENT = "PaperScout/0.1 (+https://inspirehep.net)"
_JSON_ACCEPT_HEADER = "application/json"
_BIBTEX_ACCEPT_HEADER = "application/x-bibtex"
_PREVIEW_PAGE_SIZE = 1


@dataclass(frozen=True, slots=True)
class InspireClientConfig:
    """Configuration for remote API access."""

    base_url: str = DEFAULT_API_BASE_URL
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    max_retries: int = DEFAULT_MAX_RETRIES
    retry_backoff_seconds: float = DEFAULT_RETRY_BACKOFF_SECONDS
    user_agent: str = DEFAULT_USER_AGENT

    def __post_init__(self) -> None:
        if not self.base_url.startswith("https://"):
            raise ValueError("base_url must use HTTPS.")

        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive.")

        if self.max_retries < 0:
            raise ValueError("max_retries cannot be negative.")

        if self.retry_backoff_seconds < 0:
            raise ValueError("retry_backoff_seconds cannot be negative.")

        if not self.user_agent.strip():
            raise ValueError("user_agent cannot be empty.")


@dataclass(frozen=True, slots=True)
class InspirePreflightResult:
    """Normalized result of a lightweight count query."""

    summary: PreflightSummary
    api_total: int

    def __post_init__(self) -> None:
        if self.api_total != self.summary.total_results:
            raise ValueError("api_total must match summary.total_results.")


@dataclass(frozen=True, slots=True)
class InspirePage:
    """Representation of a single JSON search page."""

    total_results: int
    page_number: int
    page_size: int
    raw_payload: dict[str, Any] = field(repr=False)

    def __post_init__(self) -> None:
        if self.total_results < 0:
            raise ValueError("total_results cannot be negative.")

        if self.page_number < 1:
            raise ValueError("page_number must be at least 1.")

        if self.page_size < 1:
            raise ValueError("page_size must be at least 1.")

    @property
    def hits(self) -> list[dict[str, Any]]:
        hits_section = self.raw_payload.get("hits", {})
        hits = hits_section.get("hits", [])
        if not isinstance(hits, list):
            raise ValueError("INSPIRE response contained a non-list hits.hits field.")
        return hits


class InspireClient:
    """Small, robust wrapper around the INSPIRE literature search API."""

    def __init__(self, config: InspireClientConfig | None = None) -> None:
        self._config = config or InspireClientConfig()

    @property
    def config(self) -> InspireClientConfig:
        return self._config

    def run_preflight(self, built_query: BuiltQuery) -> InspirePreflightResult:
        """Fetch the total number of records for a query with minimal payload."""

        payload = self.fetch_json_page(
            built_query,
            page=1,
            size=_PREVIEW_PAGE_SIZE,
            fields=("control_number",),
        )
        summary = PreflightSummary(total_results=payload.total_results)
        return InspirePreflightResult(summary=summary, api_total=payload.total_results)

    def fetch_json_page(
        self,
        built_query: BuiltQuery,
        *,
        page: int,
        size: int,
        fields: tuple[str, ...] = (),
        sort: str | None = "mostrecent",
    ) -> InspirePage:
        """Fetch a search page in JSON form."""

        if page < 1:
            raise ValueError("page must be at least 1.")

        if not 1 <= size <= 1_000:
            raise ValueError("size must be between 1 and 1000.")

        params = {
            "q": built_query.query,
            "page": page,
            "size": size,
        }
        if sort is not None:
            params["sort"] = sort
        if fields:
            params["fields"] = ",".join(fields)

        payload = self._request_json(params=params)
        total_results = self._extract_total_results(payload)
        return InspirePage(
            total_results=total_results,
            page_number=page,
            page_size=size,
            raw_payload=payload,
        )

    def fetch_bibtex_page(
        self,
        built_query: BuiltQuery,
        *,
        page: int,
        size: int,
        sort: str | None = "mostrecent",
    ) -> str:
        """Fetch a search page directly in BibTeX format."""

        if page < 1:
            raise ValueError("page must be at least 1.")

        if not 1 <= size <= 1_000:
            raise ValueError("size must be between 1 and 1000.")

        params = {
            "q": built_query.query,
            "page": page,
            "size": size,
            "format": "bibtex",
        }
        if sort is not None:
            params["sort"] = sort

        return self._request_text(params=params, accept_header=_BIBTEX_ACCEPT_HEADER)

    def fetch_all_bibtex(
        self,
        built_query: BuiltQuery,
        *,
        total_results: int,
        page_size: int,
        sort: str | None = "mostrecent",
    ) -> str:
        """Fetch and concatenate all BibTeX pages for a query."""

        if total_results < 0:
            raise ValueError("total_results cannot be negative.")

        if total_results == 0:
            return ""

        if not 1 <= page_size <= 1_000:
            raise ValueError("page_size must be between 1 and 1000.")

        chunks: list[str] = []
        remaining = total_results
        page = 1

        while remaining > 0:
            current_page_size = min(page_size, remaining)
            bibtex = self.fetch_bibtex_page(
                built_query,
                page=page,
                size=current_page_size,
                sort=sort,
            ).strip()
            if bibtex:
                chunks.append(bibtex)

            remaining -= current_page_size
            page += 1

        return "\n\n".join(chunks)

    def _request_json(self, *, params: dict[str, Any]) -> dict[str, Any]:
        text = self._request_text(params=params, accept_header=_JSON_ACCEPT_HEADER)
        try:
            payload = loads(text)
        except JSONDecodeError as exc:
            raise RuntimeError("INSPIRE returned invalid JSON.") from exc

        if not isinstance(payload, dict):
            raise RuntimeError("INSPIRE returned a non-object JSON payload.")

        return payload

    def _request_text(self, *, params: dict[str, Any], accept_header: str) -> str:
        url = self._build_url(params)
        headers = {
            "Accept": accept_header,
            "User-Agent": self._config.user_agent,
        }
        request = Request(url, headers=headers, method="GET")

        attempt = 0
        while True:
            try:
                with urlopen(request, timeout=self._config.timeout_seconds) as response:
                    charset = response.headers.get_content_charset() or "utf-8"
                    return response.read().decode(charset)
            except HTTPError as exc:
                if self._should_retry_http_error(exc.code, attempt):
                    self._sleep_before_retry(attempt, retry_after=exc.headers.get("Retry-After"))
                    attempt += 1
                    continue
                raise RuntimeError(
                    f"INSPIRE request failed with HTTP status {exc.code}."
                ) from exc
            except URLError as exc:
                if attempt < self._config.max_retries:
                    self._sleep_before_retry(attempt)
                    attempt += 1
                    continue
                raise RuntimeError("INSPIRE request failed due to a network error.") from exc

    def _build_url(self, params: dict[str, Any]) -> str:
        query_string = urlencode(params, doseq=True)
        return f"{self._config.base_url}?{query_string}"

    def build_search_url(
        self,
        built_query: BuiltQuery,
        *,
        page: int = 1,
        size: int = 25,
        sort: str | None = "mostrecent",
        format_name: str | None = None,
    ) -> str:
        """Build a fully qualified INSPIRE API URL for inspection or debugging."""

        if page < 1:
            raise ValueError("page must be at least 1.")

        if not 1 <= size <= 1_000:
            raise ValueError("size must be between 1 and 1000.")

        params: dict[str, Any] = {
            "q": built_query.query,
            "page": page,
            "size": size,
        }
        if sort is not None:
            params["sort"] = sort
        if format_name is not None:
            params["format"] = format_name

        return self._build_url(params)

    def _extract_total_results(self, payload: dict[str, Any]) -> int:
        hits_section = payload.get("hits")
        if not isinstance(hits_section, dict):
            raise RuntimeError("INSPIRE response is missing a valid hits section.")

        total = hits_section.get("total")
        if not isinstance(total, int):
            raise RuntimeError("INSPIRE response is missing an integer hits.total value.")

        return total

    def _should_retry_http_error(self, status_code: int, attempt: int) -> bool:
        retryable_statuses = {429, 500, 502, 503, 504}
        return status_code in retryable_statuses and attempt < self._config.max_retries

    def _sleep_before_retry(self, attempt: int, *, retry_after: str | None = None) -> None:
        if retry_after is not None:
            try:
                sleep(max(float(retry_after), 0.0))
                return
            except ValueError:
                pass

        sleep(self._config.retry_backoff_seconds * (2**attempt))
