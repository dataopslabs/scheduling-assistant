import type { AppConfig, Case, Decision, Mode } from "./types";
export const API = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(API + path, init);
  if (!r.ok) {
    let detail = "";
    try { detail = JSON.stringify((await r.json()).detail ?? ""); } catch { /* ignore */ }
    throw new Error(`HTTP ${r.status}${detail ? " " + detail.slice(0, 160) : ""}`);
  }
  return r.json();
}
export const getCases = () => req<Case[]>("/api/cases");
export const getConfig = () => req<AppConfig>("/api/config");
export const getHealth = () => req<{ status: string }>("/health");
export const decide = (mode: Mode, c: Case) =>
  req<Decision>("/api/decide", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ mode, case: c }) });
