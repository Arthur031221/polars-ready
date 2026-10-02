"""AST scanner for common Pandas calls. It never imports the audited project."""
from __future__ import annotations

import ast
import json
from pathlib import Path

from .rules import RULES, WEIGHTS


class PandasVisitor(ast.NodeVisitor):
    def __init__(self, filename: str, cell: int | None = None):
        self.filename, self.cell = filename, cell
        self.modules: set[str] = set()
        self.objects: dict[str, str] = {}
        self.frames: set[str] = set()
        self.findings: list[dict] = []
        self.seen: set[tuple[int, int, str]] = set()

    def add(self, node: ast.AST, rule: str, detail: str = "") -> None:
        severity, suggestion, confidence, explanation = RULES[rule]
        key = (node.lineno, node.col_offset, rule)
        if key in self.seen:
            return
        self.seen.add(key)
        result = {"file": self.filename, "line": node.lineno, "column": node.col_offset + 1,
                  "rule": rule, "severity": severity, "confidence": confidence,
                  "suggestion": suggestion, "reason": explanation}
        if self.cell is not None:
            result["cell"] = self.cell
        if detail:
            result["detail"] = detail
        self.findings.append(result)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name == "pandas":
                self.modules.add(alias.asname or alias.name)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module == "pandas":
            for alias in node.names:
                self.objects[alias.asname or alias.name] = alias.name

    def is_pandas_call(self, node: ast.Call) -> bool:
        f = node.func
        return (isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id in self.modules) or (isinstance(f, ast.Name) and f.id in self.objects)

    def pandas_name(self, node: ast.Call) -> str | None:
        if not self.is_pandas_call(node):
            return None
        return node.func.attr if isinstance(node.func, ast.Attribute) else self.objects[node.func.id]

    def from_frame(self, expr: ast.AST) -> bool:
        if isinstance(expr, ast.Name):
            return expr.id in self.frames
        if isinstance(expr, ast.Call):
            if self.pandas_name(expr) in RULES:
                return True
            if isinstance(expr.func, ast.Attribute):
                return self.from_frame(expr.func.value)
        if isinstance(expr, (ast.Attribute, ast.Subscript)):
            return self.from_frame(expr.value)
        return False

    def visit_Assign(self, node: ast.Assign) -> None:
        self.visit(node.value)
        if self.from_frame(node.value):
            for target in node.targets:
                for name in ast.walk(target):
                    if isinstance(name, ast.Name):
                        self.frames.add(name.id)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if node.value:
            self.visit(node.value)
            if isinstance(node.target, ast.Name) and self.from_frame(node.value):
                self.frames.add(node.target.id)

    def visit_Call(self, node: ast.Call) -> None:
        name = self.pandas_name(node)
        if name in RULES:
            self.add(node, name)
        elif isinstance(node.func, ast.Attribute) and node.func.attr in RULES and self.from_frame(node.func.value):
            self.add(node, node.func.attr)
        for keyword in node.keywords:
            if keyword.arg == "inplace" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True and (name or isinstance(node.func, ast.Attribute) and self.from_frame(node.func.value)):
                self.add(node, "assign", "inplace=True mutates a Pandas object; use an explicit Polars assignment")
            if keyword.arg == "dtype" and isinstance(keyword.value, ast.Constant) and keyword.value.value in ("object", object):
                self.add(node, "astype", "object dtype needs a concrete Polars type")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr in ("loc", "iloc", "at", "iat", "cat") and self.from_frame(node.value):
            self.add(node, node.attr)
        if node.attr == "MultiIndex" and isinstance(node.value, ast.Name) and node.value.id in self.modules:
            self.add(node, "MultiIndex")
        if node.attr in ("tz_localize", "tz_convert") and isinstance(node.value, ast.Attribute) and node.value.attr == "dt" and self.from_frame(node.value.value):
            self.add(node, "dt_" + node.attr)
        self.generic_visit(node)


def scan_source(source: str, filename: str, cell: int | None = None) -> list[dict]:
    tree = ast.parse(source, filename=filename)
    visitor = PandasVisitor(filename, cell)
    visitor.visit(tree)
    return sorted(visitor.findings, key=lambda f: (f.get("cell", 0), f["line"], f["column"], list(RULES).index(f["rule"])))


def scan_path(path: Path) -> dict:
    if path.is_file():
        paths = [path]
    elif path.is_dir():
        paths = sorted(p for p in path.rglob("*") if p.suffix in (".py", ".ipynb") and not any(s.startswith(".") or s in {"venv", "node_modules", "__pycache__"} for s in p.relative_to(path).parts))
    else:
        raise ValueError(f"path does not exist: {path}")
    findings: list[dict] = []
    errors: list[dict] = []
    scanned = 0
    for file in paths:
        if file.suffix not in (".py", ".ipynb"):
            continue
        try:
            text = file.read_text(encoding="utf-8")
            if file.suffix == ".ipynb":
                notebook = json.loads(text)
                cells = notebook.get("cells", [])
                for number, cell in enumerate(cells, 1):
                    if cell.get("cell_type") != "code":
                        continue
                    source = cell.get("source", "")
                    source = "".join(source) if isinstance(source, list) else source
                    if source.lstrip().startswith(("%", "!")):
                        continue
                    findings.extend(scan_source(source, str(file), number))
            else:
                findings.extend(scan_source(text, str(file)))
            scanned += 1
        except (OSError, UnicodeError, ValueError, SyntaxError, TypeError) as exc:
            errors.append({"file": str(file), "error": str(exc)})
    counts = {severity: sum(f["severity"] == severity for f in findings) for severity in WEIGHTS}
    # A heuristic triage score, not a prediction of equivalent outputs or migration cost.
    score = round(100 * counts["direct"] / len(findings)) if findings else None
    return {"version": 1, "path": str(path), "files_scanned": scanned, "findings": findings,
            "counts": counts, "score": score, "errors": errors}
