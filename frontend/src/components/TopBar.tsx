import type { AppConfig, Mode } from "../types";

interface Props { mode: Mode; onMode: (m: Mode) => void; config: AppConfig | null; api: "up" | "down" | "checking" }

export default function TopBar({ mode, onMode, config, api }: Props) {
  return (
    <header className="topbar">
      <div className="brand">
        <div className="logo" aria-hidden>S</div>
        <div><b>Scheduling Reliability Lab</b><span>AI agent proposes · policy decides</span></div>
      </div>
      <div className="seg" role="tablist" aria-label="Test mode">
        <button role="tab" aria-selected={mode === "mock"} className={mode === "mock" ? "on" : ""} onClick={() => onMode("mock")}>
          <b>Test Mock Data</b><small>Replay simulated model outputs</small>
        </button>
        <button role="tab" aria-selected={mode === "live"} className={mode === "live" ? "on" : ""} onClick={() => onMode("live")}>
          <b>Test Live Agent (LLM)</b><small>Strands agent · Amazon Bedrock</small>
        </button>
      </div>
      <div className="meta">
        <span className="chip" title="Bedrock model used by the live agent">{config?.model_id ?? "model: —"}</span>
        <span className={"status " + api}><i />{api === "up" ? "API online" : api === "down" ? "API offline" : "Connecting…"}</span>
        <a className="link" href="/docs/index.html">Case study</a>
      </div>
    </header>
  );
}
