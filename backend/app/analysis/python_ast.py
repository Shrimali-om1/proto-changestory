from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ParsedSymbol:
    name: str
    qualified_name: str
    type: str
    file_path: str
    start_line: int
    end_line: int


@dataclass
class ParsedModule:
    file_path: str
    module_name: str
    tree: ast.Module
    symbols: list[ParsedSymbol]
    imports: dict[str, str]


class _SymbolVisitor(ast.NodeVisitor):
    def __init__(self, module_name: str, file_path: str) -> None:
        self.module_name = module_name
        self.file_path = file_path
        self.symbols: list[ParsedSymbol] = []
        self.stack: list[tuple[str, str]] = []

    def _add(self, node: ast.AST, name: str, symbol_type: str) -> None:
        parent = ".".join([self.module_name, *(x[0] for x in self.stack)])
        self.symbols.append(ParsedSymbol(name, f"{parent}.{name}", symbol_type, self.file_path,
                                         node.lineno, getattr(node, "end_lineno", node.lineno)))

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._add(node, node.name, "class")
        self.stack.append((node.name, "class"))
        self.generic_visit(node)
        self.stack.pop()

    def _function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        in_class = bool(self.stack and self.stack[-1][1] == "class")
        symbol_type = "method" if in_class else ("async_function" if isinstance(node, ast.AsyncFunctionDef) else "function")
        self._add(node, node.name, symbol_type)
        self.stack.append((node.name, "function"))
        self.generic_visit(node)
        self.stack.pop()

    visit_FunctionDef = _function
    visit_AsyncFunctionDef = _function


def module_name_for(relative_path: str) -> str:
    return relative_path.removesuffix(".py").replace("/__init__", "").replace("/", ".")


def parse_python_file(path: Path, relative_path: str) -> ParsedModule:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=relative_path)
    visitor = _SymbolVisitor(module_name_for(relative_path), relative_path)
    visitor.visit(tree)
    imports: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module:
            for item in node.names:
                imports[item.asname or item.name] = f"{node.module}.{item.name}"
        elif isinstance(node, ast.Import):
            for item in node.names:
                imports[item.asname or item.name.split(".")[0]] = item.name
    return ParsedModule(relative_path, module_name_for(relative_path), tree, visitor.symbols, imports)


def parse_repository(root: Path) -> tuple[dict[str, ParsedModule], list[str]]:
    modules: dict[str, ParsedModule] = {}
    limitations: list[str] = []
    for file_path in sorted(root.rglob("*.py")):
        if ".pytest_cache" in file_path.parts or "__pycache__" in file_path.parts:
            continue
        relative = file_path.relative_to(root).as_posix()
        try:
            modules[relative] = parse_python_file(file_path, relative)
        except SyntaxError:
            limitations.append(f"Python file could not be parsed because of a syntax error: {relative}.")
    return modules, limitations


def enclosing_symbol(symbols: list[ParsedSymbol], line: int) -> ParsedSymbol | None:
    matching = [symbol for symbol in symbols if symbol.start_line <= line <= symbol.end_line]
    return min(matching, key=lambda symbol: symbol.end_line - symbol.start_line) if matching else None
