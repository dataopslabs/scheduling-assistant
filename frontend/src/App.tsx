import { useEffect, useState } from "react";
const API = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
type Dec = { action: string; reply: string };
type Case = any;
type _Report = { total: number; passed: number; pass_rate: number; unsafe_acceptance_rate: number; valid_decision_rejection_rate: number; results: { case_id: string; category: string; passed: boolean; rules: string[] }[] };
const APPT = ["confirmed", "tentative", "pending", "none"];
const CREW = ["confirmed", "unknown", "pending", "unconfirmed"];
const RULES = [["E1", "Conflict accuracy"], ["E2", "Customer intent"], ["E3", "Availability"], ["E4", "Crew confirmation"], ["E5", "Data completeness"]];
const pct = (n: number) => (n * 100).toFixed(0) + "%";
const LABEL: Record<string, string> = { conflict_accuracy: "Conflict", customer_intent: "Customer intent", availability_integrity: "Availability", confirmation_integrity: "Crew confirmation", data_uncertainty_extension: "Missing data" };

export default function App() {
  const [cases, setCases] = useState<Case[]>([]);
  const [sel, setSel] = useState("C-001");
  const [input, setInput] = useState<any>(null);
  const [log, setLog] = useState<any[]>([]);
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
      const t0 = performance.now();
      const res = await call("/api/decide", c);
      const { proposed_decision, ...facts } = c;
      setInput({ facts, kind });
      setOut(res);
      setLog((l) => [{ n: l.length + 1, id: c.case_id, mode: res.mode, action: res.proposed_decision.action, ok: res.acceptable, rules: res.findings.map((f: any) => f.rule_id), final: res.final_action, ms: Math.round(performance.now() - t0), t: new Date().toLocaleTimeString() }, ...l].slice(0, 12));
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
        {[["Agent runs", log.length], ["Approved", log.filter((r) => r.ok).length], ["Blocked & replaced", log.filter((r) => !r.ok).length], ["Escalated to a human", log.filter((r) => r.final === "escalate").length]].map(([a, b]) => <div className="m" key={String(a)}><small>{a}</small><b>{b}</b></div>)}
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
        </div>
      </div>
      {out && input && <div className="card" style={{ marginTop: 18 }}>
        <h3>3 · DATA AND DECISION BEHIND THIS RUN</h3>
        <div className="three">
          <div><h4>Data the agent saw</h4>
            <table className="kv"><tbody>
              <tr><td>Customer message</td><td>{input.facts.customer_message}</td></tr>
              <tr><td>Appointment</td><td>{input.facts.appointment?.date} {input.facts.appointment?.start_time}–{input.facts.appointment?.end_time} · <b>{input.facts.appointment?.status ?? "missing"}</b></td></tr>
              <tr><td>Crew confirmation</td><td><b>{input.facts.crew?.confirmation_status ?? "missing"}</b></td></tr>
              <tr><td>Available slots</td><td>{input.facts.available_slots?.length ? input.facts.available_slots.map((x: any) => `${x.date} ${x.start_time}`).join(", ") : "none supplied"}</td></tr>
              <tr><td>Other jobs</td><td>{input.facts.other_jobs?.length ? input.facts.other_jobs.map((j: any) => `${j.job_id || "job"}: ${j.status}`).join(", ") : "none"}</td></tr>
            </tbody></table></div>
          <div><h4>Policy checks</h4>
            {RULES.map(([id, name]) => { const hit = out.findings.find((f: any) => f.rule_id.startsWith(id)); const skipped = !hit && out.findings.some((f: any) => f.rule_id.startsWith("E5"));
              return <div className="rule" key={id}><span>{id} · {name}</span><span className={hit ? "fail" : skipped ? "skip" : "pass"}>{hit ? "✗ BLOCKED" : skipped ? "– skipped" : "✓ passed"}</span>{hit && <div className="alt">{hit.reason}</div>}</div>; })}
          </div>
          <div><h4>Decision record</h4>
            <pre>{JSON.stringify({ source: out.mode, proposed: out.proposed_decision, verdict: out.acceptable ? "approved" : "blocked", final: { action: out.final_action, reply: out.final_reply } }, null, 2)}</pre></div>
        </div>
      </div>}
      {log.length > 0 && <div className="card" style={{ marginTop: 18 }}>
        <h3>4 · RUN LOG (THIS SESSION)</h3>
        <table className="log"><thead><tr><th>#</th><th>Time</th><th>Scenario</th><th>Source</th><th>Proposed</th><th>Verdict</th><th>Rules</th><th>Final</th><th>ms</th></tr></thead>
          <tbody>{log.map((r) => <tr key={r.n}><td>{r.n}</td><td>{r.t}</td><td>{r.id}</td><td>{r.mode}</td><td>{r.action}</td><td className={r.ok ? "pass" : "fail"}>{r.ok ? "approved" : "blocked"}</td><td>{r.rules.join(", ") || "—"}</td><td>{r.final}</td><td>{r.ms}</td></tr>)}</tbody></table>
      </div>}
    </main>
    <footer>Model output is a proposal, never authorization · <a href="/docs/index.html">Case study</a></footer>
  </>);
}
