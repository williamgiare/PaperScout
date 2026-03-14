"""Application service layer for PaperScout."""

from __future__ import annotations

from dataclasses import dataclass, field

from .inspire_client import InspireClient
from .model import SearchRequest
from .query_builder import BuiltQuery, InspireQueryBuilder
from .selector import ExecutionPlan, SearchSelector


@dataclass(frozen=True, slots=True)
class PreparedSearch:
    """Previewable search state before any remote execution occurs."""

    request: SearchRequest
    built_query: BuiltQuery
    preview_api_url: str
    preview_bibtex_url: str
    human_query: str

    def __post_init__(self) -> None:
        if not self.preview_api_url.strip():
            raise ValueError("preview_api_url cannot be empty.")

        if not self.preview_bibtex_url.strip():
            raise ValueError("preview_bibtex_url cannot be empty.")

        if not self.human_query.strip():
            raise ValueError("human_query cannot be empty.")


@dataclass(frozen=True, slots=True)
class SearchExecutionResult:
    """Full execution result including preview, plan and optional BibTeX."""

    prepared_search: PreparedSearch
    execution_plan: ExecutionPlan
    bibtex_content: str = ""
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.execution_plan.can_execute and not self.execution_plan.should_abort:
            if self.execution_plan.total_results > 0 and not self.bibtex_content.strip():
                raise ValueError(
                    "bibtex_content cannot be empty for an executable plan with results."
                )


@dataclass(frozen=True, slots=True)
class SearchEstimateResult:
    """Preflight-only result for interactive estimate workflows."""

    prepared_search: PreparedSearch
    execution_plan: ExecutionPlan
    warnings: tuple[str, ...] = field(default_factory=tuple)


class PaperScoutService:
    """High-level orchestrator for query preview and search execution."""

    def __init__(
        self,
        *,
        query_builder: InspireQueryBuilder | None = None,
        inspire_client: InspireClient | None = None,
        selector: SearchSelector | None = None,
    ) -> None:
        self._query_builder = query_builder or InspireQueryBuilder()
        self._inspire_client = inspire_client or InspireClient()
        self._selector = selector or SearchSelector()

    @property
    def inspire_client(self) -> InspireClient:
        return self._inspire_client

    def prepare_search(self, request: SearchRequest) -> PreparedSearch:
        """Build and expose the exact query that would be sent to INSPIRE."""

        built_query = self._query_builder.build(request.filters)
        preview_api_url = self._inspire_client.build_search_url(
            built_query,
            page=1,
            size=min(request.limits.page_size, 25),
            sort="mostrecent",
        )
        preview_bibtex_url = self._inspire_client.build_search_url(
            built_query,
            page=1,
            size=min(request.limits.page_size, 25),
            sort="mostrecent",
            format_name="bibtex",
        )

        return PreparedSearch(
            request=request,
            built_query=built_query,
            preview_api_url=preview_api_url,
            preview_bibtex_url=preview_bibtex_url,
            human_query=built_query.query,
        )

    def execute_search(
        self,
        request: SearchRequest,
        *,
        force: bool = False,
        ) -> SearchExecutionResult:
        """Run preflight, select an execution plan and fetch BibTeX if allowed."""

        estimate_result = self.estimate_search(request, force=force)
        prepared_search = estimate_result.prepared_search
        execution_plan = estimate_result.execution_plan
        warnings = estimate_result.warnings
        if not execution_plan.can_execute or execution_plan.requires_confirmation:
            return SearchExecutionResult(
                prepared_search=prepared_search,
                execution_plan=execution_plan,
                bibtex_content="",
                warnings=warnings,
            )

        bibtex_content = self._inspire_client.fetch_all_bibtex(
            prepared_search.built_query,
            total_results=execution_plan.total_results,
            page_size=request.limits.page_size,
            sort="mostrecent",
        )

        return SearchExecutionResult(
            prepared_search=prepared_search,
            execution_plan=execution_plan,
            bibtex_content=bibtex_content,
            warnings=warnings,
        )

    def estimate_search(
        self,
        request: SearchRequest,
        *,
        force: bool = False,
    ) -> SearchEstimateResult:
        """Run preflight and return the execution plan without fetching BibTeX."""

        prepared_search = self.prepare_search(request)
        preflight = self._inspire_client.run_preflight(prepared_search.built_query)
        execution_plan = self._selector.build_plan(
            request,
            preflight.summary,
            force=force,
        )
        warnings = tuple(execution_plan.warnings)
        return SearchEstimateResult(
            prepared_search=prepared_search,
            execution_plan=execution_plan,
            warnings=warnings,
        )
