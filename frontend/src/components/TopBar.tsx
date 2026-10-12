import type { AppConfig, Mode } from "../types";

interface Props { mode: Mode; onMode: (m: Mode) => void; config: AppConfig | null; api: "up" | "down" | "checking"; page: "lab" | "about"; onPage: (p: "lab" | "about") => void }

export default function TopBar({ mode, onMode, config, api, page, onPage }: Props) {
  return (
    <header className="topbar">
      <div className="brand">
        <div className="logo" aria-hidden>S</div>
        <div><b>Scheduling Reliability Lab</b><span>AI agent proposes · policy decides</span></div>
      </div>
      <nav className="nav" aria-label="Pages">
        <button className={page === "about" ? "on" : ""} onClick={() => onPage("about")}>About the project</button>
        <button className={page === "lab" ? "on" : ""} onClick={() => onPage("lab")}>Test lab</button>
      </nav>
      {page === "lab" ? <div className="seg" role="tablist" aria-label="Test mode">
        <button role="tab" aria-selected={mode === "mock"} className={mode === "mock" ? "on" : ""} onClick={() => onMode("mock")}>
          <b>Test Mock Data</b><small>Replay simulated model outputs</small>
        </button>
        <button role="tab" aria-selected={mode === "live"} className={mode === "live" ? "on" : ""} onClick={() => onMode("live")}>
          <b>Test Live Agent (LLM)</b><small>Strands agent · Amazon Bedrock</small>
        </button>
      </div> : <div className="seg-spacer" />}
      <div className="meta">
        <span className="chip" title="Bedrock model used by the live agent">{config?.model_id ?? "model: —"}</span>
        <span className={"status " + api}><i />{api === "up" ? "API online" : api === "down" ? "API offline" : "Connecting…"}</span>
      </div>
    </header>
  );
}
