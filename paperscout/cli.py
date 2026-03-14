"""Command-line interface for PaperScout."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .bibtex_exporter import BibtexExporter
from .cite import cite
from .service import PaperScoutService
from .validators import build_search_request


_DEFAULT_NON_PERSISTENT_OUTPUT = Path("paperscout.bib")


_DETAILED_HELP = """PaperScout commands

Available actions:
- paperscout-preview
  Build the INSPIRE query and show the exact query string plus preview URLs.
  No network preflight is executed and no file is written.

- paperscout-estimate
  Build the query and ask INSPIRE only for the total number of matching papers.
  No BibTeX is downloaded and no file is written.

- paperscout-save
  Build the query, run the INSPIRE preflight, enforce safety thresholds, then
  download and save the BibTeX output if the search is allowed to proceed.

- paperscout-validate
  Validate CLI inputs locally and show the normalized query that would be used.
  No network requests are made and no file is written.

- paperscout-cite
  Read a `.bib` file and print a LaTeX `\\cite{...}` command.
  This does not contact INSPIRE and does not write files.

Inputs:
- --keyword
  One search keyword or phrase.
  Pass it by repeating the flag once per keyword.
  Example: --keyword inflation --keyword model

- --author
  One author name to match in INSPIRE.
  Pass it by repeating the flag once per required author.
  Example: --author Linde --author Starobinsky

- --collaboration
  Collaboration name to match in INSPIRE.
  Example: --collaboration Planck

- --from
  Inclusive starting year for the search range.
  Example: --from 2022

- --to
  Inclusive ending year for the search range.
  Example: --to 2024

- --min-citations
  Minimum number of citations required for matching papers.
  Example: --min-citations 10

- --output
  Destination BibTeX filename.
  Example: --output results.bib

Shell note:
- If a value contains spaces or shell-special characters, wrap it in quotes.
- Examples: --author "William Giarè" and --keyword "effective field theory"

How filters are interpreted:
- At least one primary filter is required: --keyword, --author, or --collaboration
- --from and --to are optional
- --min-citations is optional
- --output is required only for paperscout-save

Keyword behavior:
- Repeat --keyword once per required keyword.
- Example: --keyword inflation --keyword model
- This means both keywords are required.
- Each keyword is searched in title, abstract, or INSPIRE keywords.
- Multi-word keywords are allowed: --keyword "effective field theory"
- Do not separate multiple keywords with commas inside one flag unless you
  really want the comma to be part of the same keyword text.

Author behavior:
- --author can be used alone, or together with keywords and other filters.
- Repeat --author once per required author.
- Example: --author Linde --author Starobinsky
- If multiple authors are given, the paper must contain all of them.
- If used with keywords, the search keeps only papers matching all required
  authors and the keywords.

Collaboration behavior:
- --collaboration can be used alone, or together with keywords and other filters.
- Example: --collaboration Planck
- If used with keywords, the search keeps only papers matching both the
  collaboration and the keywords.

Time range behavior:
- --from alone means from January 1 of that year up to today.
- --to alone means from the earliest available records up to December 31
  of that year.
- Using both creates an inclusive year range.

Citation behavior:
- --min-citations keeps only papers with at least that many citations.
- Example: --min-citations 50

Typical examples:
- paperscout-preview --keyword inflation
- paperscout-estimate --keyword inflation --author Starobinsky --from 2022
- paperscout-save --keyword inflation --keyword model --author Starobinsky --from 2022 --output starobinsky.bib
- paperscout-validate --collaboration Planck --min-citations 50
- paperscout-cite linde.bib
"""


def build_parser(
    program_name: str,
    *,
    require_output: bool,
    include_force: bool,
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=program_name,
        description="Search INSPIRE and preview or export BibTeX results.",
    )
    parser.add_argument(
        "--keyword",
        action="append",
        default=[],
        help="Keyword to require in the search. Repeat the flag for multiple keywords.",
    )
    parser.add_argument(
        "--author",
        action="append",
        default=[],
        help="Filter by author name.",
    )
    parser.add_argument(
        "--collaboration",
        help="Filter by collaboration name.",
    )
    parser.add_argument(
        "--from",
        dest="from_year",
        type=int,
        help="Inclusive starting year for the search range.",
    )
    parser.add_argument(
        "--to",
        dest="to_year",
        type=int,
        help="Inclusive ending year for the search range.",
    )
    parser.add_argument(
        "--min-citations",
        type=int,
        help="Minimum number of citations required.",
    )
    parser.add_argument(
        "--output",
        required=require_output,
        help="Destination .bib file.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite the output file if it already exists.",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=250,
        help="INSPIRE API page size (1-1000).",
    )
    parser.add_argument(
        "--warning-threshold",
        type=int,
        default=1_000,
        help="Warn when the preflight count exceeds this threshold.",
    )
    parser.add_argument(
        "--hard-limit",
        type=int,
        default=5_000,
        help="Abort by default when the preflight count exceeds this threshold.",
    )
    if include_force:
        parser.add_argument(
            "--force",
            action="store_true",
            help="Proceed despite warning and hard-limit safeguards.",
        )
    return parser


def main_preview(argv: list[str] | None = None) -> int:
    args = build_parser(
        "paperscout-preview",
        require_output=False,
        include_force=False,
    ).parse_args(argv)
    request = _build_request_from_args(args, require_output=False)
    service = PaperScoutService()
    prepared = service.prepare_search(request)

    print("Query:")
    print(prepared.human_query)
    print()
    print("Preview API URL:")
    print(prepared.preview_api_url)
    print()
    print("Preview BibTeX URL:")
    print(prepared.preview_bibtex_url)

    return 0


def main_estimate(argv: list[str] | None = None) -> int:
    args = build_parser(
        "paperscout-estimate",
        require_output=False,
        include_force=False,
    ).parse_args(argv)
    request = _build_request_from_args(args, require_output=False)
    service = PaperScoutService()

    prepared = service.prepare_search(request)
    print("Query:")
    print(prepared.human_query)
    print()

    preflight = service.inspire_client.run_preflight(prepared.built_query)
    page_size = request.limits.page_size
    estimated_pages = (
        0
        if preflight.summary.total_results == 0
        else (preflight.summary.total_results + page_size - 1) // page_size
    )

    print(f"Estimated matching papers: {preflight.summary.total_results}")
    print(f"Estimated pages at page size {page_size}: {estimated_pages}")
    print()
    print("Preview API URL:")
    print(prepared.preview_api_url)
    return 0


def main_save(argv: list[str] | None = None) -> int:
    args = build_parser(
        "paperscout-save",
        require_output=True,
        include_force=True,
    ).parse_args(argv)
    request = _build_request_from_args(args, require_output=True)
    service = PaperScoutService()
    exporter = BibtexExporter()

    prepared = service.prepare_search(request)
    print("Query:")
    print(prepared.human_query)
    print()
    print("Preview API URL:")
    print(prepared.preview_api_url)
    print()

    result = service.execute_search(request, force=args.force)

    if result.warnings:
        print("Warnings:")
        for warning in result.warnings:
            print(f"- {warning}")
        print()

    if result.execution_plan.should_abort:
        print("Search aborted before fetching results.")
        return 2

    if result.execution_plan.requires_confirmation:
        print("Search requires confirmation. Rerun with --force to continue.")
        return 2

    if result.execution_plan.total_results == 0:
        print("No papers matched the current search filters.")
        return 0

    output_path = exporter.save(result.bibtex_content, request.output)
    print(
        f"Saved {result.execution_plan.total_results} paper(s) to {output_path}"
    )
    return 0


def main_validate(argv: list[str] | None = None) -> int:
    args = build_parser(
        "paperscout-validate",
        require_output=False,
        include_force=False,
    ).parse_args(argv)
    request = _build_request_from_args(args, require_output=False)
    service = PaperScoutService()
    prepared = service.prepare_search(request)

    print("Input validation successful.")
    print()
    print("Normalized query:")
    print(prepared.human_query)
    return 0


def main_help(argv: list[str] | None = None) -> int:
    if argv:
        parser = build_parser(
            "paperscout-help",
            require_output=False,
            include_force=False,
        )
        parser.parse_args(argv)
    print(_DETAILED_HELP.rstrip())
    return 0


def main_cite(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="paperscout-cite",
        description="Build a LaTeX cite command from a BibTeX file.",
    )
    parser.add_argument(
        "input",
        help="Input .bib file.",
    )
    parser.add_argument(
        "--sort",
        choices=("file", "alpha", "date"),
        default="file",
        help="Ordering strategy for BibTeX keys.",
    )
    args = parser.parse_args(argv)

    print(cite(args.input, sort=args.sort))
    return 0


def main(argv: list[str] | None = None) -> int:
    print(_DETAILED_HELP.rstrip())
    return 0


def _build_request_from_args(
    args: argparse.Namespace,
    *,
    require_output: bool,
):
    destination = Path(args.output) if require_output else _DEFAULT_NON_PERSISTENT_OUTPUT
    return build_search_request(
        destination=destination,
        keywords=args.keyword,
        author=args.author,
        collaboration=args.collaboration,
        min_citations=args.min_citations,
        from_year=args.from_year,
        to_year=args.to_year,
        overwrite=args.overwrite,
        page_size=args.page_size,
        preflight_warning_threshold=args.warning_threshold,
        hard_result_limit=args.hard_limit,
    )


if __name__ == "__main__":
    sys.exit(main())
