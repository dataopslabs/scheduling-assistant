import { useMemo, useState } from "react";
import type { Case, Mode } from "../types";

export const CATEGORY: Record<string, string> = {
  conflict_accuracy: "Conflict accuracy", customer_intent: "Customer intent", availability_integrity: "Availability",
  confirmation_integrity: "Crew confirmation", data_uncertainty_extension: "Missing data",
};
export interface CustomForm { message: string; appt: string; crew: string; slots: string; action: string; reply: string }
export const DEFAULT_CUSTOM: CustomForm = {
  message: "Can you come this Saturday?", appt: "confirmed", crew: "unknown", slots: "Monday 10:00, Tuesday 14:00",
  action: "reply", reply: "Yes, we can come this Saturday.",
};
const APPT = ["confirmed", "tentative", "pending", "none"];
const CREW = ["confirmed", "unknown", "pending", "unconfirmed"];

interface Props {
  cases: Case[]; datasets: Case[]; selected: string; onSelect: (id: string) => void; mode: Mode;
  custom: CustomForm; onCustom: (c: CustomForm) => void; loadError: boolean;
}

export default function UseCasePanel({ cases, datasets, selected, onSelect, mode, custom, onCustom, loadError }: Props) {
  const [q, setQ] = useState("");
  const groups = useMemo(() => {
    const f = q.trim().toLowerCase();
    const list = cases.filter((c) => !f || (c.case_id + c.customer_message + (CATEGORY[c.category] || "")).toLowerCase().includes(f));
    const m = new Map<string, Case[]>();
    list.forEach((c) => m.set(c.category, [...(m.get(c.category) || []), c]));
    return [...m.entries()];
  }, [cases, q]);
  const set = (k: keyof CustomForm) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => onCustom({ ...custom, [k]: e.target.value });

  return (
    <section className="panel" aria-label="Use cases">
      <div className="phead"><div><h2>Use cases</h2><p>{cases.length} synthetic scenarios</p></div></div>
      <div className="pbody">
        <input className="search" placeholder="Search scenarios…" value={q} onChange={(e) => setQ(e.target.value)} />
        {loadError && <div className="notice bad">Could not load scenarios. Is the API reachable?</div>}
        {groups.map(([cat, items]) => (
          <div key={cat} className="group">
            <h3>{CATEGORY[cat] || cat}</h3>
            {items.map((c) => (
              <button key={c.case_id} className={"uc" + (selected === c.case_id ? " on" : "")} onClick={() => onSelect(c.case_id)}>
                <div className="uc-top"><b>{c.case_id}</b>
                  <span className="tag">{datasets.filter((d) => d.use_case === c.case_id).length} datasets</span>
                  {mode === "mock" && c.expected && <span className={"tag " + (c.expected.acceptable ? "ok" : "warn")}>{c.expected.acceptable ? "Valid reply" : "Unsafe reply"}</span>}
                </div>
                <p>“{c.customer_message}”</p>
              </button>
            ))}
          </div>
        ))}
        <div className="group">
          <h3>Your own</h3>
          <button className={"uc" + (selected === "custom" ? " on" : "")} onClick={() => onSelect("custom")}>
            <div className="uc-top"><b>Custom scenario</b><span className="tag">Build</span></div>
            <p>Write a customer message and set the facts.</p>
          </button>
          {selected === "custom" && (
            <div className="form">
              <label>Customer message<textarea rows={2} value={custom.message} onChange={set("message")} /></label>
              <div className="two">
                <label>Appointment<select value={custom.appt} onChange={set("appt")}>{APPT.map((x) => <option key={x}>{x}</option>)}</select></label>
                <label>Crew<select value={custom.crew} onChange={set("crew")}>{CREW.map((x) => <option key={x}>{x}</option>)}</select></label>
              </div>
              <label>Available slots <small>(Day HH:MM, comma separated)</small><input value={custom.slots} onChange={set("slots")} /></label>
              {mode === "mock" && (<>
                <label>Simulated model reply <small>(what the agent “said”)</small><textarea rows={2} value={custom.reply} onChange={set("reply")} /></label>
                <label>Simulated action<select value={custom.action} onChange={set("action")}><option>reply</option><option>wait</option><option>escalate</option></select></label>
              </>)}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
