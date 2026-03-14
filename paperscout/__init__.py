"""PaperScout package."""

from .api import SaveResult, estimate, preview, save
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
from .query_builder import BuiltQuery, InspireQueryBuilder
from .selector import ExecutionPlan, FetchStrategy, PreflightSummary, SearchSelector
from .service import (
    PreparedSearch,
    SearchEstimateResult,
    SearchExecutionResult,
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
    "OutputConfig",
    "SaveResult",
    "cite",
    "estimate",
    "parse_bibtex_file",
    "parse_bibtex_text",
    "PaperScoutService",
    "PreparedSearch",
    "PreflightSummary",
    "SearchEstimateResult",
    "SearchField",
    "SearchFilters",
    "SearchLimits",
    "SearchRequest",
    "SearchExecutionResult",
    "SearchSelector",
    "preview",
    "save",
]
