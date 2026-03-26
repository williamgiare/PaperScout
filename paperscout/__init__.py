"""PaperScout package."""

from .api import ListResult, SaveResult, estimate, list_papers, preview, save
from .model import (
    DateRange,
    OutputConfig,
    SearchField,
    SearchFilters,
    SearchLimits,
    SearchRequest,
)
from .cite import BibEntry, cite, parse_bibtex_file, parse_bibtex_text
from .bibtex_exporter import BibtexExporter
from .inspire_client import (
    InspireClient,
    InspireClientConfig,
    InspirePage,
    InspirePreflightResult,
)
from .listing import ListedPaper, format_paper_list, format_paper_listing, save_paper_list
from .query_builder import BuiltQuery, InspireQueryBuilder
from .selector import ExecutionPlan, FetchStrategy, PreflightSummary, SearchSelector
from .service import (
    PreparedSearch,
    SearchEstimateResult,
    SearchExecutionResult,
    SearchListResult,
    PaperScoutService,
)

__all__ = [
    "BibtexExporter",
    "BibEntry",
    "BuiltQuery",
    "DateRange",
    "ExecutionPlan",
    "FetchStrategy",
    "InspireClient",
    "InspireClientConfig",
    "InspirePage",
    "InspirePreflightResult",
    "InspireQueryBuilder",
    "ListedPaper",
    "ListResult",
    "OutputConfig",
    "SaveResult",
    "cite",
    "estimate",
    "format_paper_list",
    "format_paper_listing",
    "list_papers",
    "parse_bibtex_file",
    "parse_bibtex_text",
    "PaperScoutService",
    "PreparedSearch",
    "PreflightSummary",
    "SearchEstimateResult",
    "SearchField",
    "SearchFilters",
    "SearchListResult",
    "SearchLimits",
    "SearchRequest",
    "SearchExecutionResult",
    "SearchSelector",
    "preview",
    "save_paper_list",
    "save",
]
