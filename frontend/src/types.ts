export type Mode = "mock" | "live";
export type Action = "reply" | "wait" | "escalate";
export interface Slot { date?: string; day?: string; start_time?: string; time?: string }
export interface Case {
  case_id: string; use_case?: string | null; variant?: number | null; title?: string | null; category: string; customer_message: string;
  appointment: { date?: string | null; start_time?: string | null; end_time?: string | null; status?: string | null };
  crew: { confirmation_status?: string | null };
  available_slots: Slot[]; other_jobs: { job_id?: string; status?: string }[];
  proposed_decision?: { action: Action; reply: string } | null;
  expected?: { acceptable: boolean; rule: string | null } | null;
}
export interface RuleResult { rule_id: string; name: string; status: "passed" | "blocked" | "skipped"; reason?: string | null }
export interface Decision {
  case_id: string; mode: Mode; acceptable: boolean; final_action: Action; final_reply: string; note: string;
  proposed_decision: { action: Action; reply: string };
  findings: { rule_id: string; reason: string; safer_alternative: string }[];
  evidence: { request_id: string; timestamp: string; latency_ms: number; mode: Mode; source: string; model_id?: string | null; facts: Record<string, any>; rules: RuleResult[]; error?: string | null };
}
export interface HistoryRow { n: number; time: string; id: string; mode: Mode; source: string; proposed: Action; ok: boolean; rules: string[]; final: Action; ms: number }
export interface AppConfig { model_id: string; region?: string | null; version: string }
export interface BatchItem { case_id: string; title?: string | null; customer_message: string; expected_acceptable?: boolean | null; decision: Decision }
export interface BatchResult { mode: Mode; total: number; approved: number; blocked: number; items: BatchItem[] }
