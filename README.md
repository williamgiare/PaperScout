# PaperScout

PaperScout is a small Python tool for querying the [INSPIRE](https://inspirehep.net/) literature database and working with results in BibTeX format.

It is designed around a simple workflow:

1. preview the exact INSPIRE query that would be used
2. estimate how many papers match
3. validate inputs locally
4. save matching results to a `.bib` file

The project is usable both from the command line and from Python or Jupyter notebooks.

## What It Can Do

PaperScout currently supports:

- keyword search across title, abstract, and INSPIRE keywords
- repeated `--keyword` filters with logical `AND`
- repeated `--author` filters with logical `AND`
- collaboration filtering
- inclusive year-based filtering with `--from` and `--to`
- minimum citation filtering with `--min-citations`
- BibTeX export to a configurable output file
- query preview before execution
- preflight result counting before download
- safer handling of accented text by querying both accented and unaccented variants when needed

## Installation

From the project root:

```bash
python3 -m pip install -e .
```

This installs the following commands:

- `paperscout-preview`
- `paperscout-estimate`
- `paperscout-save`
- `paperscout-validate`
- `paperscout-help`
- `paperscout-cite`

If you change the CLI or entry points, reinstall with:

```bash
python3 -m pip install -e .
```

## Command Overview

### `paperscout-preview`

Builds the exact INSPIRE query and prints:

- the normalized query string
- a preview API URL
- a preview BibTeX URL

It does not fetch results and does not write files.

Example:

```bash
paperscout-preview --keyword inflation --author Starobinsky --from 2022
```

### `paperscout-estimate`

Builds the query and asks INSPIRE only for the total number of matching records.

It prints:

- the normalized query
- the estimated number of matching papers
- the estimated number of pages at the current page size
- a preview API URL

It does not download BibTeX and does not write files.

Example:

```bash
paperscout-estimate --keyword inflation --author Starobinsky --from 2022
```

### `paperscout-validate`

Validates inputs locally and prints the normalized query that would be used.

It does not contact INSPIRE and does not write files.

Example:

```bash
paperscout-validate --collaboration Planck --min-citations 50
```

### `paperscout-save`

Builds the query, runs a preflight count, applies safety thresholds, downloads matching BibTeX, and saves it to disk.

This is the only command that requires `--output`.

Example:

```bash
paperscout-save \
  --keyword inflation \
  --keyword model \
  --author Starobinsky \
  --from 2022 \
  --output starobinsky_inflation.bib
```

### `paperscout-help`

Prints the integrated CLI help text with explanations of filters and examples.

```bash
paperscout-help
```

### `paperscout-cite`

Reads a BibTeX file and prints a ready-to-use LaTeX `\cite{...}` command.

Examples:

```bash
paperscout-cite results.bib
paperscout-cite results.bib --sort alpha
paperscout-cite results.bib --sort date
```

Supported sort modes:

- `file`: preserve the order found in the `.bib` file
- `alpha`: sort by BibTeX key
- `date`: sort by year and month, oldest first when available

## Filters and Semantics

### Keywords

Pass one keyword per `--keyword` flag:

```bash
--keyword inflation --keyword model
```

This means:

- `inflation` must be present
- `model` must be present

Each keyword is searched in:

- title
- abstract
- INSPIRE keywords

Multi-word keywords are supported:

```bash
--keyword "effective field theory"
```

### Authors

Pass one author per `--author` flag:

```bash
--author Starobinsky --author Guth
```

If multiple authors are given, all of them must be present in the paper.

PaperScout currently builds this as a logical `AND` between authors.

### Collaboration

You can filter by collaboration:

```bash
--collaboration Planck
```

If used together with keywords or authors, all filters must match.

### Time Range

The tool currently supports year-only time filters.

Examples:

```bash
--from 2022
--to 2024
--from 2022 --to 2024
```

Interpretation:

- `--from 2022` means from `2022-01-01` up to today
- `--to 2024` means from the earliest available records up to `2024-12-31`
- using both creates an inclusive range

### Minimum Citations

To keep only papers with at least a given number of citations:

```bash
--min-citations 10
```

## Required vs Optional Inputs

At least one primary filter is required:

- `--keyword`
- `--author`
- `--collaboration`

Optional filters:

- `--from`
- `--to`
- `--min-citations`

Required only for `paperscout-save`:

- `--output`

## Notes on Names, Accents, and Quotes

If a value contains spaces, quote it in the shell:

```bash
--author "William Giarè"
--keyword "effective field theory"
```

If a value is a single word, quotes are optional:

```bash
--author Giarè
--keyword inflation
```

PaperScout normalizes Unicode input and, when useful, builds both accented and unaccented text variants in the query. This improves robustness for names such as `Giarè` where INSPIRE indexing may behave differently across records.

## Safety Behavior

PaperScout uses a preflight count before downloading BibTeX.

Default limits:

- warning threshold: `1000`
- hard limit: `5000`
- page size: `250`

These can be adjusted from the CLI:

```bash
--warning-threshold 1000
--hard-limit 5000
--page-size 250
```

To proceed despite threshold warnings:

```bash
--force
```

## Examples

### Single keyword

```bash
paperscout-preview --keyword inflation
```

### Two required keywords

```bash
paperscout-estimate --keyword inflation --keyword model
```

### Author plus keyword plus year

```bash
paperscout-estimate --keyword inflation --author Starobinsky --from 2022
```

### Multiple authors

```bash
paperscout-preview --author Starobinsky --author Guth
```

### Collaboration plus citation threshold

```bash
paperscout-validate --collaboration Planck --min-citations 50
```

### Save results to BibTeX

```bash
paperscout-save \
  --keyword inflation \
  --author "William Giarè" \
  --from 2022 \
  --output papers.bib
```

## Python and Jupyter Usage

The project can also be used directly from Python:

```python
from paperscout.api import preview

prepared = preview(
    keywords=["inflation", "model"],
    author=["Starobinsky"],
    from_year=2022,
    min_citations=10,
)

print(prepared.human_query)
print(prepared.preview_api_url)
```

To estimate results:

```python
from paperscout.api import estimate

estimate_result = estimate(
    keywords=["inflation", "model"],
    author=["Starobinsky"],
    from_year=2022,
    min_citations=10,
)

print(estimate_result.execution_plan.total_results)
print(estimate_result.execution_plan.expected_pages)
```

To execute and save:

```python
from paperscout.api import save

save_result = save(
    output="output/starobinsky_inflation.bib",
    keywords=["inflation", "model"],
    author=["Starobinsky"],
    from_year=2022,
    min_citations=10,
)

print(save_result.saved_path)
```

### Building a LaTeX `\cite{...}` from a BibTeX file

PaperScout also includes an internal utility for turning a saved `.bib` file into a LaTeX citation command. This is the same logic used by `paperscout-cite`.

Example:

```python
from paperscout.cite import cite

print(cite("results.bib"))
print(cite("results.bib", sort="alpha"))
print(cite("results.bib", sort="date"))
```

Supported sort modes:

- `file`: preserve the order of the `.bib` file
- `alpha`: sort by BibTeX key
- `date`: sort by year and month, oldest first when available

For a complete interactive example, see [`examples/example.ipynb`](/Users/williamgiare/codes/dev/PaperScout/examples/example.ipynb).

## Project Structure

Main modules:

- [`paperscout/model.py`](/Users/williamgiare/codes/dev/PaperScout/paperscout/model.py): domain models and normalization
- [`paperscout/validators.py`](/Users/williamgiare/codes/dev/PaperScout/paperscout/validators.py): input validation and request builders
- [`paperscout/query_builder.py`](/Users/williamgiare/codes/dev/PaperScout/paperscout/query_builder.py): INSPIRE query construction
- [`paperscout/inspire_client.py`](/Users/williamgiare/codes/dev/PaperScout/paperscout/inspire_client.py): HTTP client and preflight/download logic
- [`paperscout/selector.py`](/Users/williamgiare/codes/dev/PaperScout/paperscout/selector.py): execution planning based on result size
- [`paperscout/service.py`](/Users/williamgiare/codes/dev/PaperScout/paperscout/service.py): orchestration layer
- [`paperscout/api.py`](/Users/williamgiare/codes/dev/PaperScout/paperscout/api.py): notebook-friendly high-level Python wrapper
- [`paperscout/cli.py`](/Users/williamgiare/codes/dev/PaperScout/paperscout/cli.py): command-line interface
- [`paperscout/bibtex_exporter.py`](/Users/williamgiare/codes/dev/PaperScout/paperscout/bibtex_exporter.py): BibTeX persistence
- [`paperscout/cite.py`](/Users/williamgiare/codes/dev/PaperScout/paperscout/cite.py): build LaTeX `\cite{...}` commands from BibTeX files

## Current Limitations

- time filters are year-based only
- author matching still depends on INSPIRE’s indexing behavior
- no dedicated author-identifier mode yet
- no JSON export yet
- no full CLI test suite yet

## Development

Run the current tests with:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

## License and Data Source Notes

PaperScout queries the INSPIRE literature service. If you use it heavily or build on top of it, follow INSPIRE’s usage policies and avoid abusive request patterns.
