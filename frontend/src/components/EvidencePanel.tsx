import { useState } from "react";
import type { Case, Decision, HistoryRow } from "../types";

type Tab = "facts" | "pipeline" | "policy" | "trace" | "history";
interface Props { facts: Record<string, any> | null; result: Decision | null; history: HistoryRow[]; running: boolean }

const KV = ({ k, v }: { k: string; v: React.ReactNode }) => <div className="kv"><span>{k}</span><div>{v}</div></div>;
const badge = (s?: string | null) => <span className={"st st-" + (s ?? "missing")}>{s ?? "missing"}</span>;
const slotTxt = (x: any) => `${x.date ?? x.day ?? "?"} ${x.start_time ?? x.time ?? ""}`.trim();

export default function EvidencePanel({ facts, result, history, running }: Props) {
  const [tab, setTab] = useState<Tab>("facts");
  const f = (result?.evidence.facts ?? facts) as (Partial<Case> & Record<string, any>) | null;
  const ev = result?.evidence;
  const tabs: [Tab, string][] = [["facts", "Facts"], ["pipeline", "Pipeline"], ["policy", "Policy"], ["trace", "Trace"], ["history", `History${history.length ? ` (${history.length})` : ""}`]];
  return (
    <section className="panel" aria-label="Evidence">
      <div className="phead"><div><h2>Evidence</h2><p>Data and decision behind this run</p></div></div>
      <div className="tabs" role="tablist">{tabs.map(([k, l]) => <button key={k} role="tab" aria-selected={tab === k} className={tab === k ? "on" : ""} onClick={() => setTab(k)}>{l}</button>)}</div>
      <div className="pbody">
        {tab === "facts" && (f ? (<>
          <p className="hint">{result ? "Exactly what the agent and policy saw for this run." : "Facts that will be supplied to the agent."}</p>
          <KV k="Customer message" v={<>“{f.customer_message}”</>} />
          <KV k="Appointment" v={<>{f.appointment?.date ?? "—"} {f.appointment?.start_time ?? ""}{f.appointment?.end_time ? `–${f.appointment.end_time}` : ""} {badge(f.appointment?.status)}</>} />
          <KV k="Crew confirmation" v={badge(f.crew?.confirmation_status)} />
          <KV k="Available slots" v={f.available_slots?.length ? <ul className="plain">{f.available_slots.map((s: any, i: number) => <li key={i}>{slotTxt(s)}</li>)}</ul> : <span className="mute">None supplied</span>} />
          <KV k="Other jobs" v={f.other_jobs?.length ? <ul className="plain">{f.other_jobs.map((j: any, i: number) => <li key={i}>{j.job_id ?? "job"} {badge(j.status)}</li>)}</ul> : <span className="mute">None</span>} />
        </>) : <p className="mute">Select a use case.</p>)}

        {tab === "pipeline" && (ev ? (<>
          <p className="hint">AI proposes · the Decider judges · Python verifies · the system of record confirms.</p>
          {ev.pipeline.map((st, i) => (
            <div className={"step " + st.status} key={st.key + i}>
              <span className="sn">{i + 1}</span>
              <div><b>{st.name}</b><small>{st.detail || "—"}</small></div>
              <span className="sms">{st.status === "skipped" ? "skipped" : `${st.ms} ms`}</span>
            </div>))}
          {ev.judgment && <><div className="jhead"><span>Decider judgment</span></div>
            <div className="conf"><div style={{ width: `${Math.round(ev.judgment.confidence * 100)}%` }} className={ev.judgment.confidence >= 0.9 ? "hi" : "lo"} /></div>
            <small className="mute">{ev.judgment.next_action} · confidence {ev.judgment.confidence.toFixed(2)} (gate 0.90) · {ev.judgment.reason}</small></>}
          {ev.draft_request && <><div className="jhead"><span>Draft request (reviewer)</span></div><pre>{JSON.stringify(ev.draft_request, null, 2)}</pre></>}
          {ev.evidence_pack && <><div className="jhead"><span>Evidence pack (Python)</span></div><pre>{JSON.stringify(ev.evidence_pack, null, 2)}</pre></>}
        </>) : <p className="mute">{running ? "Running…" : "Run the scenario to see the pipeline."}</p>)}

        {tab === "policy" && (ev ? (<>
          <p className="hint">Deterministic rules applied to the first draft. {result?.acceptable ? "All passed." : "Blocked rules explain why."}</p>
          {ev.rules.map((r) => (
            <div className={"rule " + r.status} key={r.rule_id}>
              <div className="rule-h"><span className="rid">{r.rule_id.split("_")[0]}</span><b>{r.name}</b>
                <span className={"rs " + r.status}>{r.status === "passed" ? "Passed" : r.status === "blocked" ? "Blocked" : "Skipped"}</span></div>
              {r.reason && <p>{r.reason}</p>}
            </div>))}
        </>) : <p className="mute">{running ? "Running…" : "Run the scenario to see rule-by-rule results."}</p>)}

        {tab === "trace" && (ev ? (<>
          <KV k="Request ID" v={<code>{ev.request_id}</code>} />
          <KV k="Timestamp" v={<code>{ev.timestamp}</code>} />
          <KV k="Mode" v={ev.mode === "live" ? "Live agent (LLM)" : "Mock data"} />
          <KV k="Proposal source" v={<code>{ev.source}</code>} />
          <KV k="Model" v={<code>{ev.model_id ?? "— (no model call)"}</code>} />
          <KV k="Latency" v={<>{ev.latency_ms} ms</>} />
          {ev.error && <div className="notice bad"><b>Agent error</b><br />{ev.error}</div>}
          <div className="jhead"><span>Decision record</span><button className="mini" onClick={() => navigator.clipboard?.writeText(JSON.stringify(result, null, 2))}>Copy JSON</button></div>
          <pre>{JSON.stringify({ proposed: result!.proposed_decision, resolution: result!.resolution, findings: result!.findings.map((x) => x.rule_id), final: { action: result!.final_action, reply: result!.final_reply } }, null, 2)}</pre>
        </>) : <p className="mute">{running ? "Running…" : "Run the scenario to see the trace."}</p>)}

        {tab === "history" && (history.length ? (
          <table className="hist"><thead><tr><th>#</th><th>Case</th><th>Mode</th><th>Verdict</th><th>ms</th></tr></thead>
            <tbody>{history.map((h) => (
              <tr key={h.n}><td>{h.n}</td><td><b>{h.id}</b><small>{h.time}</small></td><td>{h.mode === "live" ? "Live" : "Mock"}</td>
                <td><span className={"rs " + (h.ok ? "passed" : "blocked")}>{h.ok ? "Approved" : "Blocked"}</span>{h.rules.length > 0 && <small>{h.rules.map((r) => r.split("_")[0]).join(", ")}</small>}</td><td>{h.ms}</td></tr>))}</tbody></table>
        ) : <p className="mute">No runs yet in this session.</p>)}
      </div>
    </section>
  );
}
