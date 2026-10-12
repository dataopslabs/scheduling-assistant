import type { BatchResult, Case, Decision, Mode } from "../types";

interface Props { mode: Mode; customer: string; running: boolean; result: Decision | null; error: string; onRun: () => void; model?: string; scenario: Case | null; custom: boolean;
  variants: Case[]; variantId: string | null; onVariant: (id: string | null) => void; onRunAll: () => void; batch: BatchResult | null; batchRunning: boolean; onInspect: (id: string) => void }

const ACTION: Record<string, string> = { reply: "Reply", wait: "Wait", escalate: "Escalate to human" };

export default function ResponsePanel({ mode, customer, running, result, error, onRun, model, scenario, custom, variants, variantId, onVariant, onRunAll, batch, batchRunning, onInspect }: Props) {
  const live = mode === "live";
  const blocked = result && !result.acceptable;
  return (
    <section className="panel mid" aria-label="Response">
      <div className="phead">
        <div><h2>Response</h2><p>{live ? `Live agent · ${model ?? "Bedrock"}` : "Mock data · simulated model output"}</p></div>
        <button className="run" onClick={onRun} disabled={running}>
          {running ? <><span className="spin" />Running…</> : live ? "Run live agent" : "Run mock test"}
        </button>
      </div>
      {!custom && variants.length > 0 && (
        <div className="dsbar">
          <span>Dataset</span>
          <button className={!variantId ? "on" : ""} onClick={() => onVariant(null)}>Original</button>
          {variants.map((v) => <button key={v.case_id} className={variantId === v.case_id ? "on" : ""} title={v.title ?? ""} onClick={() => onVariant(v.case_id)}>#{v.variant}</button>)}
          <button className="all" onClick={onRunAll} disabled={batchRunning || running}>{batchRunning ? "Running…" : `Run all ${variants.length} datasets`}</button>
        </div>
      )}
      {scenario?.title && !custom && <div className="dstitle">Dataset {scenario.case_id}: {scenario.title}</div>}
      <div className="pbody chat">
        {error && <div className="notice bad">{error}</div>}

        <div className="turn">
          <div className="who">Customer</div>
          <div className="bubble cust">{customer || "Select a use case"}</div>
        </div>

        {batchRunning && <div className="notice">Sending {variants.length} payloads to the {live ? "LLM" : "mock agent"}…</div>}
        {batch && (
          <div className="batch">
            <div className="bsum"><b>{batch.total} datasets</b><span className="rs passed">{batch.approved} approved</span><span className="rs blocked">{batch.blocked} blocked</span><span className="mute">{batch.mode === "live" ? "live LLM" : "mock replay"}</span></div>
            <table><thead><tr><th>Dataset</th><th>Customer</th><th>{live ? "LLM proposal" : "Simulated reply"}</th><th>Policy</th></tr></thead>
              <tbody>{batch.items.map((i) => (
                <tr key={i.case_id} onClick={() => onInspect(i.case_id)} className={variantId === i.case_id ? "sel" : ""}>
                  <td><b>{i.case_id}</b><small>{i.title}</small></td><td>{i.customer_message}</td><td>{i.decision.proposed_decision.reply}</td>
                  <td><span className={"rs " + (i.decision.acceptable ? "passed" : "blocked")}>{i.decision.acceptable ? "Approved" : "Blocked"}</span>{i.decision.findings.length > 0 && <small>{i.decision.findings.map((f) => f.rule_id.split("_")[0]).join(", ")}</small>}</td></tr>))}</tbody></table>
            <p className="mute">Click a row to inspect its full response and evidence.</p>
          </div>)}

        {!result && !running && !batch && !batchRunning && (
          <div className="empty">
            <div className="empty-ic">▶</div>
            <b>{live ? "Ask the live agent" : "Replay the simulated model output"}</b>
            <p>{live
              ? "The agent sees only the facts in the Evidence panel. Its proposal is checked by the policy before a reply is released."
              : custom ? "Edit the simulated reply on the left, then run to see how the policy responds."
                : scenario?.proposed_decision ? "This scenario carries a recorded model reply. Run it to see whether the policy approves or blocks it." : "Run to simulate."}</p>
          </div>
        )}

        {running && <div className="turn"><div className="who">Agent</div><div className="bubble skel"><i /><i /><i /></div></div>}

        {result && (<>
          <div className="turn">
            <div className="who">{result.evidence.source === "bedrock" ? "Agent proposal" : result.evidence.source === "bedrock-fallback" ? "Agent proposal (fallback)" : "Simulated model output"}
              <span className="pillgrey">{ACTION[result.proposed_decision.action]}</span></div>
            <div className="bubble prop">{result.proposed_decision.reply}</div>
          </div>

          <div className={"verdict " + (result.acceptable ? "ok" : "bad")}>
            <div className="vic">{result.acceptable ? "✓" : "!"}</div>
            <div>
              <b>{result.acceptable ? "Approved by policy" : "Blocked by policy"}</b>
              <p>{result.acceptable ? "Every claim in the proposal is supported by the scheduling facts." : "The proposal was replaced with a safe alternative."}</p>
              {result.findings.map((f) => <div className="finding" key={f.rule_id}><span className="rid">{f.rule_id.split("_")[0]}</span>{f.reason}</div>)}
            </div>
          </div>

          <div className="turn right">
            <div className="who">Sent to customer<span className="pillgrey">{ACTION[result.final_action]}</span></div>
            <div className={"bubble final" + (blocked ? " replaced" : "")}>{result.final_reply}</div>
            <div className="foot">{result.note}</div>
          </div>
        </>)}
      </div>
    </section>
  );
}
