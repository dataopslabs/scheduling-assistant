import { useEffect, useState } from "react";

// Images live in the public GitHub repo and are referenced directly from there.
const RAW = "https://raw.githubusercontent.com/dataopslabs/scheduling-assistant/staging/docs/images/";
const REPO = "https://github.com/dataopslabs/scheduling-assistant/blob/staging/docs/images/";

export type Section = "problem" | "solution" | "design";
export const SECTIONS: Section[] = ["problem", "solution", "design"];

interface Content {
  label: string; file: string; title: string; summary: string; points: [string, string][];
  built: string[]; next: string[];
}

const CONTENT: Record<Section, Content> = {
  problem: {
    label: "Problem", file: "01-problem.webp",
    title: "When AI scheduling decisions cannot be trusted",
    summary: "An assistant can sound confident while making an incorrect scheduling decision. A plausible response is not necessarily a correct scheduling decision.",
    points: [
      ["Case A · Conflict", "A completed job is misread as an active conflict, so the assistant escalates or refuses to schedule."],
      ["Case B · Intent", "The customer will follow up later, but the assistant proposes booking a date anyway."],
      ["Case C · Availability", "The assistant confirms Saturday although the authoritative slot list only has Monday and Tuesday."],
      ["Case D · Confirmation", "The appointment is tentative and crew confirmation is unknown, yet attendance is promised."],
    ],
    built: ["Root cause 1: language-model judgment is mistaken for verified fact.", "Root cause 2: customer intent is not reliably distinguished from a booking request.", "Root cause 3: no deterministic final validation blocks unsupported promises."],
    next: [],
  },
  solution: {
    label: "Solution", file: "02-solution.webp",
    title: "Trust through separation of responsibilities",
    summary: "LLMs interpret and communicate. A Strands Decider evaluates intent. Python verifies facts and controls scheduling actions. AI proposes, the Decider judges, Python verifies, the system of record confirms.",
    points: [
      ["1 · Understand", "Request reviewer turns the message into a structured draft request. No write tools."],
      ["2 · Decide", "Typed judgment of intent and next action with a confidence score; below 0.9 goes to a human."],
      ["3 · Verify", "Python rules and tools fetch status, slots and crew confirmation and build an evidence pack."],
      ["4 · Draft", "A response writer uses only the evidence pack. It has no scheduling tools."],
      ["5 · Validate", "Final guard checks every date, slot, status and confirmation claim; one rewrite, then safe holding reply or human."],
    ],
    built: ["Strands agent on Amazon Bedrock proposes a reply and action.", "Python policy rules E1–E5 verify every claim against the facts.", "A blocked proposal is replaced by a safe alternative or escalation.", "Read-only: no code path can modify an appointment."],
    next: ["Separate request-reviewer and response-writer agents", "Strands Decider with the 0.9 confidence gate", "Evidence pack from the scheduling API and appointment database", "Run in Amazon Bedrock AgentCore Runtime", "One-rewrite loop in the final guard"],
  },
  design: {
    label: "Design", file: "03-design.webp",
    title: "Code structure and responsibilities",
    summary: "A modular Python implementation that separates agent reasoning, typed decisions, business rules, external tools and validation. Models interpret language; code enforces invariants; tests prove both rejection and acceptance paths.",
    points: [
      ["API and schemas", "main.py orchestrates; schemas.py validates structured input and output; config.py loads settings."],
      ["LLM agents", "Request reviewer and response writer understand and communicate, with no booking-write access."],
      ["Decider adapter", "Typed questions about intent and next action; low confidence escalates rather than books."],
      ["Rules and tools", "Availability, conflict and confirmation rules; the scheduling API performs authorized writes only."],
      ["Evidence and final guard", "Structured evidence pack; unsupported dates, slots, statuses or crew claims are rejected."],
      ["Automated tests", "Each rule has a rejecting and an accepting test, plus regression tests for every case."],
    ],
    built: ["FastAPI app on Lambda behind API Gateway (api/, services/, config.py, schemas.py).", "policy.py with rule functions E1–E5 and per-rule results.", "services/agent.py (Strands + Bedrock) and services/decision.py (propose → validate → respond).", "68 automated tests, including 30 synthetic datasets."],
    next: ["Split policies/ into availability, conflict and confirmation modules", "evidence_builder and scheduling_api tool layer", "Typed decider_client with confidence"],
  },
};

interface Props { section: Section; onSection: (s: Section) => void; onOpenLab: () => void }

export default function AboutPage({ section, onSection, onOpenLab }: Props) {
  const c = CONTENT[section];
  const idx = SECTIONS.indexOf(section);
  const [zoom, setZoom] = useState(false);
  const [failed, setFailed] = useState(false);
  useEffect(() => { setFailed(false); setZoom(false); }, [section]);
  useEffect(() => {
    if (!zoom) return;
    const h = (e: KeyboardEvent) => e.key === "Escape" && setZoom(false);
    window.addEventListener("keydown", h); return () => window.removeEventListener("keydown", h);
  }, [zoom]);
  const src = RAW + c.file;

  return (
    <main className="about">
      <div className="about-head">
        <div>
          <div className="crumb">About the project</div>
          <h1>{c.title}</h1>
          <p className="lede">{c.summary}</p>
        </div>
        <button className="run" onClick={onOpenLab}>Open the test lab →</button>
      </div>

      <div className="steps" role="tablist" aria-label="About sections">
        {SECTIONS.map((s, i) => (
          <button key={s} role="tab" aria-selected={s === section} className={s === section ? "on" : ""} onClick={() => onSection(s)}>
            <span className="num">{i + 1}</span>{CONTENT[s].label}
          </button>))}
      </div>

      <div className="about-grid">
        <figure className="figure">
          {failed ? (
            <div className="img-fail">Could not load the image from GitHub.<br /><a href={REPO + c.file} target="_blank" rel="noreferrer">Open it on GitHub</a></div>
          ) : (
            <button className="imgbtn" onClick={() => setZoom(true)} aria-label={`Enlarge ${c.label} diagram`}>
              <img src={src} alt={`${c.label}: ${c.title}`} onError={() => setFailed(true)} />
              <span className="zoomhint">Click to enlarge</span>
            </button>)}
          <figcaption>Source: <a href={REPO + c.file} target="_blank" rel="noreferrer">docs/images/{c.file}</a> · GitHub</figcaption>
        </figure>

        <aside className="side">
          <div className="sidecard">
            <h3>{section === "problem" ? "The four failure cases" : section === "solution" ? "Five-step flow" : "Layers"}</h3>
            <ul className="pts">{c.points.map(([h, t]) => <li key={h}><b>{h}</b><span>{t}</span></li>)}</ul>
          </div>
          <div className="sidecard built">
            <h3>{section === "problem" ? "Common root causes" : "In this build"}</h3>
            <ul>{c.built.map((t) => <li key={t}>{t}</li>)}</ul>
          </div>
          {c.next.length > 0 && <div className="sidecard next"><h3>On the roadmap (from the target design)</h3><ul>{c.next.map((t) => <li key={t}>{t}</li>)}</ul></div>}
        </aside>
      </div>

      <div className="pager">
        <button disabled={idx === 0} onClick={() => onSection(SECTIONS[idx - 1])}>← {idx > 0 ? CONTENT[SECTIONS[idx - 1]].label : ""}</button>
        <button disabled={idx === SECTIONS.length - 1} onClick={() => onSection(SECTIONS[idx + 1])}>{idx < SECTIONS.length - 1 ? CONTENT[SECTIONS[idx + 1]].label : ""} →</button>
      </div>

      {zoom && !failed && (
        <div className="lightbox" onClick={() => setZoom(false)} role="dialog" aria-label="Enlarged diagram">
          <img src={src} alt={c.title} />
          <button className="lbclose" onClick={() => setZoom(false)}>Close ✕</button>
        </div>)}
    </main>
  );
}
