from __future__ import annotations

import ast
import hashlib
from collections import defaultdict
from pathlib import Path

from app.analysis.diff_parser import FileChange, parse_unified_diff
from app.analysis.python_ast import ParsedModule, ParsedSymbol, enclosing_symbol, parse_repository
from app.models import (AnalysisReport, ChangeSummary, ChangedFile, Evidence, Recommendation,
                        Relationship, Risk, Symbol)


BASE_LIMITATIONS = [
    "Python-only MVP: non-Python files are reported but not structurally analyzed.",
    "Caller relationships include only statically detectable direct calls.",
    "Dynamic imports, reflection, and runtime dependencies are not guaranteed.",
    "Test coverage mapping is a static heuristic; recommendations are not execution results.",
]


def _id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode()).hexdigest()[:12]
    return f"{prefix}-{digest}"


def _symbol(symbol: ParsedSymbol, evidence_ids: list[str] | None = None) -> Symbol:
    return Symbol(id=_id("symbol", symbol.qualified_name, symbol.file_path), name=symbol.name,
                  qualified_name=symbol.qualified_name, type=symbol.type, file_path=symbol.file_path,
                  start_line=symbol.start_line, end_line=symbol.end_line, evidence_ids=evidence_ids or [])


def _call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
        return f"{node.func.value.id}.{node.func.attr}"
    return None


def _find_callers(modules: dict[str, ParsedModule], changed: list[ParsedSymbol]) -> tuple[list[Relationship], list[Evidence], list[ParsedSymbol]]:
    changed_by_name = defaultdict(list)
    for symbol in changed:
        if symbol.type != "class":
            changed_by_name[symbol.name].append(symbol)
    relationships: list[Relationship] = []
    evidence: list[Evidence] = []
    affected: dict[str, ParsedSymbol] = {}
    for module in modules.values():
        for node in ast.walk(module.tree):
            if not isinstance(node, ast.Call):
                continue
            call_name = _call_name(node)
            if not call_name:
                continue
            lookup_name = call_name.rsplit(".", 1)[-1]
            candidates = changed_by_name.get(lookup_name, [])
            if len(candidates) != 1:
                continue
            target = candidates[0]
            if "." in call_name and call_name.split(".")[0] not in module.imports:
                continue
            caller = enclosing_symbol(module.symbols, node.lineno)
            if caller is None or caller.qualified_name == target.qualified_name:
                continue
            evidence_id = _id("evidence", "call", module.file_path, str(node.lineno), target.qualified_name)
            evidence.append(Evidence(id=evidence_id, kind="call_site", file_path=module.file_path,
                                     line_start=node.lineno, line_end=node.lineno, symbol=caller.qualified_name,
                                     description=f"Statically detected call to {target.qualified_name}.", snippet=call_name))
            relationships.append(Relationship(source=caller.qualified_name, target=target.qualified_name,
                                               evidence_ids=[evidence_id]))
            affected[caller.qualified_name] = caller
    relationships.sort(key=lambda item: (item.source, item.target))
    return relationships, evidence, sorted(affected.values(), key=lambda item: (item.file_path, item.start_line, item.name))


def _test_recommendations(root: Path, modules: dict[str, ParsedModule], changed: list[ParsedSymbol], evidence: list[Evidence]) -> list[Recommendation]:
    recommendations: list[Recommendation] = []
    test_files = [(path, module) for path, module in modules.items() if path.startswith("tests/") or "/test_" in path]
    for symbol in changed:
        matches: list[tuple[str, int]] = []
        for file_path, module in test_files:
            for node in ast.walk(module.tree):
                if isinstance(node, ast.Name) and node.id == symbol.name:
                    matches.append((file_path, node.lineno))
        evidence_ids: list[str] = []
        for file_path, line in sorted(set(matches)):
            evidence_id = _id("evidence", "test", file_path, str(line), symbol.qualified_name)
            evidence.append(Evidence(id=evidence_id, kind="test_reference", file_path=file_path, line_start=line,
                                     line_end=line, symbol=symbol.qualified_name,
                                     description=f"Existing test statically references {symbol.name}."))
            evidence_ids.append(evidence_id)
        is_handler = "api" in symbol.file_path or symbol.name.startswith(("get_", "post_", "create_"))
        title = f"Run an integration check for {symbol.name}" if is_handler else f"Test {symbol.name} behavior"
        reason = ("The changed handler should be checked through its public route or function boundary."
                  if is_handler else ("An existing test statically references this changed symbol." if matches
                  else "No direct test reference was found; add a focused behavior test."))
        recommendations.append(Recommendation(id=_id("test-rec", symbol.qualified_name), title=title, reason=reason,
                                               related_symbols=[symbol.qualified_name], evidence_ids=evidence_ids,
                                               confidence="high" if matches else "medium"))
    return sorted(recommendations, key=lambda item: item.id)


def analyze(diff_text: str, repository_root: Path) -> AnalysisReport:
    file_changes = parse_unified_diff(diff_text)
    modules, syntax_limitations = parse_repository(repository_root)
    evidence: list[Evidence] = []
    changed_parsed: dict[str, tuple[ParsedSymbol, list[str]]] = {}
    for file_change in file_changes:
        file_evidence_ids: list[str] = []
        for line, text in file_change.added_lines:
            evidence_id = _id("evidence", "changed", file_change.path, str(line), text)
            evidence.append(Evidence(id=evidence_id, kind="changed_line", file_path=file_change.path,
                                     line_start=line, line_end=line, description="Added line in supplied diff.", snippet=text))
            file_evidence_ids.append(evidence_id)
            module = modules.get(file_change.path)
            if module:
                mapped = enclosing_symbol(module.symbols, line)
                if mapped:
                    prior = changed_parsed.setdefault(mapped.qualified_name, (mapped, []))
                    prior[1].append(evidence_id)
        for line, text in file_change.deleted_lines:
            evidence_id = _id("evidence", "deleted", file_change.path, str(line), text)
            evidence.append(Evidence(id=evidence_id, kind="deleted_line", file_path=file_change.path,
                                     line_start=line, line_end=line, description="Deleted line in supplied diff.", snippet=text))
            file_evidence_ids.append(evidence_id)
    changed_entries = sorted(changed_parsed.values(), key=lambda item: (item[0].file_path, item[0].start_line, item[0].name))
    changed = [entry[0] for entry in changed_entries]
    changed_symbols = [_symbol(symbol, ids) for symbol, ids in changed_entries]
    relationships, call_evidence, affected_parsed = _find_callers(modules, changed)
    evidence.extend(call_evidence)
    affected_symbols = [_symbol(symbol) for symbol in affected_parsed]
    recommendations = _test_recommendations(repository_root, modules, changed, evidence)
    callers = defaultdict(list)
    for relationship in relationships:
        callers[relationship.target].append(relationship)
    risks: list[Risk] = []
    for symbol in changed_symbols:
        symbol_callers = callers[symbol.qualified_name]
        if len(symbol_callers) >= 2:
            title = "Potential shared-impact risk"
            risks.append(Risk(id=_id("risk", "multiple-callers", symbol.qualified_name), severity="medium", title=title,
                              description=f"{symbol.name} has {len(symbol_callers)} statically detectable direct callers.",
                              related_symbols=[symbol.qualified_name, *(item.source for item in symbol_callers)],
                              evidence_ids=[eid for item in symbol_callers for eid in item.evidence_ids]))
        matching = next((item for item in recommendations if symbol.qualified_name in item.related_symbols), None)
        if matching and not matching.evidence_ids:
            risks.append(Risk(id=_id("risk", "test-coverage", symbol.qualified_name), severity="low",
                              title="Potential test-coverage risk", description=f"No direct existing test reference was found for {symbol.name}.",
                              related_symbols=[symbol.qualified_name], evidence_ids=symbol.evidence_ids))
    explanations = [f"Changed symbol: {symbol.qualified_name}\nFile: {symbol.file_path}\nLines: {symbol.start_line}-{symbol.end_line}\n\nThis symbol changed in the supplied diff. It has {len(callers[symbol.qualified_name])} statically detectable caller(s)." for symbol in changed_symbols]
    file_models: list[ChangedFile] = []
    for file_change in file_changes:
        related = [symbol.qualified_name for symbol in changed_symbols if symbol.file_path == file_change.path]
        ids = [item.id for item in evidence if item.file_path == file_change.path]
        file_models.append(ChangedFile(path=file_change.path, change_type=file_change.change_type,
                                       lines_added=len(file_change.added_lines), lines_deleted=len(file_change.deleted_lines),
                                       related_symbols=related, evidence_ids=ids))
    limitations = BASE_LIMITATIONS + syntax_limitations
    unmapped = [f.path for f in file_changes if f.path.endswith(".py") and f.added_lines and not any(s.file_path == f.path for s in changed_symbols)]
    if unmapped:
        limitations.append("Some changed Python lines could not be confidently mapped to a parsed symbol: " + ", ".join(sorted(unmapped)) + ".")
    digest = hashlib.sha256((diff_text + str(repository_root.resolve())).encode()).hexdigest()[:16]
    return AnalysisReport(session_id=digest,
        change_summary=ChangeSummary(files_changed=len(file_models), lines_added=sum(len(f.added_lines) for f in file_changes),
            lines_deleted=sum(len(f.deleted_lines) for f in file_changes), symbols_changed=len(changed_symbols),
            symbols_affected=len(affected_symbols), potential_risks=len(risks), test_recommendations=len(recommendations)),
        files=file_models, changed_symbols=changed_symbols, affected_symbols=affected_symbols, relationships=relationships,
        evidence=sorted(evidence, key=lambda item: item.id), risks=sorted(risks, key=lambda item: item.id),
        test_recommendations=recommendations, limitations=limitations, explanations=explanations)
