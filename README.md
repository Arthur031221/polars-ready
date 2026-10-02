<h1 align="center">
  <img src="assets/logo.svg" width="72" alt=""><br>
  polars-ready
</h1>

<p align="center">
  <strong>See which Pandas calls need review before you move a Python pipeline to Polars.</strong>
</p>

<p align="center">
  <a href="https://github.com/Arthur031221/polars-ready/stargazers"><img src="https://img.shields.io/github/stars/Arthur031221/polars-ready?style=social" alt="GitHub stars"></a>
  <a href="https://github.com/Arthur031221/polars-ready/actions"><img src="https://github.com/Arthur031221/polars-ready/actions/workflows/test.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/Arthur031221/polars-ready" alt="License"></a>
</p>

<p align="center">
  <a href="#quickstart">⚡ Quickstart</a> •
  <a href="#how-it-works">🔍 How it works</a> •
  <a href="#examples">📖 Examples</a> •
  <a href="#faq">💬 FAQ</a>
</p>

> [!TIP]
> Try a scan without adding a dependency to your project:
> ```sh
> uvx --from git+https://github.com/Arthur031221/polars-ready polars-ready examples/sales_pipeline.py
> ```

<p align="center">
  <img src="assets/demo.gif" alt="A terminal audit of examples/sales_pipeline.py showing direct, rewrite, and blocker findings." width="100%">
</p>

## Why polars-ready

Pandas pipelines can depend on implicit indexes, null behavior, expressions, and row order. Replacing imports without finding those dependencies can change output.

polars-ready reads Python syntax trees and never imports or runs the target code. It reports where a recognized call appears, its rule ID and confidence, and a Polars suggestion so you can review the migration before changing the pipeline.

## Features

- 🔎 **Finds common migration work:** covers Pandas constructors and I/O, grouping, sorting, missing data, reshaping, index use, row callbacks, categorical access, and timezone methods.
- 📍 **Shows each match:** reports its source location, rule ID, confidence, severity, and suggested Polars idiom.
- 📂 **Scans source and notebooks:** accepts Python files, Jupyter notebooks, and directories containing them.
- 🧭 **Follows common aliases:** tracks Pandas import aliases and local names assigned from recognized constructors or calls.
- 🔒 **Leaves target code untouched:** parses source without importing or executing the audited project.
- 📊 **Provides a review score:** shows the share of recognized calls classified as direct patterns, not a prediction of equivalent results or migration time.

## Quickstart

Run the included source fixture with the isolated command from the tip box:

```sh
uvx --from git+https://github.com/Arthur031221/polars-ready polars-ready examples/sales_pipeline.py
```

For a persistent installation, use:

```sh
pip install git+https://github.com/Arthur031221/polars-ready
```

Selected output from the fixture:

```text
36% direct patterns
4 direct    3 rewrite    4 blocker
1 files scanned
BLOCKER examples/sales_pipeline.py:12  resample
          frame.group_by_dynamic(index_column=timestamp, every=interval)
BLOCKER examples/sales_pipeline.py:12  set_index
          Keep keys as named columns
```

The score is the share of recognized calls classified as direct. It does not predict whether a migration will preserve results or save time.

## Examples

### A small sales pipeline

The scanner works on source text; it does not need a `sales.csv` file to inspect this example:

```python
import pandas as pd
sales = pd.read_csv("sales.csv")
sales = sales.dropna(subset=["amount"])
monthly = sales.set_index("date").resample("M").sum()
monthly.to_csv("monthly.csv")
```

Scanning this source reports 40% direct patterns, with 2 direct calls, 1 rewrite, and 2 blockers. The output includes these blocker findings:

```text
40% direct patterns
2 direct    1 rewrite    2 blocker
1 files scanned
  BLOCKER  monthly_sales.py:4  resample
          frame.group_by_dynamic(index_column=timestamp, every=interval)
  BLOCKER  monthly_sales.py:4  set_index
          Keep keys as named columns
```

### A notebook report

Write the JSON report to a file for a notebook audit:

```sh
polars-ready analysis.ipynb --json > audit.json
```

For a notebook with one `pd.read_csv` call, the report summary is:

```json
{
  "version": 1,
  "files_scanned": 1,
  "counts": {"direct": 1, "rewrite": 0, "blocker": 0},
  "errors": []
}
```

## How it works

The scanner parses `.py` files and notebook code cells into Python syntax trees, then checks calls against the rule catalog. It follows common Pandas import aliases and local variables assigned from recognized constructors or calls. Each match is classified as direct, rewrite, or blocker and includes a conservative Polars hint.

## FAQ

<details>
<summary><b>What does the direct percentage mean?</b></summary>

It is the share of recognized calls classified as direct patterns. It is not a prediction that the migration will preserve results or save time.

</details>

<details>
<summary><b>What does the scanner recognize, and what can it miss?</b></summary>

The first release recognizes common Pandas constructors and I/O, group operations, sorting, missing data, reshaping, index use, row callbacks, categorical access, and timezone methods. [The rule catalog](src/polars_ready/rules.py) lists every supported ID and its hint.

The scanner can miss dynamically imported Pandas, values passed across function boundaries, and aliases hidden in containers. It can report an unrelated method on a variable whose name is reused. Notebook code cells that start with a shell or IPython magic are skipped; other syntax errors are reported.

</details>

<details>
<summary><b>Which paths and output options are available?</b></summary>

Scan a source directory, write a notebook audit as JSON, or return a blocker status for a directory:

```sh
polars-ready path/to/source-directory
polars-ready analysis.ipynb --json > audit.json
polars-ready path/to/source-directory --fail-on-blocker
```

`--fail-on-blocker` exits with status 2 when a blocker is found. Parse errors exit with status 1. JSON output includes a version field for CI consumers.

</details>

<details>
<summary><b>How do I work on the project?</b></summary>

```sh
python -m pip install -e .
python -m unittest discover -s tests -v
```

Run `polars-ready examples/sales_pipeline.py` after changing report formatting. The fixture is source text for scanning and does not need a `sales.csv` file. Keep the scanner read-only and free of imports from the audited project.

</details>

## Contributing

Issues with a short Pandas snippet and expected classification are useful; new rules should include a test that distinguishes a Pandas call from an unrelated method with the same name, and suggestions should stay conservative because source syntax alone cannot prove equivalent results. See [CONTRIBUTING.md](CONTRIBUTING.md) or [open an issue](https://github.com/Arthur031221/polars-ready/issues).

## License

MIT licensed. See [LICENSE](LICENSE).
