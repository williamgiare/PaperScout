# PaperScout

PaperScout is a Python tool that helps you search the [INSPIRE](https://inspirehep.net/) literature database and save the results as BibTeX.

You can:
1. build the exact INSPIRE query
2. preview or estimate the result set
3. save the matching papers to a `.bib` file

It works from the command line, from Python, and inside notebooks, but the workflow stays the same and is meant to feel lightweight.


## Quick Start

Install from the project root:

```bash
python3 -m pip install -e .
```

Then try a search:

```bash
paperscout-preview --keyword inflation --author Starobinsky --from 2022
```

Estimate the size before downloading:

```bash
paperscout-estimate --keyword inflation --author Starobinsky --from 2022
```

Save the results to BibTeX:

```bash
paperscout-save \
  --keyword inflation \
  --author Starobinsky \
  --from 2022 \
  --output results.bib
```

## Main Commands

- `paperscout-preview`: build the query and show the preview URLs
- `paperscout-estimate`: ask INSPIRE how many papers match
- `paperscout-save`: download and save matching BibTeX entries
- `paperscout-validate`: validate inputs locally without contacting INSPIRE
- `paperscout-help`: print the built-in help text
- `paperscout-cite`: turn a `.bib` file into a LaTeX `\cite{...}` command

## Common Filters

PaperScout supports:

- repeated `--keyword` filters
- repeated `--author` filters
- `--collaboration`
- `--from` and `--to` year filters
- `--min-citations`

At least one primary filter is required:

- `--keyword`
- `--author`
- `--collaboration`

### How The Main Flags Work

- `--keyword`: search a term or phrase across title, abstract, and INSPIRE keywords
- repeated `--keyword`: combined with logical `AND`, so all given keywords must match
- `--author`: require a specific author in the paper metadata
- repeated `--author`: combined with logical `AND`, so all given authors must be present
- `--collaboration`: require a specific collaboration name
- `--from`: set the inclusive starting year
- `--to`: set the inclusive ending year
- `--from` with `--to`: build an inclusive year range

Example:

```bash
paperscout-preview \
  --keyword CMB \
  --keyword Spectra \
  --author White \ 
  --collaboration Planck \
  --from 2013 \
  --to 2025
```

This means: find papers that match both keywords, include the given author, match the collaboration, and fall inside the selected year range.

## Python API

The same workflow is available in Python:

```python
from paperscout.api import preview, estimate, save

prepared = preview(keywords=["inflation"], author=["Starobinsky"], from_year=2022)
result = estimate(keywords=["inflation"], author=["Starobinsky"], from_year=2022)
saved = save(
    output="results.bib",
    keywords=["inflation"],
    author=["Starobinsky"],
    from_year=2022,
)
``` 

## Project Docs

- If you want the technical overview, internal architecture, and module breakdown, see [`docs/README.md`](/Users/williamgiare/codes/GitHub/PaperScout/docs/README.md). That document also explains the filter semantics in more detail.

- For additional information see [`examples/example.ipynb`](/Users/williamgiare/codes/GitHub/PaperScout/examples/example.ipynb)

## Development

Project layout:

- `paperscout/`: package source
- `tests/`: test suite
- `examples/`: notebook and sample output
- `docs/`: structured project documentation

## Tests

Run tests with:

```bash
python3 -m unittest discover -s tests
```
