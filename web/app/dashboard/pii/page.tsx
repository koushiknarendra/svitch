"use client";
import { useState } from "react";

const PII_SHIELD_URL = process.env.NEXT_PUBLIC_PII_SHIELD_URL ?? "https://service-sage-mu.vercel.app";

const ENTITY_COLORS: Record<string, string> = {
  AADHAAR_IN: "#1C6EF2", PAN_IN: "#9333ea", UPI_IN: "#d97706",
  MOBILE_IN: "#16a34a",  IFSC_IN: "#0891b2", BANK_ACCOUNT_IN: "#dc2626",
  GST_IN: "#7c3aed",     EMAIL: "#ea580c",    IPV4: "#71716B",
};

interface DetectResult {
  redacted: string;
  entities: Array<{ type: string; value: string; start: number; end: number }>;
  pii_found: boolean;
  processing_ms: number;
}

const SAMPLES = [
  { label: "Loan application", text: "Customer Rajesh Kumar, Aadhaar 9876 5432 1098, PAN ABCDE1234F applied for ₹5L loan. Account 912345678901, IFSC HDFC0001234. UPI rajesh@upi, mobile 9876543210." },
  { label: "KYC verification", text: "KYC for Priya Sharma, mob: +91-9123456789, email priya.sharma@gmail.com. GST 22AAAAA0000A1Z5. Aadhaar: 2345-6789-0123." },
  { label: "Clean text",        text: "The quarterly revenue target is ₹50 crores. Please review the attached projection model for Q4 FY26." },
];

const RECENT: Array<{ time: string; entities: string[]; agent: string; blocked: boolean }> = [
  { time: "2m ago",  entities: ["AADHAAR_IN", "PAN_IN", "MOBILE_IN"], agent: "loan-processor-v3", blocked: true },
  { time: "6m ago",  entities: ["UPI_IN", "MOBILE_IN"],               agent: "support-agent-v1",  blocked: true },
  { time: "14m ago", entities: ["EMAIL"],                             agent: "marketing-agent",   blocked: false },
  { time: "28m ago", entities: ["AADHAAR_IN", "BANK_ACCOUNT_IN"],    agent: "fraud-detector",    blocked: true },
  { time: "41m ago", entities: ["GST_IN"],                           agent: "invoice-agent",      blocked: false },
];

export default function PIIShieldPage() {
  const [text, setText] = useState(SAMPLES[0].text);
  const [result, setResult] = useState<DetectResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function scan() {
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const res = await fetch(`${PII_SHIELD_URL}/detect`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, mode: "redact" }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setResult(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  const entityCounts: Record<string, number> = {};
  if (result) {
    for (const e of result.entities) {
      entityCounts[e.type] = (entityCounts[e.type] ?? 0) + 1;
    }
  }

  return (
    <div style={{ padding: "36px 40px", maxWidth: 960, margin: "0 auto" }}>
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, margin: "0 0 6px", fontFamily: "Space Grotesk, sans-serif", color: "#0D0D0B" }}>
          PII Shield
        </h1>
        <p style={{ margin: 0, fontSize: 14, color: "#71716B" }}>
          Detect and redact Indian PII from prompts and responses in real time
        </p>
      </div>

      {/* Stats */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14, marginBottom: 28 }}>
        {[
          { label: "Scans today",     value: "1,847" },
          { label: "PII blocked",     value: "312" },
          { label: "Block rate",      value: "16.9%" },
          { label: "Avg latency",     value: "38 ms" },
        ].map(s => (
          <div key={s.label} style={{ background: "white", borderRadius: 10, padding: "16px 18px", border: "1px solid #E8E8E4" }}>
            <div style={{ fontSize: 11, color: "#71716B", marginBottom: 6, fontWeight: 500, textTransform: "uppercase", letterSpacing: "0.05em" }}>{s.label}</div>
            <div style={{ fontSize: 22, fontWeight: 700, fontFamily: "Space Grotesk, sans-serif", color: "#0D0D0B" }}>{s.value}</div>
          </div>
        ))}
      </div>

      {/* Live demo */}
      <div style={{ background: "white", borderRadius: 12, border: "1px solid #E8E8E4", marginBottom: 20, overflow: "hidden" }}>
        <div style={{ padding: "18px 22px 0", borderBottom: "1px solid #F0F0EC", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontSize: 14, fontWeight: 600, color: "#0D0D0B", paddingBottom: 16 }}>Live Demo</span>
          <div style={{ display: "flex", gap: 8, paddingBottom: 12 }}>
            {SAMPLES.map(s => (
              <button key={s.label} onClick={() => { setText(s.text); setResult(null); }} style={{
                padding: "4px 12px", borderRadius: 6, border: "1px solid #E8E8E4",
                background: text === s.text ? "#0D0D0B" : "white", color: text === s.text ? "white" : "#71716B",
                fontSize: 12, cursor: "pointer", fontFamily: "inherit",
              }}>{s.label}</button>
            ))}
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", minHeight: 180 }}>
          <div style={{ padding: 22, borderRight: "1px solid #F0F0EC" }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: "#71716B", marginBottom: 10, textTransform: "uppercase", letterSpacing: "0.05em" }}>Input</div>
            <textarea
              value={text}
              onChange={e => { setText(e.target.value); setResult(null); }}
              style={{
                width: "100%", height: 140, border: "1px solid #E8E8E4", borderRadius: 8,
                padding: 12, fontSize: 13, resize: "vertical", outline: "none",
                fontFamily: "JetBrains Mono, monospace", color: "#0D0D0B", background: "#FAFAF8",
                boxSizing: "border-box",
              }}
            />
          </div>
          <div style={{ padding: 22 }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: "#71716B", marginBottom: 10, textTransform: "uppercase", letterSpacing: "0.05em" }}>Redacted Output</div>
            {result ? (
              <div style={{
                height: 140, border: "1px solid #E8E8E4", borderRadius: 8, padding: 12,
                fontSize: 13, fontFamily: "JetBrains Mono, monospace", color: "#0D0D0B",
                background: result.pii_found ? "#FFF8F0" : "#F0FDF4",
                overflowY: "auto", whiteSpace: "pre-wrap", wordBreak: "break-word",
              }}>
                {result.redacted}
              </div>
            ) : (
              <div style={{
                height: 140, border: "1px dashed #E8E8E4", borderRadius: 8, display: "flex",
                alignItems: "center", justifyContent: "center", color: "#A8A8A2", fontSize: 13,
              }}>
                Output appears here
              </div>
            )}
          </div>
        </div>

        <div style={{ padding: "16px 22px", borderTop: "1px solid #F0F0EC", display: "flex", alignItems: "center", gap: 16 }}>
          <button
            onClick={scan}
            disabled={loading || !text.trim()}
            style={{
              padding: "8px 20px", borderRadius: 8, background: "#0D0D0B", color: "white",
              border: "none", fontSize: 14, fontWeight: 500, cursor: loading ? "wait" : "pointer",
              opacity: loading ? 0.7 : 1, fontFamily: "inherit",
            }}
          >
            {loading ? "Scanning…" : "Scan for PII"}
          </button>

          {result && (
            <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
              {Object.entries(entityCounts).map(([type, count]) => (
                <span key={type} style={{
                  fontSize: 11, fontWeight: 600, padding: "3px 8px", borderRadius: 5,
                  background: `${ENTITY_COLORS[type] ?? "#71716B"}18`,
                  color: ENTITY_COLORS[type] ?? "#71716B",
                }}>
                  {type} × {count}
                </span>
              ))}
              {!result.pii_found && (
                <span style={{ fontSize: 12, color: "#16a34a", fontWeight: 500 }}>✓ No PII detected</span>
              )}
              <span style={{ fontSize: 11, color: "#A8A8A2", marginLeft: "auto" }}>{result.processing_ms} ms</span>
            </div>
          )}

          {error && (
            <span style={{ fontSize: 12, color: "#dc2626" }}>
              {error.includes("403") || error.includes("401")
                ? "API protected — disable Vercel deployment protection to use live demo"
                : `Error: ${error}`}
            </span>
          )}
        </div>
      </div>

      {/* Recent detections */}
      <div style={{ background: "white", borderRadius: 12, border: "1px solid #E8E8E4", overflow: "hidden" }}>
        <div style={{ padding: "18px 22px", borderBottom: "1px solid #F0F0EC" }}>
          <span style={{ fontSize: 14, fontWeight: 600, color: "#0D0D0B" }}>Recent Detections</span>
        </div>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ background: "#FAFAF8" }}>
              {["Time", "Agent", "Entity Types", "Blocked"].map(h => (
                <th key={h} style={{ padding: "10px 22px", textAlign: "left", fontSize: 11, fontWeight: 600, color: "#71716B", textTransform: "uppercase", letterSpacing: "0.05em" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {RECENT.map((r, i) => (
              <tr key={i} style={{ borderTop: "1px solid #F5F5F3" }}>
                <td style={{ padding: "12px 22px", fontSize: 12, color: "#A8A8A2" }}>{r.time}</td>
                <td style={{ padding: "12px 22px", fontSize: 12, fontFamily: "JetBrains Mono, monospace", color: "#0D0D0B" }}>{r.agent}</td>
                <td style={{ padding: "12px 22px" }}>
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                    {r.entities.map(e => (
                      <span key={e} style={{
                        fontSize: 10, fontWeight: 600, padding: "2px 7px", borderRadius: 4,
                        background: `${ENTITY_COLORS[e] ?? "#71716B"}18`, color: ENTITY_COLORS[e] ?? "#71716B",
                      }}>{e}</span>
                    ))}
                  </div>
                </td>
                <td style={{ padding: "12px 22px" }}>
                  <span style={{
                    fontSize: 11, fontWeight: 600, padding: "3px 8px", borderRadius: 5,
                    background: r.blocked ? "#FFF0F0" : "#F0FDF4", color: r.blocked ? "#dc2626" : "#16a34a",
                  }}>{r.blocked ? "Blocked" : "Passed"}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
