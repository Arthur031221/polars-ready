# Contributing

Issues with a short Pandas snippet and the expected classification are useful. A new rule should include a test that distinguishes a Pandas call from an unrelated method with the same name. Keep suggestions conservative: source syntax alone cannot prove equivalent results.

Install with `python -m pip install -e .` and run `python -m unittest discover -s tests -v`. Run `polars-ready examples/sales_pipeline.py` after changing report formatting. Please keep the scanner read-only and free of imports from the audited project.
