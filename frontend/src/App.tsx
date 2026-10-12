import { useEffect, useState } from "react";
const API = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
type Dec = { action: string; reply: string };
type Case = any;
type Report = { total: number; passed: number; pass_rate: number; unsafe_acceptance_rate: number; valid_decision_rejection_rate: number; results: { case_id: string; category: string; passed: boolean; rules: string[] }[] };
const APPT = ["confirmed", "tentative", "pending", "none"];
const CREW = ["confirmed", "unknown", "pending", "unconfirmed"];
const pct = (n: number) => (n * 100).toFixed(0) + "%";
const LABEL: Record<string, string> = { conflict_accuracy: "Conflict", customer_intent: "Customer intent", availability_integrity: "Availability", confirmation_integrity: "Crew confirmation", data_uncertainty_extension: "Missing data" };

export default function App() {
  const [cases, setCases] = useState<Case[]>([]);
  const [sel, setSel] = useState("C-001");
  const [report, setReport] = useState<Report | null>(null);
  const [out, setOut] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  // custom simulation
  const [msg, setMsg] = useState("Can you come this Saturday?");
  const [appt, setAppt] = useState("confirmed");
  const [crew, setCrew] = useState("unknown");
  const [slots, setSlots] = useState("Monday 10:00, Tuesday 14:00");
  const [custom, setCustom] = useState(false);
  const [customMsg, setCustomMsg] = useState("");

  const call = async (path: string, body?: any) => {
    const r = await fetch(API + path, body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : { method: path.includes("evaluate") ? "POST" : "GET" });
    if (!r.ok) throw new Error("HTTP " + r.status);
    return r.json();
  };
  useEffect(() => {
    call("/api/cases").then(setCases).catch(() => setErr("Backend unreachable"));
    call("/api/evaluate").then(setReport).catch(() => {});
  }, []);

  const current = cases.find((c) => c.case_id === sel);
  const customCase = () => ({
    case_id: "LIVE", category: "custom", customer_message: msg,
    appointment: { date: "2026-10-13", start_time: "09:00", end_time: "12:00", status: appt },
    crew: { confirmation_status: crew },
    available_slots: slots.split(",").map((s) => s.trim()).filter(Boolean).map((s) => { const [d, t] = s.split(/\s+/); return { date: d, start_time: t || "" }; }),
    other_jobs: [],
  });
  async function run(kind: "replay" | "live") {
    setBusy(true); setErr(""); setOut(null);
    try {
      let c: any;
      if (custom) { c = customCase(); setCustomMsg(c.customer_message); }
      else { c = { ...current }; delete c.expected; if (kind === "live") delete c.proposed_decision; }
      setOut(await call("/api/decide", c));
    } catch (e: any) { setErr(String(e.message || e)); } finally { setBusy(false); }
  }
  const customerText = custom ? customMsg || msg : current?.customer_message;

  return (<>
    <div className="hero"><div className="in">
      <div className="eyebrow">AGENT RELIABILITY LAB</div>
      <h1>AI Scheduling Assistant</h1>
      <p>A model proposes the reply. A deterministic policy checks it against the scheduling facts before the customer sees anything.</p>
      <span className="tag">Synthetic data · no real bookings</span>
    </div></div>
    <main>
      <div className="metrics">
        {[["Test cases", report?.total ?? "—"], ["Policy pass rate", report ? pct(report.pass_rate) : "—"], ["Unsafe replies let through", report ? pct(report.unsafe_acceptance_rate) : "—"], ["Valid replies wrongly blocked", report ? pct(report.valid_decision_rejection_rate) : "—"]].map(([a, b]) => <div className="m" key={String(a)}><small>{a}</small><b>{b}</b></div>)}
      </div>
      {err && <div className="err">{err}</div>}
      <div className="grid">
        <div className="card">
          <h3>1 · CHOOSE A SCENARIO</h3>
          {cases.map((c) => <button key={c.case_id} className={"case" + (!custom && sel === c.case_id ? " on" : "")} onClick={() => { setSel(c.case_id); setCustom(false); setOut(null); }}>
            <b>{c.case_id}</b> · {LABEL[c.category] || c.category}<small>{c.customer_message}</small></button>)}
          <button className={"case" + (custom ? " on" : "")} onClick={() => { setCustom(true); setOut(null); }}><b>＋ Build your own</b><small>Type a message and set the facts</small></button>
          {custom && <>
            <label>Customer message</label><textarea rows={2} value={msg} onChange={(e) => setMsg(e.target.value)} />
            <div className="two"><div><label>Appointment</label><select value={appt} onChange={(e) => setAppt(e.target.value)}>{APPT.map((x) => <option key={x}>{x}</option>)}</select></div>
              <div><label>Crew</label><select value={crew} onChange={(e) => setCrew(e.target.value)}>{CREW.map((x) => <option key={x}>{x}</option>)}</select></div></div>
            <label>Available slots</label><input value={slots} onChange={(e) => setSlots(e.target.value)} />
          </>}
          <div className="row">
            {!custom && <button className="sec" disabled={busy} onClick={() => run("replay")}>Replay model reply</button>}
            <button className="pri" disabled={busy} onClick={() => run("live")}>{busy ? "Running…" : "Ask live agent"}</button>
          </div>
        </div>
        <div className="card">
          <h3>2 · CONVERSATION SIMULATION</h3>
          <div className="chat">
            <div className="b cust"><small>CUSTOMER</small>{customerText || "Pick a scenario"}</div>
            {!out && <div className="alt">Run a scenario to see the agent’s proposal, the policy check and what the customer would receive.</div>}
            {out && <>
              <div className="b prop"><small>AGENT PROPOSAL · {out.mode} · {out.proposed_decision.action}</small>{out.proposed_decision.reply}</div>
              <div className={"guard " + (out.acceptable ? "ok" : "bad")}>
                <span className="pill">{out.acceptable ? "APPROVED" : "BLOCKED"}</span>
                {out.acceptable ? "Every claim is supported by the scheduling facts." : out.findings.map((f: any) => <div key={f.rule_id}><b>{f.rule_id}</b> — {f.reason}</div>)}
              </div>
              <div className="b final"><small>SENT TO CUSTOMER · action: {out.final_action}</small>{out.final_reply}</div>
              {!out.acceptable && <div className="alt">The unsafe proposal was replaced by the policy’s safer alternative.</div>}
            </>}
          </div>
          {report && <><h3 style={{ marginTop: 22 }}>3 · EVALUATION SUITE</h3>
            {report.results.map((r) => <div className="res" key={r.case_id}><span><b>{r.case_id}</b> · {LABEL[r.category] || r.category}</span><span>{r.rules.join(", ") || "valid"} <span className={r.passed ? "pass" : "fail"}>{r.passed ? "✓ PASS" : "✗ FAIL"}</span></span></div>)}</>}
        </div>
      </div>
    </main>
    <footer>Model output is a proposal, never authorization · <a href="/docs/index.html">Case study</a></footer>
  </>);
}
