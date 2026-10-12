import { useCallback, useEffect, useMemo, useState } from "react";
import { batch as runBatch, decide, getCases, getConfig, getDatasets, getHealth } from "./api";
import type { AppConfig, BatchResult, Case, Decision, HistoryRow, Mode } from "./types";
import TopBar from "./components/TopBar";
import UseCasePanel, { CustomForm, DEFAULT_CUSTOM } from "./components/UseCasePanel";
import ResponsePanel from "./components/ResponsePanel";
import EvidencePanel from "./components/EvidencePanel";
import AboutPage, { SECTIONS, Section } from "./components/AboutPage";

// Hash routes: #/lab (default) · #/about/problem | #/about/solution | #/about/design
function parseHash(): { page: "lab" | "about"; section: Section } {
  const [, p, sec] = window.location.hash.split("/");
  return { page: p === "about" ? "about" : "lab", section: (SECTIONS as string[]).includes(sec) ? (sec as Section) : "problem" };
}

const store = { get: (k: string) => { try { return localStorage.getItem(k); } catch { return null; } }, set: (k: string, v: string) => { try { localStorage.setItem(k, v); } catch { /* ignore */ } } };

function buildCustom(f: CustomForm, mode: Mode): Case {
  return {
    case_id: "CUSTOM", category: "custom", customer_message: f.message,
    appointment: { date: "2026-10-13", start_time: "09:00", end_time: "12:00", status: f.appt },
    crew: { confirmation_status: f.crew },
    available_slots: f.slots.split(",").map((s) => s.trim()).filter(Boolean).map((s) => { const [d, t] = s.split(/\s+/); return { date: d, start_time: t ?? "" }; }),
    other_jobs: [],
    proposed_decision: mode === "mock" && f.reply.trim() ? { action: f.action as any, reply: f.reply } : null,
  };
}

export default function App() {
  const [route, setRoute] = useState(parseHash);
  useEffect(() => { const h = () => setRoute(parseHash()); window.addEventListener("hashchange", h); return () => window.removeEventListener("hashchange", h); }, []);
  const go = (page: "lab" | "about", section: Section = route.section) => { window.location.hash = page === "about" ? `#/about/${section}` : "#/lab"; };
  const [mode, setMode] = useState<Mode>(() => (store.get("mode") === "live" ? "live" : "mock"));
  const [cases, setCases] = useState<Case[]>([]);
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [api, setApi] = useState<"up" | "down" | "checking">("checking");
  const [loadError, setLoadError] = useState(false);
  const [selected, setSelected] = useState("C-001");
  const [custom, setCustom] = useState<CustomForm>(DEFAULT_CUSTOM);
  const [result, setResult] = useState<Decision | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const [history, setHistory] = useState<HistoryRow[]>([]);
  const [datasets, setDatasets] = useState<Case[]>([]);
  const [variantId, setVariantId] = useState<string | null>(null);
  const [batch, setBatch] = useState<BatchResult | null>(null);
  const [batchRunning, setBatchRunning] = useState(false);

  useEffect(() => {
    getHealth().then(() => setApi("up")).catch(() => setApi("down"));
    getConfig().then(setConfig).catch(() => {});
    getCases().then(setCases).catch(() => setLoadError(true));
    getDatasets().then(setDatasets).catch(() => {});
  }, []);

  const variants = useMemo(() => datasets.filter((d) => d.use_case === selected), [datasets, selected]);
  const scenario: Case | null = useMemo(
    () => (selected === "custom" ? buildCustom(custom, mode)
      : (variantId && datasets.find((d) => d.case_id === variantId)) || cases.find((c) => c.case_id === selected) || null), [selected, variantId, custom, cases, datasets, mode]);

  const reset = () => { setResult(null); setError(""); setBatch(null); };
  const changeMode = (m: Mode) => { setMode(m); store.set("mode", m); reset(); };
  const select = (id: string) => { setSelected(id); setVariantId(null); reset(); };
  const pickVariant = (id: string | null) => { setVariantId(id); reset(); };

  const run = useCallback(async () => {
    if (!scenario) return;
    setRunning(true); setError(""); setResult(null);
    try {
      const r = await decide(mode, scenario);
      setResult(r);
      setHistory((h) => [{ n: h.length ? h[0].n + 1 : 1, time: new Date().toLocaleTimeString(), id: scenario.case_id, mode, source: r.evidence.source, proposed: r.proposed_decision.action, ok: r.acceptable, rules: r.findings.map((x) => x.rule_id), final: r.final_action, ms: r.evidence.latency_ms }, ...h].slice(0, 25));
    } catch (e: any) { setError(String(e.message || e)); } finally { setRunning(false); }
  }, [scenario, mode]);

  const runAll = useCallback(async () => {
    setBatchRunning(true); setError(""); setResult(null); setBatch(null);
    try {
      const b = await runBatch(mode, selected); setBatch(b);
      setHistory((h) => [...b.items.map((i, k) => ({ n: (h[0]?.n ?? 0) + b.items.length - k, time: new Date().toLocaleTimeString(), id: i.case_id, mode, source: i.decision.evidence.source, proposed: i.decision.proposed_decision.action, ok: i.decision.acceptable, rules: i.decision.findings.map((x) => x.rule_id), final: i.decision.final_action, ms: i.decision.evidence.latency_ms })), ...h].slice(0, 40));
    } catch (e: any) { setError(String(e.message || e)); } finally { setBatchRunning(false); }
  }, [mode, selected]);
  const inspect = (id: string) => { const it = batch?.items.find((i) => i.case_id === id); if (it) { setVariantId(id); setResult(it.decision); } };

  const facts = scenario ? (({ proposed_decision, expected, category, ...rest }) => rest)(scenario as any) : null;

  return (
    <div className="app">
      <TopBar mode={mode} onMode={changeMode} config={config} api={api} page={route.page} onPage={(p) => go(p)} />
      {route.page === "about" ? <AboutPage section={route.section} onSection={(sec) => go("about", sec)} onOpenLab={() => go("lab")} /> : (
      <main className="panels">
        <UseCasePanel cases={cases} datasets={datasets} selected={selected} onSelect={select} mode={mode} custom={custom} onCustom={(c) => { setCustom(c); reset(); }} loadError={loadError} />
        <ResponsePanel mode={mode} customer={scenario?.customer_message ?? ""} running={running} result={result} error={error} onRun={run}
          model={config?.model_id} scenario={scenario} custom={selected === "custom"}
          variants={variants} variantId={variantId} onVariant={pickVariant} onRunAll={runAll} batch={batch} batchRunning={batchRunning} onInspect={inspect} />
        <EvidencePanel facts={facts} result={result} history={history} running={running} />
      </main>)}
    </div>
  );
}
