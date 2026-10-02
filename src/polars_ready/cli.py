"""Command line entry point."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .scanner import scan_path

COLORS = {"direct": "\033[32m", "rewrite": "\033[33m", "blocker": "\033[31m"}
RESET = "\033[0m"


def render(report: dict, color: bool = True) -> str:
    c = (lambda key: COLORS[key]) if color else (lambda key: "")
    reset = RESET if color else ""
    findings = report["findings"]
    counts = report["counts"]
    score = f'{report["score"]}% direct patterns' if report["score"] is not None else "No recognized Pandas patterns"
    lines = ["POLARS READY  |  static migration audit", "", score,
             f'{counts["direct"]} direct    {counts["rewrite"]} rewrite    {counts["blocker"]} blocker',
             f'{report["files_scanned"]} files scanned', ""]
    grouped: dict[str, list[dict]] = {}
    for finding in findings:
        grouped.setdefault(finding["file"], []).append(finding)
    for filename, items in grouped.items():
        direct = sum(x["severity"] == "direct" for x in items)
        width = 20
        filled = round(width * direct / len(items))
        lines.append(f'{filename}  [{"#" * filled}{"." * (width - filled)}] {direct}/{len(items)} direct')
        for f in items:
            location = f'{f["file"]}:{f["line"]}'
            if "cell" in f:
                location += f' (cell {f["cell"]})'
            lines.append(f'  {c(f["severity"])}{f["severity"].upper():7}{reset} {location}  {f["rule"]}')
            lines.append(f'          {f.get("detail") or f["suggestion"]}')
        lines.append("")
    for error in report["errors"]:
        lines.append(f'ERROR {error["file"]}: {error["error"]}')
    if findings:
        lines.append("Score = direct findings / recognized findings. Review every result before migration.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect Pandas code without importing or executing it")
    parser.add_argument("path", type=Path, help="Python file, notebook or directory")
    parser.add_argument("--json", action="store_true", help="Stable JSON report")
    parser.add_argument("--no-color", action="store_true", help="Disable ANSI colors")
    parser.add_argument("--fail-on-blocker", action="store_true", help="Exit 2 if a blocker is found")
    args = parser.parse_args(argv)
    try:
        report = scan_path(args.path)
    except ValueError as exc:
        parser.error(str(exc))
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(render(report, color=sys.stdout.isatty() and not args.no_color))
    if report["errors"]:
        return 1
    return 2 if args.fail_on_blocker and report["counts"]["blocker"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
