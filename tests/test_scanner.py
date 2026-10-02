import json
import tempfile
import unittest
from pathlib import Path

from polars_ready.cli import main, render
from polars_ready.scanner import scan_path, scan_source


class ScannerTests(unittest.TestCase):
    def test_alias_and_chained_methods(self):
        text = "import pandas as p\na = p.read_csv('x')\nb = a.groupby('x').apply(lambda x: x)\n"
        found = scan_source(text, "x.py")
        self.assertEqual([f["rule"] for f in found], ["read_csv", "groupby", "apply"])
        self.assertEqual([f["line"] for f in found], [2, 3, 3])

    def test_unrelated_methods_not_reported(self):
        text = "import pandas as pd\nclass Other: pass\na = Other()\na.apply(lambda x:x)\n"
        self.assertEqual(scan_source(text, "x.py"), [])

    def test_reassignment_clears_frame_tracking(self):
        text = (
            "import pandas as pd\n"
            "frame = pd.read_csv('x.csv')\n"
            "frame = load_settings()\n"
            "frame.groupby('region')\n"
            "frame: object = load_settings()\n"
            "frame.apply(callback)\n"
        )
        found = scan_source(text, "x.py")
        self.assertEqual([finding["rule"] for finding in found], ["read_csv"])

    def test_index_and_timezone_traps(self):
        text = "from pandas import DataFrame as DF\nf = DF({'x':[1]})\nf.loc[0]\nf['x'].dt.tz_localize('UTC')\n"
        found = scan_source(text, "x.py")
        self.assertEqual({x["rule"] for x in found}, {"DataFrame", "loc", "dt_tz_localize"})

    def test_notebook_locations_and_errors(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            (base / "one.ipynb").write_text(json.dumps({"cells": [{"cell_type": "code", "source": ["import pandas as pd\n", "pd.read_csv('a')"]}]}))
            (base / "bad.py").write_text("def broken(\n")
            report = scan_path(base)
            self.assertEqual(report["files_scanned"], 1)
            self.assertEqual(report["findings"][0]["cell"], 1)
            self.assertEqual(len(report["errors"]), 1)

    def test_cli_json_and_blocker_exit(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "script.py"
            path.write_text("import pandas as pd\nx = pd.DataFrame({})\nx.iterrows()\n")
            report = scan_path(path)
            self.assertEqual(report["counts"], {"direct": 1, "rewrite": 0, "blocker": 1})
            self.assertEqual(report["score"], 50)
            self.assertIn("iterrows", render(report, False))
            from contextlib import redirect_stdout
            from io import StringIO
            with redirect_stdout(StringIO()) as stdout:
                rc = main([str(path), "--json", "--fail-on-blocker"])
            self.assertEqual(rc, 2)
            self.assertEqual(json.loads(stdout.getvalue())["version"], 1)


if __name__ == "__main__":
    unittest.main()
