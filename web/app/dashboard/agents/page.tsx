"use client";
import { useState, useEffect, useCallback } from "react";

const TRACER_URL = process.env.NEXT_PUBLIC_AGENT_TRACER_URL ?? "https://agent-tracer.vercel.app";

// ── Types matching the API ─────────────────────────────────────────────────
interface ApiRun {
  run_id: string;
  agent_id: string;
  started_at_ms: number;
  last_event_at_ms: number;
  duration_ms: number;
  event_count: number;
  pii_events: number;
  human_checkpoints: number;
}

interface ApiEvent {
  id: string;
  seq: number;
  event_type: string;
  timestamp_ms: number;
  data: Record<string, unknown>;
  pii_types: string[];
  pii_redacted: boolean;
  human_approved: boolean | null;
  record_hash: string;
}

// ── Display helpers ────────────────────────────────────────────────────────
const PII_COLOR: Record<string, string> = {
  AADHAAR_IN: "#1C6EF2", PAN_IN: "#9333ea", UPI_IN: "#d97706",
  MOBILE_IN: "#16a34a",  IFSC_IN: "#0891b2", BANK_ACCOUNT_IN: "#dc2626",
  GST_IN: "#7c3aed",     EMAIL: "#ea580c",
};

function relativeTime(ms: number) {
  const diff = Date.now() - ms;
  if (diff < 60_000) return `${Math.round(diff / 1000)}s ago`;
  if (diff < 3_600_000) return `${Math.round(diff / 60_000)}m ago`;
  return `${Math.round(diff / 3_600_000)}h ago`;
}

function toolLabel(event: ApiEvent): string {
  const d = event.data;
  if (event.event_type === "llm_call") return `llm.${String(d.model ?? "chat").split("/").pop()}`;
  if (event.event_type === "tool_call") return String(d.tool ?? "tool_call");
  if (event.event_type === "human_checkpoint") return "human_review.checkpoint";
  if (event.event_type === "decision") return "agent.decision";
  if (event.event_type === "data_access") return `data_access.${d.source ?? ""}`;
  return event.event_type;
}

function inputSummary(event: ApiEvent): string {
  const d = event.data;
  if (event.event_type === "llm_call") return String(d.prompt ?? "").slice(0, 80) + (String(d.prompt ?? "").length > 80 ? "…" : "");
  if (event.event_type === "tool_call") return `tool=${d.tool}`;
  if (event.event_type === "human_checkpoint") return String(d.question ?? "");
  if (event.event_type === "decision") return String(d.reason ?? "");
  if (event.event_type === "data_access") return `fields=${JSON.stringify(d.fields_accessed ?? [])}`;
  return JSON.stringify(d).slice(0, 80);
}

function outputSummary(event: ApiEvent): string {
  const d = event.data;
  if (event.event_type === "llm_call") return String(d.response ?? "").slice(0, 60) + (String(d.response ?? "").length > 60 ? "…" : "");
  if (event.event_type === "tool_call") return JSON.stringify(d.output ?? {}).slice(0, 60);
  if (event.event_type === "human_checkpoint") return event.human_approved ? "Approved" : "Rejected";
  if (event.event_type === "decision") return String(d.outcome ?? "");
  return "";
}

// ── Seed data (posts demo events to give the page something to show) ───────
async function seedDemoRun() {
  const runId = crypto.randomUUID();
  const events = [
    { agent_id: "loan-processor-v3", event_type: "data_access", data: { source: "crm", fields_accessed: ["name", "income"], purpose: "loan_processing" }, pii_types: [] },
    { agent_id: "loan-processor-v3", event_type: "tool_call", data: { tool: "pii_shield.detect", input: { text: "Aadhaar 9876 5432 1098" }, output: { redacted: "[AADHAAR_IN]" } }, pii_types: ["AADHAAR_IN"], pii_redacted: true },
    { agent_id: "loan-processor-v3", event_type: "llm_call", data: { provider: "openai", model: "gpt-4o", prompt: "Assess eligibility for [AADHAAR_IN] applicant", response: "Applicant appears eligible. Score: 72/100." }, pii_types: [] },
    { agent_id: "loan-processor-v3", event_type: "decision", data: { reason: "Score above threshold (70)", outcome: "approve", confidence: 0.87 }, pii_types: [] },
    { agent_id: "loan-processor-v3", event_type: "human_checkpoint", data: { question: "Approve ₹5L loan for this applicant?", reviewer_id: "anand.k", notes: "Looks good" }, pii_types: [], human_approved: true },
  ];
  for (const ev of events) {
    await fetch(`${TRACER_URL}/runs/${runId}/events`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(ev),
    });
  }
  return runId;
}

// ── Component ──────────────────────────────────────────────────────────────
export default function AgentTracerPage() {
  const [runs, setRuns] = useState<ApiRun[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [events, setEvents] = useState<ApiEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [eventsLoading, setEventsLoading] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [error, setError] = useState("");

  const fetchRuns = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${TRACER_URL}/runs`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setRuns(data.runs ?? []);
      setError("");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to connect");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchRuns(); }, [fetchRuns]);

  async function selectRun(runId: string) {
    setSelectedId(runId);
    setEventsLoading(true);
    try {
      const res = await fetch(`${TRACER_URL}/runs/${runId}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setEvents(data.events ?? []);
    } catch {
      setEvents([]);
    } finally {
      setEventsLoading(false);
    }
  }

  async function seed() {
    setSeeding(true);
    try {
      await seedDemoRun();
      await fetchRuns();
    } finally {
      setSeeding(false);
    }
  }

  const selectedRun = runs.find(r => r.run_id === selectedId);

  return (
    <div style={{ padding: "36px 40px", maxWidth: 1100, margin: "0 auto" }}>
      <div style={{ marginBottom: 32, display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 700, margin: "0 0 6px", fontFamily: "Space Grotesk, sans-serif", color: "#0D0D0B" }}>
            Agent Tracer
          </h1>
          <p style={{ margin: 0, fontSize: 14, color: "#71716B" }}>
            Immutable, hash-chained audit trail of every agent decision
          </p>
        </div>
        <button onClick={seed} disabled={seeding} style={{
          padding: "8px 18px", borderRadius: 8, border: "1px solid #E8E8E4",
          background: "white", color: "#0D0D0B", fontSize: 13, fontWeight: 500,
          cursor: seeding ? "wait" : "pointer", fontFamily: "inherit", opacity: seeding ? 0.6 : 1,
        }}>
          {seeding ? "Seeding…" : "+ Seed demo run"}
        </button>
      </div>

      {/* Stats */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14, marginBottom: 28 }}>
        {[
          { label: "Total runs",        value: runs.length.toString() },
          { label: "PII events",        value: runs.reduce((s, r) => s + r.pii_events, 0).toString() },
          { label: "Human checkpoints", value: runs.reduce((s, r) => s + r.human_checkpoints, 0).toString() },
          { label: "Avg duration",      value: runs.length ? `${Math.round(runs.reduce((s, r) => s + r.duration_ms, 0) / runs.length / 1000)}s` : "—" },
        ].map(s => (
          <div key={s.label} style={{ background: "white", borderRadius: 10, padding: "16px 18px", border: "1px solid #E8E8E4" }}>
            <div style={{ fontSize: 11, color: "#71716B", marginBottom: 6, fontWeight: 500, textTransform: "uppercase", letterSpacing: "0.05em" }}>{s.label}</div>
            <div style={{ fontSize: 22, fontWeight: 700, fontFamily: "Space Grotesk, sans-serif", color: "#0D0D0B" }}>{s.value}</div>
          </div>
        ))}
      </div>

      {error && (
        <div style={{ marginBottom: 20, padding: "12px 16px", borderRadius: 8, background: "#FFF0F0", border: "1px solid #FDD", fontSize: 13, color: "#dc2626" }}>
          Could not reach Agent Tracer API ({error}). Add <code>NEXT_PUBLIC_AGENT_TRACER_URL</code> env var if using a custom deployment.
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: selectedRun ? "320px 1fr" : "1fr", gap: 20 }}>
        {/* Runs list */}
        <div style={{ background: "white", borderRadius: 12, border: "1px solid #E8E8E4", overflow: "hidden", alignSelf: "start" }}>
          <div style={{ padding: "16px 20px", borderBottom: "1px solid #F0F0EC" }}>
            <span style={{ fontSize: 14, fontWeight: 600, color: "#0D0D0B" }}>Agent Runs</span>
          </div>

          {loading ? (
            <div style={{ padding: "32px 20px", textAlign: "center", color: "#A8A8A2", fontSize: 13 }}>Loading…</div>
          ) : runs.length === 0 ? (
            <div style={{ padding: "32px 20px", textAlign: "center" }}>
              <div style={{ fontSize: 13, color: "#71716B", marginBottom: 12 }}>No runs recorded yet.</div>
              <div style={{ fontSize: 12, color: "#A8A8A2" }}>
                Use the SDK to start tracing agents, or click<br />"Seed demo run" to see a sample.
              </div>
            </div>
          ) : (
            runs.map(run => (
              <div
                key={run.run_id}
                onClick={() => selectRun(run.run_id)}
                style={{
                  padding: "14px 20px", borderBottom: "1px solid #F5F5F3", cursor: "pointer",
                  background: selectedId === run.run_id ? "#F5F8FF" : "white",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 6 }}>
                  <span style={{ fontSize: 13, fontWeight: 500, color: "#0D0D0B", fontFamily: "JetBrains Mono, monospace" }}>{run.agent_id}</span>
                  <span style={{ fontSize: 11, color: "#A8A8A2" }}>{relativeTime(run.started_at_ms)}</span>
                </div>
                <div style={{ display: "flex", gap: 12, fontSize: 11, color: "#A8A8A2" }}>
                  <span>{run.event_count} events</span>
                  <span>{run.pii_events} PII</span>
                  <span>{run.human_checkpoints} human</span>
                  <span>{Math.round(run.duration_ms / 1000)}s</span>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Timeline */}
        {selectedRun && (
          <div style={{ background: "white", borderRadius: 12, border: "1px solid #E8E8E4", overflow: "hidden" }}>
            <div style={{ padding: "16px 22px", borderBottom: "1px solid #F0F0EC", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div>
                <div style={{ fontSize: 14, fontWeight: 600, color: "#0D0D0B", marginBottom: 2 }}>{selectedRun.agent_id}</div>
                <div style={{ fontSize: 11, color: "#A8A8A2", fontFamily: "JetBrains Mono, monospace" }}>{selectedRun.run_id}</div>
              </div>
              <button onClick={() => { setSelectedId(null); setEvents([]); }} style={{
                background: "none", border: "none", cursor: "pointer", color: "#71716B", fontSize: 20, lineHeight: 1, padding: 4,
              }}>×</button>
            </div>

            <div style={{ padding: "20px 22px" }}>
              {eventsLoading ? (
                <div style={{ textAlign: "center", color: "#A8A8A2", fontSize: 13, padding: "24px 0" }}>Loading events…</div>
              ) : events.length === 0 ? (
                <div style={{ textAlign: "center", color: "#A8A8A2", fontSize: 13, padding: "24px 0" }}>No events found for this run.</div>
              ) : (
                events.map((ev, i) => (
                  <div key={ev.id} style={{ display: "flex", gap: 16, marginBottom: 0 }}>
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", width: 28 }}>
                      <div style={{
                        width: 28, height: 28, borderRadius: "50%", flexShrink: 0,
                        display: "flex", alignItems: "center", justifyContent: "center",
                        background: ev.pii_types.length > 0 ? "#FFF0F0" : ev.human_approved !== null ? "#EEF4FF" : "#F5F5F3",
                        border: `1.5px solid ${ev.pii_types.length > 0 ? "#dc2626" : ev.human_approved !== null ? "#1C6EF2" : "#E8E8E4"}`,
                        fontSize: 11, fontWeight: 700,
                        color: ev.pii_types.length > 0 ? "#dc2626" : ev.human_approved !== null ? "#1C6EF2" : "#71716B",
                      }}>{ev.seq}</div>
                      {i < events.length - 1 && (
                        <div style={{ width: 1, flex: 1, minHeight: 20, background: "#E8E8E4", margin: "4px 0" }} />
                      )}
                    </div>
                    <div style={{ flex: 1, paddingBottom: i < events.length - 1 ? 16 : 0 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                        <span style={{ fontSize: 13, fontWeight: 600, color: "#0D0D0B", fontFamily: "JetBrains Mono, monospace" }}>{toolLabel(ev)}</span>
                        {ev.human_approved !== null && (
                          <span style={{ fontSize: 10, fontWeight: 700, padding: "1px 6px", borderRadius: 4, background: "#EEF4FF", color: "#1C6EF2" }}>HUMAN</span>
                        )}
                        {ev.pii_redacted && (
                          <span style={{ fontSize: 10, fontWeight: 700, padding: "1px 6px", borderRadius: 4, background: "#FFF0F0", color: "#dc2626" }}>REDACTED</span>
                        )}
                      </div>
                      <div style={{ fontSize: 12, color: "#71716B", marginBottom: ev.pii_types.length ? 6 : 0 }}>{inputSummary(ev)}</div>
                      {ev.pii_types.length > 0 && (
                        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 4 }}>
                          {ev.pii_types.map(t => (
                            <span key={t} style={{
                              fontSize: 10, fontWeight: 600, padding: "2px 6px", borderRadius: 4,
                              background: `${PII_COLOR[t] ?? "#71716B"}18`, color: PII_COLOR[t] ?? "#71716B",
                            }}>{t}</span>
                          ))}
                        </div>
                      )}
                      {outputSummary(ev) && (
                        <div style={{ fontSize: 12, color: "#A8A8A2", fontStyle: "italic" }}>→ {outputSummary(ev)}</div>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
