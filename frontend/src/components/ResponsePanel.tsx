import type { Case, Decision, Mode } from "../types";

interface Props { mode: Mode; customer: string; running: boolean; result: Decision | null; error: string; onRun: () => void; model?: string; scenario: Case | null; custom: boolean }

const ACTION: Record<string, string> = { reply: "Reply", wait: "Wait", escalate: "Escalate to human" };

export default function ResponsePanel({ mode, customer, running, result, error, onRun, model, scenario, custom }: Props) {
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
      <div className="pbody chat">
        {error && <div className="notice bad">{error}</div>}

        <div className="turn">
          <div className="who">Customer</div>
          <div className="bubble cust">{customer || "Select a use case"}</div>
        </div>

        {!result && !running && (
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
