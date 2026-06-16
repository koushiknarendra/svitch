"use client";
import { useState } from "react";

interface Step {
  seq: number;
  tool: string;
  input_summary: string;
  pii_detected: boolean;
  pii_types: string[];
  duration_ms: number;
  human_reviewed: boolean;
  output_summary: string;
}

interface Run {
  run_id: string;
  agent_id: string;
  started_at: string;
  duration_ms: number;
  steps: number;
  pii_touches: number;
  human_checkpoints: number;
  status: "completed" | "flagged" | "blocked";
  purpose: string;
  steps_data: Step[];
}

const RUNS: Run[] = [
  {
    run_id: "run_8f3a2c1d", agent_id: "loan-processor-v3", started_at: "2m ago",
    duration_ms: 4820, steps: 7, pii_touches: 3, human_checkpoints: 1,
    status: "completed", purpose: "Loan eligibility assessment",
    steps_data: [
      { seq: 1, tool: "fetch_customer_profile", input_summary: "customer_id=CUST-5821", pii_detected: false, pii_types: [], duration_ms: 112, human_reviewed: false, output_summary: "Customer profile loaded" },
      { seq: 2, tool: "pii_shield.detect",      input_summary: "Aadhaar 9876…1098, PAN ABCDE…", pii_detected: true, pii_types: ["AADHAAR_IN", "PAN_IN"], duration_ms: 38, human_reviewed: false, output_summary: "2 entities redacted" },
      { seq: 3, tool: "llm.chat",                input_summary: "Assess eligibility with redacted profile", pii_detected: false, pii_types: [], duration_ms: 1840, human_reviewed: false, output_summary: "Score: 72/100, Eligible" },
      { seq: 4, tool: "credit_bureau.query",     input_summary: "hashed_id=a3f2…", pii_detected: false, pii_types: [], duration_ms: 620, human_reviewed: false, output_summary: "Bureau score: 740" },
      { seq: 5, tool: "pii_shield.detect",       input_summary: "Account 9123…01, IFSC HDFC…", pii_detected: true, pii_types: ["BANK_ACCOUNT_IN", "IFSC_IN"], duration_ms: 41, human_reviewed: false, output_summary: "2 entities redacted" },
      { seq: 6, tool: "human_review.checkpoint", input_summary: "Final approval for ₹5L loan", pii_detected: false, pii_types: [], duration_ms: 24000, human_reviewed: true, output_summary: "Approved by Anand K." },
      { seq: 7, tool: "notify_customer",         input_summary: "mobile=9876…210 (hashed)", pii_detected: true, pii_types: ["MOBILE_IN"], duration_ms: 89, human_reviewed: false, output_summary: "SMS sent" },
    ],
  },
  {
    run_id: "run_2e9b4f7a", agent_id: "fraud-detector", started_at: "14m ago",
    duration_ms: 2340, steps: 5, pii_touches: 2, human_checkpoints: 0,
    status: "flagged", purpose: "Suspicious transaction review",
    steps_data: [
      { seq: 1, tool: "fetch_transaction",       input_summary: "txn_id=TXN-9921", pii_detected: false, pii_types: [], duration_ms: 88, human_reviewed: false, output_summary: "₹2.4L UPI transfer" },
      { seq: 2, tool: "pii_shield.detect",       input_summary: "UPI vpa=9876543210@upi", pii_detected: true, pii_types: ["UPI_IN"], duration_ms: 29, human_reviewed: false, output_summary: "1 entity redacted" },
      { seq: 3, tool: "rule_engine.evaluate",    input_summary: "velocity + amount threshold", pii_detected: false, pii_types: [], duration_ms: 140, human_reviewed: false, output_summary: "Rule #17 triggered" },
      { seq: 4, tool: "llm.chat",                input_summary: "Classify fraud risk", pii_detected: false, pii_types: [], duration_ms: 1980, human_reviewed: false, output_summary: "HIGH risk — flagged" },
      { seq: 5, tool: "pii_shield.detect",       input_summary: "Aadhaar in alert payload", pii_detected: true, pii_types: ["AADHAAR_IN"], duration_ms: 33, human_reviewed: false, output_summary: "Redacted before alert" },
    ],
  },
  {
    run_id: "run_c1d8e0f3", agent_id: "onboarding-agent", started_at: "22m ago",
    duration_ms: 8100, steps: 4, pii_touches: 1, human_checkpoints: 1,
    status: "completed", purpose: "New customer KYC",
    steps_data: [
      { seq: 1, tool: "consent.grant",           input_summary: "purpose=kyc, cats=[AADHAAR, MOBILE]", pii_detected: false, pii_types: [], duration_ms: 54, human_reviewed: false, output_summary: "Consent recorded" },
      { seq: 2, tool: "pii_shield.detect",       input_summary: "Aadhaar 2345…0123", pii_detected: true, pii_types: ["AADHAAR_IN"], duration_ms: 35, human_reviewed: false, output_summary: "1 entity redacted" },
      { seq: 3, tool: "kyc_provider.verify",     input_summary: "hashed aadhaar submitted", pii_detected: false, pii_types: [], duration_ms: 3400, human_reviewed: false, output_summary: "Verified" },
      { seq: 4, tool: "human_review.checkpoint", input_summary: "KYC approval", pii_detected: false, pii_types: [], duration_ms: 4600, human_reviewed: true, output_summary: "Approved" },
    ],
  },
];

const STATUS_COLOR: Record<string, string> = {
  completed: "#16a34a", flagged: "#d97706", blocked: "#dc2626",
};

const PII_COLOR: Record<string, string> = {
  AADHAAR_IN: "#1C6EF2", PAN_IN: "#9333ea", UPI_IN: "#d97706",
  MOBILE_IN: "#16a34a",  IFSC_IN: "#0891b2", BANK_ACCOUNT_IN: "#dc2626",
};

export default function AgentTracerPage() {
  const [selected, setSelected] = useState<Run | null>(null);

  return (
    <div style={{ padding: "36px 40px", maxWidth: 1100, margin: "0 auto" }}>
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, margin: "0 0 6px", fontFamily: "Space Grotesk, sans-serif", color: "#0D0D0B" }}>
          Agent Tracer
        </h1>
        <p style={{ margin: 0, fontSize: 14, color: "#71716B" }}>
          Immutable, hash-chained audit trail of every agent decision
        </p>
      </div>

      {/* Stats */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14, marginBottom: 28 }}>
        {[
          { label: "Runs (24h)",        value: "94" },
          { label: "PII touches",       value: "218" },
          { label: "Human checkpoints", value: "31" },
          { label: "Flagged runs",      value: "7" },
        ].map(s => (
          <div key={s.label} style={{ background: "white", borderRadius: 10, padding: "16px 18px", border: "1px solid #E8E8E4" }}>
            <div style={{ fontSize: 11, color: "#71716B", marginBottom: 6, fontWeight: 500, textTransform: "uppercase", letterSpacing: "0.05em" }}>{s.label}</div>
            <div style={{ fontSize: 22, fontWeight: 700, fontFamily: "Space Grotesk, sans-serif", color: "#0D0D0B" }}>{s.value}</div>
          </div>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: selected ? "340px 1fr" : "1fr", gap: 20 }}>
        {/* Runs list */}
        <div style={{ background: "white", borderRadius: 12, border: "1px solid #E8E8E4", overflow: "hidden", alignSelf: "start" }}>
          <div style={{ padding: "16px 20px", borderBottom: "1px solid #F0F0EC" }}>
            <span style={{ fontSize: 14, fontWeight: 600, color: "#0D0D0B" }}>Recent Runs</span>
          </div>
          {RUNS.map(run => (
            <div
              key={run.run_id}
              onClick={() => setSelected(selected?.run_id === run.run_id ? null : run)}
              style={{
                padding: "14px 20px", borderBottom: "1px solid #F5F5F3", cursor: "pointer",
                background: selected?.run_id === run.run_id ? "#F5F8FF" : "white",
                transition: "background 0.1s",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 6 }}>
                <span style={{ fontSize: 13, fontWeight: 500, color: "#0D0D0B", fontFamily: "JetBrains Mono, monospace" }}>{run.agent_id}</span>
                <span style={{
                  fontSize: 10, fontWeight: 700, padding: "2px 7px", borderRadius: 4,
                  background: `${STATUS_COLOR[run.status]}18`, color: STATUS_COLOR[run.status],
                  textTransform: "uppercase",
                }}>{run.status}</span>
              </div>
              <div style={{ fontSize: 12, color: "#71716B", marginBottom: 8 }}>{run.purpose}</div>
              <div style={{ display: "flex", gap: 12, fontSize: 11, color: "#A8A8A2" }}>
                <span>{run.steps} steps</span>
                <span>{run.pii_touches} PII</span>
                <span>{run.human_checkpoints} human</span>
                <span style={{ marginLeft: "auto" }}>{run.started_at}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Timeline */}
        {selected && (
          <div style={{ background: "white", borderRadius: 12, border: "1px solid #E8E8E4", overflow: "hidden" }}>
            <div style={{ padding: "16px 22px", borderBottom: "1px solid #F0F0EC", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div>
                <div style={{ fontSize: 14, fontWeight: 600, color: "#0D0D0B", marginBottom: 2 }}>
                  {selected.agent_id}
                </div>
                <div style={{ fontSize: 11, color: "#A8A8A2", fontFamily: "JetBrains Mono, monospace" }}>{selected.run_id}</div>
              </div>
              <button onClick={() => setSelected(null)} style={{
                background: "none", border: "none", cursor: "pointer", color: "#71716B", fontSize: 20, lineHeight: 1, padding: 4,
              }}>×</button>
            </div>

            <div style={{ padding: "20px 22px" }}>
              {selected.steps_data.map((step, i) => (
                <div key={step.seq} style={{ display: "flex", gap: 16, marginBottom: i < selected.steps_data.length - 1 ? 0 : 0 }}>
                  {/* Timeline spine */}
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", width: 28 }}>
                    <div style={{
                      width: 28, height: 28, borderRadius: "50%", flexShrink: 0,
                      display: "flex", alignItems: "center", justifyContent: "center",
                      background: step.pii_detected ? "#FFF0F0" : step.human_reviewed ? "#EEF4FF" : "#F5F5F3",
                      border: `1.5px solid ${step.pii_detected ? "#dc2626" : step.human_reviewed ? "#1C6EF2" : "#E8E8E4"}`,
                      fontSize: 11, fontWeight: 700,
                      color: step.pii_detected ? "#dc2626" : step.human_reviewed ? "#1C6EF2" : "#71716B",
                    }}>{step.seq}</div>
                    {i < selected.steps_data.length - 1 && (
                      <div style={{ width: 1, flex: 1, minHeight: 20, background: "#E8E8E4", margin: "4px 0" }} />
                    )}
                  </div>

                  {/* Step content */}
                  <div style={{ flex: 1, paddingBottom: i < selected.steps_data.length - 1 ? 16 : 0 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                      <span style={{ fontSize: 13, fontWeight: 600, color: "#0D0D0B", fontFamily: "JetBrains Mono, monospace" }}>{step.tool}</span>
                      <span style={{ fontSize: 11, color: "#A8A8A2" }}>{step.duration_ms}ms</span>
                      {step.human_reviewed && (
                        <span style={{ fontSize: 10, fontWeight: 700, padding: "1px 6px", borderRadius: 4, background: "#EEF4FF", color: "#1C6EF2" }}>HUMAN</span>
                      )}
                    </div>
                    <div style={{ fontSize: 12, color: "#71716B", marginBottom: step.pii_types.length ? 6 : 0 }}>{step.input_summary}</div>
                    {step.pii_types.length > 0 && (
                      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 4 }}>
                        {step.pii_types.map(t => (
                          <span key={t} style={{
                            fontSize: 10, fontWeight: 600, padding: "2px 6px", borderRadius: 4,
                            background: `${PII_COLOR[t] ?? "#71716B"}18`, color: PII_COLOR[t] ?? "#71716B",
                          }}>{t}</span>
                        ))}
                      </div>
                    )}
                    <div style={{ fontSize: 12, color: "#A8A8A2", fontStyle: "italic" }}>→ {step.output_summary}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
