"""Execution-plan selection for PaperScout searches.

This module decides how a validated search request should be executed
after a lightweight preflight count has been performed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from math import ceil

from .model import SearchRequest


class FetchStrategy(StrEnum):
    """Operational strategy selected for a search."""

    NO_RESULTS = "no_results"
    SINGLE_PAGE = "single_page"
    PAGINATED = "paginated"
    ABORTED = "aborted"


@dataclass(frozen=True, slots=True)
class PreflightSummary:
    """Summary returned by the initial count request."""

    total_results: int

    def __post_init__(self) -> None:
        if self.total_results < 0:
            raise ValueError("total_results cannot be negative.")


@dataclass(frozen=True, slots=True)
class ExecutionPlan:
    """Fully-resolved execution decision for a search request."""

    total_results: int
    expected_pages: int
    fetch_strategy: FetchStrategy
    should_abort: bool
    requires_confirmation: bool
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.total_results < 0:
            raise ValueError("total_results cannot be negative.")

        if self.expected_pages < 0:
            raise ValueError("expected_pages cannot be negative.")

        if self.should_abort and self.fetch_strategy is not FetchStrategy.ABORTED:
            raise ValueError(
                "Aborted plans must use FetchStrategy.ABORTED."
            )

        if not self.should_abort and self.fetch_strategy is FetchStrategy.ABORTED:
            raise ValueError(
                "FetchStrategy.ABORTED can only be used for aborted plans."
            )

        if self.total_results == 0 and self.expected_pages != 0:
            raise ValueError("expected_pages must be 0 when total_results is 0.")

        if self.total_results > 0 and self.expected_pages == 0 and not self.should_abort:
            raise ValueError(
                "expected_pages must be positive when results are present."
            )

        if any(not warning.strip() for warning in self.warnings):
            raise ValueError("warnings cannot contain empty messages.")

    @property
    def can_execute(self) -> bool:
        return (
            not self.should_abort
            and not self.requires_confirmation
            and self.total_results > 0
        )


class SearchSelector:
    """Deterministic planner for choosing the safest execution path."""

    def build_plan(
        self,
        request: SearchRequest,
        preflight: PreflightSummary,
        *,
        force: bool = False,
    ) -> ExecutionPlan:
        total_results = preflight.total_results
        limits = request.limits

        if total_results == 0:
            return ExecutionPlan(
                total_results=0,
                expected_pages=0,
                fetch_strategy=FetchStrategy.NO_RESULTS,
                should_abort=False,
                requires_confirmation=False,
                warnings=("No papers matched the current search filters.",),
            )

        expected_pages = ceil(total_results / limits.page_size)
        warnings: list[str] = []

        if total_results > limits.hard_result_limit and not force:
            warnings.append(
                (
                    "Search aborted because the preflight count exceeds the "
                    f"hard result limit ({limits.hard_result_limit}). "
                    "Refine the query or rerun with force enabled."
                )
            )
            return ExecutionPlan(
                total_results=total_results,
                expected_pages=expected_pages,
                fetch_strategy=FetchStrategy.ABORTED,
                should_abort=True,
                requires_confirmation=True,
                warnings=tuple(warnings),
            )

        requires_confirmation = False
        if total_results > limits.preflight_warning_threshold:
            warnings.append(
                (
                    "Large result set detected during preflight: "
                    f"{total_results} papers across approximately "
                    f"{expected_pages} page(s)."
                )
            )
            requires_confirmation = not force

        if total_results <= limits.page_size:
            fetch_strategy = FetchStrategy.SINGLE_PAGE
        else:
            fetch_strategy = FetchStrategy.PAGINATED

        return ExecutionPlan(
            total_results=total_results,
            expected_pages=expected_pages,
            fetch_strategy=fetch_strategy,
            should_abort=False,
            requires_confirmation=requires_confirmation,
            warnings=tuple(warnings),
        )
