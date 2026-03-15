# PaperScout Docs

This document explains the structure of PaperScout in a more technical way than the main project README.

The project is intentionally small, but it is organized in layers so the command-line interface, Python API, and core search logic stay easy to evolve and test.

## Architecture At A Glance

PaperScout follows a simple flow:

1. raw user input enters from the CLI or Python API
2. validators normalize and validate that input
3. domain models hold the validated request state
4. the query builder translates filters into an INSPIRE query
5. the service layer prepares or executes the search
6. the INSPIRE client performs remote requests
7. the selector decides whether execution is safe
8. the exporter saves BibTeX to disk when requested

In practice, this gives the project a few useful properties:

- the query can be previewed before any network call
- validation happens early and consistently
- safety rules for large result sets are centralized
- CLI and Python usage share the same core logic

## Layer Breakdown

### 1. Entry Points

Files:

- [`paperscout/cli.py`](/Users/williamgiare/codes/GitHub/PaperScout/paperscout/cli.py)
- [`paperscout/api.py`](/Users/williamgiare/codes/GitHub/PaperScout/paperscout/api.py)

These modules are the public entry points.

`cli.py` exposes the installed commands:

- `paperscout-preview`
- `paperscout-estimate`
- `paperscout-save`
- `paperscout-validate`
- `paperscout-help`
- `paperscout-cite`

`api.py` exposes the notebook-friendly Python API:

- `preview(...)`
- `estimate(...)`
- `save(...)`

Both layers are intentionally thin. They translate external input into a validated request and then delegate the real work to the service layer.

### 2. Validation and Request Construction

Files:

- [`paperscout/validators.py`](/Users/williamgiare/codes/GitHub/PaperScout/paperscout/validators.py)
- [`paperscout/model.py`](/Users/williamgiare/codes/GitHub/PaperScout/paperscout/model.py)

This is where PaperScout becomes strict on purpose.

`validators.py` builds a complete `SearchRequest` from raw input and enforces rules such as:

- at least one primary filter must exist
- years must stay within supported bounds
- result limits and page sizes must be valid
- output paths must point to a `.bib` file

`model.py` contains the normalized domain objects:

- `SearchFilters`
- `DateRange`
- `OutputConfig`
- `SearchLimits`
- `SearchRequest`

These dataclasses help keep the rest of the codebase predictable. Once a request exists, downstream modules can assume it is already normalized.

### 3. Query Construction

File:

- [`paperscout/query_builder.py`](/Users/williamgiare/codes/GitHub/PaperScout/paperscout/query_builder.py)

`InspireQueryBuilder` translates the internal filter model into the actual INSPIRE query string.

Important details:

- keyword clauses search across title, abstract, and INSPIRE keywords
- repeated keywords are combined with logical `AND`
- repeated authors are combined with logical `AND`
- date filters are converted into inclusive boundaries
- accented and unaccented text variants are both queried when useful
- user literals are escaped conservatively

The output is a `BuiltQuery` object with both the final query string and its component clauses.

### 4. Service Layer

File:

- [`paperscout/service.py`](/Users/williamgiare/codes/GitHub/PaperScout/paperscout/service.py)

`PaperScoutService` is the orchestration layer.

Its main responsibilities are:

- prepare a search for preview
- run a preflight estimate
- choose whether a full execution is allowed
- fetch BibTeX only when the execution plan says it is safe

This is the module that connects the query builder, the INSPIRE client, and the selector into one coherent workflow.

Key result types:

- `PreparedSearch`
- `SearchEstimateResult`
- `SearchExecutionResult`

### 5. Execution Planning and Safety

File:

- [`paperscout/selector.py`](/Users/williamgiare/codes/GitHub/PaperScout/paperscout/selector.py)

The selector turns a preflight count into an `ExecutionPlan`.

This is where PaperScout decides whether a search should:

- return immediately because there are no results
- execute as a single page
- execute as a paginated download
- stop and require confirmation
- abort because the result set is too large

This separation matters because safety rules stay centralized instead of being duplicated in the CLI and Python API.

### 6. INSPIRE API Access

File:

- [`paperscout/inspire_client.py`](/Users/williamgiare/codes/GitHub/PaperScout/paperscout/inspire_client.py)

`InspireClient` is a small wrapper around the INSPIRE literature API built with the Python standard library.

It handles:

- previewable search URLs
- lightweight preflight requests
- JSON page fetching
- BibTeX page fetching
- retry behavior for transient failures

The client is deliberately narrow in scope so it stays easy to test and reason about.

### 7. Output Utilities

Files:

- [`paperscout/bibtex_exporter.py`](/Users/williamgiare/codes/GitHub/PaperScout/paperscout/bibtex_exporter.py)
- [`paperscout/cite.py`](/Users/williamgiare/codes/GitHub/PaperScout/paperscout/cite.py)

These modules sit at the edge of the workflow:

- `BibtexExporter` writes BibTeX to disk with overwrite protection
- `cite.py` reads a `.bib` file and generates a LaTeX `\cite{...}` command

## End-to-End Request Flow

For a command like:

```bash
paperscout-save --keyword inflation --author Starobinsky --from 2022 --output results.bib
```

the internal flow is:

1. `cli.py` parses the arguments
2. `validators.py` builds a validated `SearchRequest`
3. `service.py` asks `query_builder.py` to build the INSPIRE query
4. `service.py` asks `inspire_client.py` for a preflight count
5. `selector.py` converts that count into an execution plan
6. if the plan allows execution, `inspire_client.py` fetches the BibTeX pages
7. `bibtex_exporter.py` writes the final `.bib` file

That same architecture is reused by the Python API, which is why the CLI and notebook behavior stay aligned.

## Why This Structure Works Well

The current design gives the project a good balance between simplicity and safety:

- simple public interface
- explicit internal request model
- reusable service layer
- isolated network logic
- centralized execution safeguards
- small modules with focused responsibilities

For a tool like PaperScout, that structure is helpful because users want a fast workflow, but they also need confidence that the generated search and download behavior are understandable.

## Tests

The test suite lives in:

- [`tests/test_api.py`](/Users/williamgiare/codes/GitHub/PaperScout/tests/test_api.py)
- [`tests/test_cite.py`](/Users/williamgiare/codes/GitHub/PaperScout/tests/test_cite.py)
- [`tests/test_text_handling.py`](/Users/williamgiare/codes/GitHub/PaperScout/tests/test_text_handling.py)

The tests currently cover key API behavior, BibTeX citation handling, and text normalization behavior.

Run them with:

```bash
python3 -m unittest discover -s tests
```

## Suggested Reading Order

If you want to understand the project quickly, this order works well:

1. [`README.md`](/Users/williamgiare/codes/GitHub/PaperScout/README.md)
2. [`paperscout/api.py`](/Users/williamgiare/codes/GitHub/PaperScout/paperscout/api.py)
3. [`paperscout/service.py`](/Users/williamgiare/codes/GitHub/PaperScout/paperscout/service.py)
4. [`paperscout/query_builder.py`](/Users/williamgiare/codes/GitHub/PaperScout/paperscout/query_builder.py)
5. [`paperscout/inspire_client.py`](/Users/williamgiare/codes/GitHub/PaperScout/paperscout/inspire_client.py)
