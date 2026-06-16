"use client";
import { useState } from "react";

const COMPLIANCE_URL = process.env.NEXT_PUBLIC_COMPLIANCE_URL ?? "https://compliance-engine-18cdqy9ud-koushik-narendars-projects.vercel.app";

interface TelemetryInput {
  org_id: string;
  period_start: string;
  period_end: string;
  agent_runs: number;
  pii_detections: number;
  consents_collected: number;
  consents_withdrawn: number;
  human_reviews: number;
  purpose_list: string[];
  data_categories: string[];
}

const DEFAULT_TELEMETRY: TelemetryInput = {
  org_id: "acme-fintech",
  period_start: "2026-04-01",
  period_end: "2026-06-30",
  agent_runs: 2840,
  pii_detections: 4120,
  consents_collected: 8950,
  consents_withdrawn: 142,
  human_reviews: 310,
  purpose_list: ["loan_processing", "kyc_verification", "fraud_detection"],
  data_categories: ["AADHAAR_IN", "PAN_IN", "MOBILE_IN", "BANK_ACCOUNT_IN"],
};

const PAST_REPORTS = [
  { id: "rpt_a1b2", type: "DPDP DPIA",        score: 87, date: "2026-06-01", period: "Q1 FY26" },
  { id: "rpt_c3d4", type: "RBI FREE",          score: 79, date: "2026-05-15", period: "Q1 FY26" },
  { id: "rpt_e5f6", type: "DPDP DPIA",        score: 81, date: "2026-03-01", period: "Q4 FY25" },
  { id: "rpt_g7h8", type: "RBI FREE",          score: 72, date: "2026-02-14", period: "Q4 FY25" },
];

function scoreColor(score: number) {
  if (score >= 80) return "#16a34a";
  if (score >= 60) return "#d97706";
  return "#dc2626";
}

function ScoreBar({ score }: { score: number }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
      <div style={{ flex: 1, height: 6, background: "#F0F0EC", borderRadius: 3, overflow: "hidden" }}>
        <div style={{ width: `${score}%`, height: "100%", background: scoreColor(score), borderRadius: 3 }} />
      </div>
      <span style={{ fontSize: 13, fontWeight: 700, color: scoreColor(score), minWidth: 36 }}>{score}/100</span>
    </div>
  );
}

export default function ReportsPage() {
  const [generating, setGenerating] = useState<"dpia" | "rbi" | null>(null);
  const [generated, setGenerated] = useState<{ id: string; type: string; score: number; htmlUrl?: string } | null>(null);
  const [error, setError] = useState("");
  const [tel, setTel] = useState(DEFAULT_TELEMETRY);

  async function generate(type: "dpia" | "rbi") {
    setGenerating(type);
    setError("");
    setGenerated(null);
    const endpoint = type === "dpia" ? "/report/dpdp-dpia" : "/report/rbi-free";
    const body = type === "dpia"
      ? { org_id: tel.org_id, period_start: tel.period_start, period_end: tel.period_end,
          telemetry: { agent_runs: tel.agent_runs, pii_detections: tel.pii_detections,
            consents_collected: tel.consents_collected, consents_withdrawn: tel.consents_withdrawn,
            human_reviews: tel.human_reviews, purpose_list: tel.purpose_list, data_categories: tel.data_categories } }
      : { org_id: tel.org_id, period_start: tel.period_start, period_end: tel.period_end,
          telemetry: { agent_runs: tel.agent_runs, human_reviews: tel.human_reviews,
            pii_detections: tel.pii_detections, consents_collected: tel.consents_collected } };
    try {
      const res = await fetch(`${COMPLIANCE_URL}${endpoint}`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setGenerated({
        id: data.report_id,
        type: type === "dpia" ? "DPDP DPIA" : "RBI FREE",
        score: Math.round(data.overall_score ?? data.overall_compliance_score ?? 0),
        htmlUrl: `${COMPLIANCE_URL}/report/${data.report_id}/html`,
      });
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setGenerating(null);
    }
  }

  return (
    <div style={{ padding: "36px 40px", maxWidth: 960, margin: "0 auto" }}>
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, margin: "0 0 6px", fontFamily: "Space Grotesk, sans-serif", color: "#0D0D0B" }}>
          Compliance Reports
        </h1>
        <p style={{ margin: 0, fontSize: 14, color: "#71716B" }}>
          Auto-generate DPDP DPIA and RBI FREE assessments from your agent telemetry
        </p>
      </div>

      {/* Generator cards */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 28 }}>
        {/* DPDP DPIA */}
        <div style={{ background: "white", borderRadius: 12, border: "1px solid #E8E8E4", overflow: "hidden" }}>
          <div style={{ padding: "20px 22px", borderBottom: "1px solid #F0F0EC" }}>
            <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
              <div>
                <div style={{ fontSize: 15, fontWeight: 700, color: "#0D0D0B", marginBottom: 4 }}>DPDP DPIA</div>
                <div style={{ fontSize: 12, color: "#71716B" }}>Data Protection Impact Assessment · 7 sections</div>
              </div>
              <span style={{ fontSize: 10, fontWeight: 700, padding: "3px 8px", borderRadius: 5, background: "#EEF4FF", color: "#1C6EF2" }}>DPDP ACT §33</span>
            </div>
          </div>
          <div style={{ padding: "18px 22px" }}>
            <div style={{ fontSize: 12, color: "#71716B", marginBottom: 16 }}>
              Covers processing activities, data categories, retention, consent, grievance redressal, and RoPA.
            </div>
            <div style={{ marginBottom: 16 }}>
              {[
                { key: "org_id",                label: "Org ID",      type: "text" },
                { key: "period_start",           label: "From",        type: "date" },
                { key: "period_end",             label: "To",          type: "date" },
                { key: "agent_runs",             label: "Agent runs",  type: "number" },
                { key: "pii_detections",         label: "PII events",  type: "number" },
              ].map(f => (
                <div key={f.key} style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
                  <label style={{ fontSize: 12, color: "#71716B", width: 96, flexShrink: 0 }}>{f.label}</label>
                  <input
                    type={f.type}
                    value={(tel as Record<string, unknown>)[f.key] as string}
                    onChange={e => setTel(prev => ({ ...prev, [f.key]: f.type === "number" ? Number(e.target.value) : e.target.value }))}
                    style={{
                      flex: 1, border: "1px solid #E8E8E4", borderRadius: 6, padding: "5px 10px",
                      fontSize: 12, fontFamily: "inherit", outline: "none", background: "#FAFAF8",
                    }}
                  />
                </div>
              ))}
            </div>
            <button
              onClick={() => generate("dpia")}
              disabled={generating === "dpia"}
              style={{
                width: "100%", padding: "9px", borderRadius: 8, background: "#0D0D0B", color: "white",
                border: "none", fontSize: 13, fontWeight: 500, cursor: generating === "dpia" ? "wait" : "pointer",
                opacity: generating === "dpia" ? 0.7 : 1, fontFamily: "inherit",
              }}
            >
              {generating === "dpia" ? "Generating…" : "Generate DPDP DPIA"}
            </button>
          </div>
        </div>

        {/* RBI FREE */}
        <div style={{ background: "white", borderRadius: 12, border: "1px solid #E8E8E4", overflow: "hidden" }}>
          <div style={{ padding: "20px 22px", borderBottom: "1px solid #F0F0EC" }}>
            <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
              <div>
                <div style={{ fontSize: 15, fontWeight: 700, color: "#0D0D0B", marginBottom: 4 }}>RBI FREE Framework</div>
                <div style={{ fontSize: 12, color: "#71716B" }}>AI Risk & Governance · 26 recommendations</div>
              </div>
              <span style={{ fontSize: 10, fontWeight: 700, padding: "3px 8px", borderRadius: 5, background: "#FFF8E7", color: "#d97706" }}>RBI 2024</span>
            </div>
          </div>
          <div style={{ padding: "18px 22px" }}>
            <div style={{ fontSize: 12, color: "#71716B", marginBottom: 16 }}>
              5 pillars: Fairness, Resilience, Explainability, Ethics, Evolution. Auto-scored from telemetry.
            </div>
            <div style={{ marginBottom: 16 }}>
              {[
                { key: "org_id",          label: "Org ID",       type: "text" },
                { key: "period_start",    label: "From",         type: "date" },
                { key: "period_end",      label: "To",           type: "date" },
                { key: "human_reviews",   label: "Human reviews",type: "number" },
                { key: "agent_runs",      label: "Agent runs",   type: "number" },
              ].map(f => (
                <div key={f.key} style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
                  <label style={{ fontSize: 12, color: "#71716B", width: 96, flexShrink: 0 }}>{f.label}</label>
                  <input
                    type={f.type}
                    value={(tel as Record<string, unknown>)[f.key] as string}
                    onChange={e => setTel(prev => ({ ...prev, [f.key]: f.type === "number" ? Number(e.target.value) : e.target.value }))}
                    style={{
                      flex: 1, border: "1px solid #E8E8E4", borderRadius: 6, padding: "5px 10px",
                      fontSize: 12, fontFamily: "inherit", outline: "none", background: "#FAFAF8",
                    }}
                  />
                </div>
              ))}
            </div>
            <button
              onClick={() => generate("rbi")}
              disabled={generating === "rbi"}
              style={{
                width: "100%", padding: "9px", borderRadius: 8, background: "#0D0D0B", color: "white",
                border: "none", fontSize: 13, fontWeight: 500, cursor: generating === "rbi" ? "wait" : "pointer",
                opacity: generating === "rbi" ? 0.7 : 1, fontFamily: "inherit",
              }}
            >
              {generating === "rbi" ? "Generating…" : "Generate RBI FREE Assessment"}
            </button>
          </div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div style={{ marginBottom: 20, padding: "12px 18px", borderRadius: 8, background: "#FFF0F0", border: "1px solid #FDD", fontSize: 13, color: "#dc2626" }}>
          {error.includes("403") || error.includes("401")
            ? "Compliance Engine is SSO-protected. Disable deployment protection in the Vercel dashboard to enable live generation."
            : error}
        </div>
      )}

      {/* Generated report */}
      {generated && (
        <div style={{ marginBottom: 20, padding: "18px 22px", borderRadius: 12, background: "#F0FDF4", border: "1px solid #BBF7D0" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 12 }}>
            <span style={{ fontSize: 14, fontWeight: 600, color: "#15803d" }}>✓ {generated.type} generated</span>
            <span style={{ fontSize: 12, color: "#71716B", fontFamily: "JetBrains Mono, monospace" }}>{generated.id}</span>
          </div>
          <ScoreBar score={generated.score} />
          {generated.htmlUrl && (
            <a href={generated.htmlUrl} target="_blank" rel="noreferrer" style={{
              display: "inline-block", marginTop: 12, padding: "6px 16px", borderRadius: 7,
              background: "#15803d", color: "white", fontSize: 13, fontWeight: 500, textDecoration: "none",
            }}>Open Report →</a>
          )}
        </div>
      )}

      {/* Past reports */}
      <div style={{ background: "white", borderRadius: 12, border: "1px solid #E8E8E4", overflow: "hidden" }}>
        <div style={{ padding: "16px 22px", borderBottom: "1px solid #F0F0EC" }}>
          <span style={{ fontSize: 14, fontWeight: 600, color: "#0D0D0B" }}>Past Reports</span>
        </div>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ background: "#FAFAF8" }}>
              {["Report ID", "Type", "Period", "Date", "Score", ""].map(h => (
                <th key={h} style={{ padding: "10px 22px", textAlign: "left", fontSize: 11, fontWeight: 600, color: "#71716B", textTransform: "uppercase", letterSpacing: "0.05em" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {PAST_REPORTS.map((r, i) => (
              <tr key={i} style={{ borderTop: "1px solid #F5F5F3" }}>
                <td style={{ padding: "12px 22px", fontSize: 12, fontFamily: "JetBrains Mono, monospace", color: "#71716B" }}>{r.id}</td>
                <td style={{ padding: "12px 22px", fontSize: 13, fontWeight: 500, color: "#0D0D0B" }}>{r.type}</td>
                <td style={{ padding: "12px 22px", fontSize: 12, color: "#71716B" }}>{r.period}</td>
                <td style={{ padding: "12px 22px", fontSize: 12, color: "#A8A8A2" }}>{r.date}</td>
                <td style={{ padding: "12px 22px", minWidth: 160 }}><ScoreBar score={r.score} /></td>
                <td style={{ padding: "12px 22px" }}>
                  <button style={{
                    padding: "4px 12px", borderRadius: 6, border: "1px solid #E8E8E4",
                    background: "white", color: "#71716B", fontSize: 12, cursor: "pointer", fontFamily: "inherit",
                  }}>Download</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
