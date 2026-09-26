"use client";

import { ChangeEvent, useMemo, useState } from "react";
import Link from "next/link";

type Evidence = { id: string; kind: string; file_path: string; line_start?: number | null; line_end?: number | null; symbol?: string | null; description: string; snippet?: string | null };
type Symbol = { id: string; name: string; qualified_name: string; type: string; file_path: string; start_line: number; end_line: number; evidence_ids: string[] };
type Report = {
  session_id: string; change_summary: { files_changed: number; lines_added: number; lines_deleted: number; symbols_changed: number; symbols_affected: number; potential_risks: number; test_recommendations: number };
  files: { path: string; change_type: string; lines_added: number; lines_deleted: number; related_symbols: string[]; evidence_ids: string[] }[];
  changed_symbols: Symbol[]; affected_symbols: Symbol[]; relationships: { source: string; target: string; evidence_ids: string[] }[];
  evidence: Evidence[]; risks: { id: string; severity: string; title: string; description: string; related_symbols: string[]; evidence_ids: string[] }[];
  test_recommendations: { id: string; title: string; reason: string; related_symbols: string[]; evidence_ids: string[]; confidence: string }[];
  verification: { status: string; passed: string[]; failed: string[]; duration_seconds: number; summary: string } | null;
  limitations: string[]; explanations: string[];
};

const API = process.env.NEXT_PUBLIC_CHANGESTORY_API ?? "http://127.0.0.1:8000";
const scenarios = [
  { id: "calculation", label: "A · Calculation change", file: "/fixtures/diffs/calculation.diff", hint: "Pricing function with two direct callers" },
  { id: "api", label: "B · API handler", file: "/fixtures/diffs/api-handler.diff", hint: "Handler-level integration recommendation" },
  { id: "utility", label: "C · Shared utility", file: "/fixtures/diffs/shared-utility.diff", hint: "Formatting helper with multiple consumers" },
];

function download(url: string) { window.open(url, "_blank", "noopener,noreferrer"); }

export function Dashboard({ initialReport }: { initialReport?: Report }) {
  const [diff, setDiff] = useState("");
  const [report, setReport] = useState<Report | undefined>(initialReport);
  const [selected, setSelected] = useState<{ title: string; evidenceIds: string[]; description?: string }>();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const evidence = useMemo(() => report?.evidence.filter((item) => selected?.evidenceIds.includes(item.id)) ?? [], [report, selected]);

  async function pickScenario(file: string) {
    setError("");
    const response = await fetch(file);
    setDiff(await response.text());
  }
  async function analyze() {
    if (!diff.trim()) { setError("Paste a unified Git diff or select a demo scenario before analyzing."); return; }
    setLoading(true); setError("");
    try {
      const response = await fetch(`${API}/api/v1/analyze`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ diff_text: diff, source_mode: "sample" }) });
      const data = await response.json();
      if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Analysis could not be completed.");
      setReport(data); setSelected(undefined);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "The analysis service is unavailable. Start the backend and try again."); }
    finally { setLoading(false); }
  }
  async function verify() {
    if (!report) return;
    setLoading(true); setError("");
    try {
      const response = await fetch(`${API}/api/v1/reports/${report.session_id}/verify`, { method: "POST" });
      const data = await response.json(); if (!response.ok) throw new Error(data.detail ?? "Verification could not run."); setReport(data);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Verification failed."); } finally { setLoading(false); }
  }
  function readFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]; if (!file) return;
    const reader = new FileReader(); reader.onload = () => setDiff(String(reader.result ?? "")); reader.readAsText(file);
  }
  const metrics = report ? [
    ["Files changed", report.change_summary.files_changed, "Scope"], ["Symbols changed", report.change_summary.symbols_changed, "Detected facts"],
    ["Potential risks", report.change_summary.potential_risks, "Heuristic"], ["Suggested tests", report.change_summary.test_recommendations, "Static evidence"],
  ] : [];
  return <main className="shell">
    <header className="topbar"><Link className="brand" href="/"><span className="brand-mark">↟</span> ChangeStory</Link><span className="tag">Deterministic Python change analysis</span><span className="status-dot">Local workspace</span></header>
    <section className="hero"><div><p className="eyebrow">CHANGE INTELLIGENCE / 01</p><h1>See the story<br /><em>behind the diff.</em></h1><p className="lede">Trace changed Python symbols to direct callers, evidence, potential risks, and focused verification—without pretending static analysis knows everything.</p></div><div className="hero-card"><span>Analysis contract</span><strong>Facts ≠ risks ≠ tests</strong><p>Every output keeps detected evidence, potential impact, suggested checks, and actual execution results separate.</p></div></section>
    <section className="workspace" aria-label="Diff analysis workspace"><div className="input-panel panel"><div className="panel-heading"><div><p className="eyebrow">INPUT</p><h2>Supply a unified diff</h2></div><button className="text-button" onClick={() => { setDiff(""); setReport(undefined); setError(""); }}>Reset workspace</button></div><div className="scenario-list">{scenarios.map((scenario) => <button key={scenario.id} className="scenario" onClick={() => pickScenario(scenario.file)}><b>{scenario.label}</b><span>{scenario.hint}</span></button>)}</div><label className="dropzone"><span>Diff text</span><textarea value={diff} onChange={(event) => setDiff(event.target.value)} placeholder={'diff --git a/example.py b/example.py\n...'} spellCheck={false} /><span className="file-input">Or upload a .diff file<input type="file" accept=".diff,.patch,.txt" onChange={readFile} /></span></label>{error && <p className="error" role="alert">{error}</p>}<button className="analyze-button" disabled={loading} onClick={analyze}>{loading ? "Analyzing controlled sample…" : "Analyze change"}<span>→</span></button></div>
      <aside className="guide panel"><p className="eyebrow">METHOD</p><h2>Evidence first</h2><ol><li><b>Parse</b><span>Changed lines and file status</span></li><li><b>Map</b><span>AST symbols in the sample project</span></li><li><b>Trace</b><span>Conservative direct calls only</span></li><li><b>Verify</b><span>One predefined, bundled test command</span></li></ol><p className="quiet">No external model. No arbitrary test commands. No runtime-impact claims.</p></aside></section>
    {!report && <section className="empty-state"><span>⌁</span><h2>Analysis waits for evidence.</h2><p>Select a demo scenario or paste a standard Git diff to create a local report.</p></section>}
    {report && <section className="results"><div className="report-bar"><div><p className="eyebrow">REPORT / {report.session_id.slice(0, 8)}</p><h2>Change impact report</h2></div><div className="exports"><button onClick={() => download(`${API}/api/v1/reports/${report.session_id}/export.json`)}>Export JSON</button><button onClick={() => download(`${API}/api/v1/reports/${report.session_id}/export.md`)}>Export Markdown</button></div></div><div className="metrics">{metrics.map(([label, value, note]) => <div className="metric" key={String(label)}><span>{label}</span><strong>{value}</strong><small>{note}</small></div>)}</div>
      <div className="result-grid"><section className="panel files"><p className="eyebrow">DETECTED FACTS</p><h2>Changed files</h2>{report.files.map((file) => <button className="file-row" key={file.path} onClick={() => setSelected({ title: file.path, evidenceIds: file.evidence_ids, description: `${file.change_type} file · ${file.related_symbols.length} mapped symbols` })}><span className="file-path">{file.path}</span><span className="change-type">{file.change_type}</span><span>+{file.lines_added} −{file.lines_deleted}</span></button>)}</section>
        <section className="panel graph"><p className="eyebrow">STATIC IMPACT MAP</p><h2>Known direct relationships</h2><div className="graph-stage">{report.changed_symbols.map((symbol) => <button className="node changed" key={symbol.id} onClick={() => setSelected({ title: symbol.qualified_name, evidenceIds: symbol.evidence_ids, description: `${symbol.type} · ${symbol.file_path}:${symbol.start_line}-${symbol.end_line}` })}>{symbol.name}<small>CHANGED</small></button>)}{report.relationships.length ? <div className="edges">{report.relationships.map((edge) => <button key={`${edge.source}-${edge.target}`} onClick={() => setSelected({ title: `${edge.source} calls ${edge.target}`, evidenceIds: edge.evidence_ids, description: "Statically detectable direct call" })}><span>{edge.source.split(".").at(-1)}</span><i>→</i><b>{edge.target.split(".").at(-1)}</b></button>)}</div> : <p className="quiet">No confident direct caller relationships were found.</p>}{report.affected_symbols.map((symbol) => <button className="node affected" key={symbol.id} onClick={() => setSelected({ title: symbol.qualified_name, evidenceIds: [], description: `${symbol.type} affected through a known direct call` })}>{symbol.name}<small>AFFECTED</small></button>)}</div></section></div>
      <div className="lower-grid"><section className="panel"><p className="eyebrow">POTENTIAL RISKS</p><h2>Review signals</h2>{report.risks.length ? report.risks.map((risk) => <button className="risk" key={risk.id} onClick={() => setSelected({ title: risk.title, evidenceIds: risk.evidence_ids, description: risk.description })}><span className={`severity ${risk.severity}`}>{risk.severity}</span><div><b>{risk.title}</b><p>{risk.description}</p></div></button>) : <p className="quiet">No deterministic risk rules were triggered.</p>}</section><section className="panel"><p className="eyebrow">SUGGESTED TESTS</p><h2>Targeted checks</h2>{report.test_recommendations.length ? report.test_recommendations.map((recommendation) => <button className="recommendation" key={recommendation.id} onClick={() => setSelected({ title: recommendation.title, evidenceIds: recommendation.evidence_ids, description: recommendation.reason })}><div><b>{recommendation.title}</b><p>{recommendation.reason}</p></div><span>{recommendation.confidence}</span></button>) : <p className="quiet">No focused test recommendations were produced.</p>}</section></div>
      <div className="lower-grid"><section className="panel verification"><p className="eyebrow">ACTUAL EXECUTION RESULTS</p><h2>Controlled verification</h2>{report.verification ? <><p className={`verification-status ${report.verification.status}`}>{report.verification.status}</p><p>{report.verification.summary} <span>{report.verification.duration_seconds}s</span></p><pre>{[...report.verification.passed, ...report.verification.failed].join("\n")}</pre></> : <><p className="quiet">No controlled verification has been run yet.</p><button className="secondary-button" disabled={loading} onClick={verify}>Run bundled sample tests →</button></>}</section><section className="panel"><p className="eyebrow">ANALYSIS BOUNDARIES</p><h2>Limitations</h2><ul className="limitations">{report.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}</ul></section></div>
      {selected && <aside className="details" aria-live="polite"><button aria-label="Close details" onClick={() => setSelected(undefined)}>×</button><p className="eyebrow">EVIDENCE DETAILS</p><h2>{selected.title}</h2>{selected.description && <p>{selected.description}</p>}<div>{evidence.length ? evidence.map((item) => <article key={item.id}><b>{item.kind.replace("_", " ")}</b><span>{item.file_path}{item.line_start ? `:${item.line_start}` : ""}</span><p>{item.description}</p>{item.snippet && <code>{item.snippet}</code>}</article>) : <p className="quiet">Evidence unavailable for this selected item.</p>}</div></aside>}</section>}
  </main>;
}
