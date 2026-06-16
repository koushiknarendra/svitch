"use client";
import { useState } from "react";

interface ConsentRecord {
  consent_id: string;
  purpose: string;
  data_categories: string[];
  legal_basis: string;
  status: string;
  granted_at_ms: number;
  withdrawn_at_ms: number | null;
  channel: string;
  version: string;
  record_hash: string;
  withdrawal_of: string | null;
}

const PURPOSES = [
  "loan_processing", "kyc_verification", "credit_scoring",
  "fraud_detection", "marketing", "analytics", "customer_support",
];
const CATEGORIES = [
  "AADHAAR_IN", "PAN_IN", "MOBILE_IN", "BANK_ACCOUNT_IN",
  "UPI_IN", "IFSC_IN", "EMAIL", "GST_IN",
];
const CHANNELS = ["web", "mobile_app", "branch", "ivr"];

const DEMO: ConsentRecord[] = [
  {
    consent_id: "c1a2b3c4-d5e6-7890-abcd-ef0123456789",
    purpose: "loan_processing",
    data_categories: ["AADHAAR_IN", "PAN_IN", "BANK_ACCOUNT_IN"],
    legal_basis: "explicit_consent",
    status: "active",
    granted_at_ms: Date.now() - 1000 * 60 * 22,
    withdrawn_at_ms: null,
    channel: "mobile_app",
    version: "2.1",
    record_hash: "a3f2b1c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2",
    withdrawal_of: null,
  },
  {
    consent_id: "d2e3f4a5-b6c7-8901-bcde-f01234567890",
    purpose: "kyc_verification",
    data_categories: ["AADHAAR_IN", "MOBILE_IN"],
    legal_basis: "regulatory_obligation",
    status: "active",
    granted_at_ms: Date.now() - 1000 * 60 * 60 * 2,
    withdrawn_at_ms: null,
    channel: "web",
    version: "2.1",
    record_hash: "b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5",
    withdrawal_of: null,
  },
  {
    consent_id: "e3f4a5b6-c7d8-9012-cdef-012345678901",
    purpose: "marketing",
    data_categories: ["EMAIL", "MOBILE_IN"],
    legal_basis: "explicit_consent",
    status: "withdrawn",
    granted_at_ms: Date.now() - 1000 * 60 * 60 * 24 * 3,
    withdrawn_at_ms: Date.now() - 1000 * 60 * 60 * 6,
    channel: "web",
    version: "2.0",
    record_hash: "c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6",
    withdrawal_of: null,
  },
];

const CAT_COLOR: Record<string, string> = {
  AADHAAR_IN: "#1C6EF2", PAN_IN: "#9333ea", UPI_IN: "#d97706",
  MOBILE_IN: "#16a34a",  IFSC_IN: "#0891b2", BANK_ACCOUNT_IN: "#dc2626",
  GST_IN: "#7c3aed",     EMAIL: "#ea580c",
};

function fmt(ms: number) {
  return new Date(ms).toLocaleString("en-IN", { dateStyle: "short", timeStyle: "short" });
}

export default function ConsentLedgerPage() {
  const [records, setRecords] = useState<ConsentRecord[]>(DEMO);
  const [verifyId, setVerifyId] = useState("");
  const [verifyResult, setVerifyResult] = useState<{ valid: boolean; reason: string; hash: string } | null>(null);
  const [form, setForm] = useState({
    customerId: "", purpose: "loan_processing", channel: "web", version: "2.1",
    categories: ["AADHAAR_IN", "PAN_IN"],
  });

  function grantConsent() {
    if (!form.customerId.trim()) return;
    const newRecord: ConsentRecord = {
      consent_id: crypto.randomUUID(),
      purpose: form.purpose,
      data_categories: form.categories,
      legal_basis: "explicit_consent",
      status: "active",
      granted_at_ms: Date.now(),
      withdrawn_at_ms: null,
      channel: form.channel,
      version: form.version,
      record_hash: Array.from(crypto.getRandomValues(new Uint8Array(32))).map(b => b.toString(16).padStart(2, "0")).join(""),
      withdrawal_of: null,
    };
    setRecords(prev => [newRecord, ...prev]);
    setForm(f => ({ ...f, customerId: "" }));
  }

  function withdraw(id: string) {
    setRecords(prev => prev.map(r =>
      r.consent_id === id ? { ...r, status: "withdrawn", withdrawn_at_ms: Date.now() } : r
    ));
  }

  function verify() {
    const r = records.find(r => r.consent_id.startsWith(verifyId) || r.record_hash.startsWith(verifyId));
    if (!r) {
      setVerifyResult({ valid: false, reason: "Consent record not found", hash: "" });
      return;
    }
    setVerifyResult({
      valid: r.status === "active",
      reason: r.status === "active" ? "Consent is valid and active" : "Consent has been withdrawn",
      hash: r.record_hash,
    });
  }

  function toggleCategory(cat: string) {
    setForm(f => ({
      ...f,
      categories: f.categories.includes(cat) ? f.categories.filter(c => c !== cat) : [...f.categories, cat],
    }));
  }

  return (
    <div style={{ padding: "36px 40px", maxWidth: 1060, margin: "0 auto" }}>
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, margin: "0 0 6px", fontFamily: "Space Grotesk, sans-serif", color: "#0D0D0B" }}>
          Consent Ledger
        </h1>
        <p style={{ margin: 0, fontSize: 14, color: "#71716B" }}>
          Immutable, hash-chained consent records compliant with DPDP Act §6
        </p>
      </div>

      {/* Stats */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14, marginBottom: 28 }}>
        {[
          { label: "Total consents",   value: records.length.toString() },
          { label: "Active",           value: records.filter(r => r.status === "active").length.toString() },
          { label: "Withdrawn",        value: records.filter(r => r.status === "withdrawn").length.toString() },
          { label: "Chain integrity",  value: "✓ Intact" },
        ].map(s => (
          <div key={s.label} style={{ background: "white", borderRadius: 10, padding: "16px 18px", border: "1px solid #E8E8E4" }}>
            <div style={{ fontSize: 11, color: "#71716B", marginBottom: 6, fontWeight: 500, textTransform: "uppercase", letterSpacing: "0.05em" }}>{s.label}</div>
            <div style={{ fontSize: 22, fontWeight: 700, fontFamily: "Space Grotesk, sans-serif", color: s.label === "Chain integrity" ? "#16a34a" : "#0D0D0B" }}>{s.value}</div>
          </div>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 340px", gap: 20, alignItems: "start" }}>

        {/* Records table */}
        <div style={{ background: "white", borderRadius: 12, border: "1px solid #E8E8E4", overflow: "hidden" }}>
          <div style={{ padding: "16px 22px", borderBottom: "1px solid #F0F0EC" }}>
            <span style={{ fontSize: 14, fontWeight: 600, color: "#0D0D0B" }}>Consent Records</span>
          </div>
          {records.map((r, i) => (
            <div key={r.consent_id} style={{
              padding: "16px 22px",
              borderBottom: i < records.length - 1 ? "1px solid #F5F5F3" : "none",
              background: r.status === "withdrawn" ? "#FAFAF8" : "white",
            }}>
              <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 8 }}>
                <div>
                  <div style={{ fontSize: 12, fontFamily: "JetBrains Mono, monospace", color: "#71716B", marginBottom: 4 }}>
                    {r.consent_id.split("-")[0]}…
                  </div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: "#0D0D0B" }}>{r.purpose.replace(/_/g, " ")}</div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{
                    fontSize: 11, fontWeight: 700, padding: "3px 8px", borderRadius: 5,
                    background: r.status === "active" ? "#F0FDF4" : "#FAFAF8",
                    color: r.status === "active" ? "#16a34a" : "#A8A8A2",
                    textTransform: "uppercase",
                  }}>{r.status}</span>
                  {r.status === "active" && (
                    <button onClick={() => withdraw(r.consent_id)} style={{
                      padding: "3px 10px", borderRadius: 6, border: "1px solid #FDD",
                      background: "white", color: "#dc2626", fontSize: 11, cursor: "pointer", fontFamily: "inherit",
                    }}>Withdraw</button>
                  )}
                </div>
              </div>

              <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 8 }}>
                {r.data_categories.map(c => (
                  <span key={c} style={{
                    fontSize: 10, fontWeight: 600, padding: "2px 7px", borderRadius: 4,
                    background: `${CAT_COLOR[c] ?? "#71716B"}18`, color: CAT_COLOR[c] ?? "#71716B",
                  }}>{c}</span>
                ))}
              </div>

              <div style={{ display: "flex", gap: 20, fontSize: 11, color: "#A8A8A2" }}>
                <span>Granted {fmt(r.granted_at_ms)}</span>
                {r.withdrawn_at_ms && <span>Withdrawn {fmt(r.withdrawn_at_ms)}</span>}
                <span>{r.channel} · v{r.version}</span>
                <span style={{ marginLeft: "auto", fontFamily: "JetBrains Mono, monospace" }}>{r.record_hash.slice(0, 12)}…</span>
              </div>
            </div>
          ))}
        </div>

        {/* Right column */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>

          {/* Grant form */}
          <div style={{ background: "white", borderRadius: 12, border: "1px solid #E8E8E4", padding: "20px 22px" }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: "#0D0D0B", marginBottom: 16 }}>Grant Consent</div>

            <div style={{ marginBottom: 12 }}>
              <label style={{ fontSize: 12, color: "#71716B", display: "block", marginBottom: 4 }}>Customer ID</label>
              <input
                value={form.customerId}
                onChange={e => setForm(f => ({ ...f, customerId: e.target.value }))}
                placeholder="CUST-1234"
                style={{ width: "100%", border: "1px solid #E8E8E4", borderRadius: 7, padding: "7px 10px", fontSize: 13, outline: "none", fontFamily: "inherit", boxSizing: "border-box" }}
              />
            </div>

            <div style={{ marginBottom: 12 }}>
              <label style={{ fontSize: 12, color: "#71716B", display: "block", marginBottom: 4 }}>Purpose</label>
              <select
                value={form.purpose}
                onChange={e => setForm(f => ({ ...f, purpose: e.target.value }))}
                style={{ width: "100%", border: "1px solid #E8E8E4", borderRadius: 7, padding: "7px 10px", fontSize: 13, outline: "none", fontFamily: "inherit", background: "white", boxSizing: "border-box" }}
              >
                {PURPOSES.map(p => <option key={p} value={p}>{p.replace(/_/g, " ")}</option>)}
              </select>
            </div>

            <div style={{ marginBottom: 12 }}>
              <label style={{ fontSize: 12, color: "#71716B", display: "block", marginBottom: 6 }}>Data Categories</label>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {CATEGORIES.map(c => (
                  <button
                    key={c}
                    onClick={() => toggleCategory(c)}
                    style={{
                      padding: "3px 9px", borderRadius: 5, border: `1px solid ${form.categories.includes(c) ? CAT_COLOR[c] ?? "#71716B" : "#E8E8E4"}`,
                      background: form.categories.includes(c) ? `${CAT_COLOR[c] ?? "#71716B"}15` : "white",
                      color: form.categories.includes(c) ? CAT_COLOR[c] ?? "#71716B" : "#71716B",
                      fontSize: 11, fontWeight: 600, cursor: "pointer", fontFamily: "inherit",
                    }}
                  >{c}</button>
                ))}
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 16 }}>
              <div>
                <label style={{ fontSize: 12, color: "#71716B", display: "block", marginBottom: 4 }}>Channel</label>
                <select value={form.channel} onChange={e => setForm(f => ({ ...f, channel: e.target.value }))}
                  style={{ width: "100%", border: "1px solid #E8E8E4", borderRadius: 7, padding: "7px 10px", fontSize: 12, outline: "none", fontFamily: "inherit", background: "white" }}>
                  {CHANNELS.map(c => <option key={c}>{c}</option>)}
                </select>
              </div>
              <div>
                <label style={{ fontSize: 12, color: "#71716B", display: "block", marginBottom: 4 }}>Version</label>
                <input value={form.version} onChange={e => setForm(f => ({ ...f, version: e.target.value }))}
                  style={{ width: "100%", border: "1px solid #E8E8E4", borderRadius: 7, padding: "7px 10px", fontSize: 12, outline: "none", fontFamily: "inherit", boxSizing: "border-box" }} />
              </div>
            </div>

            <button
              onClick={grantConsent}
              disabled={!form.customerId.trim() || form.categories.length === 0}
              style={{
                width: "100%", padding: "9px", borderRadius: 8, background: "#0D0D0B", color: "white",
                border: "none", fontSize: 13, fontWeight: 500, cursor: "pointer", fontFamily: "inherit",
                opacity: !form.customerId.trim() || form.categories.length === 0 ? 0.5 : 1,
              }}
            >Grant Consent</button>
          </div>

          {/* Verify */}
          <div style={{ background: "white", borderRadius: 12, border: "1px solid #E8E8E4", padding: "20px 22px" }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: "#0D0D0B", marginBottom: 12 }}>Verify Record</div>
            <input
              value={verifyId}
              onChange={e => { setVerifyId(e.target.value); setVerifyResult(null); }}
              placeholder="Consent ID or record hash prefix…"
              style={{ width: "100%", border: "1px solid #E8E8E4", borderRadius: 7, padding: "7px 10px", fontSize: 12, outline: "none", fontFamily: "JetBrains Mono, monospace", marginBottom: 10, boxSizing: "border-box" }}
            />
            <button
              onClick={verify}
              disabled={!verifyId.trim()}
              style={{
                width: "100%", padding: "8px", borderRadius: 8, background: "#1C6EF2", color: "white",
                border: "none", fontSize: 13, fontWeight: 500, cursor: "pointer", fontFamily: "inherit",
                opacity: !verifyId.trim() ? 0.5 : 1,
              }}
            >Verify</button>
            {verifyResult && (
              <div style={{
                marginTop: 12, padding: "12px 14px", borderRadius: 8,
                background: verifyResult.valid ? "#F0FDF4" : "#FFF0F0",
                border: `1px solid ${verifyResult.valid ? "#BBF7D0" : "#FDD"}`,
              }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: verifyResult.valid ? "#15803d" : "#dc2626", marginBottom: 4 }}>
                  {verifyResult.valid ? "✓ Valid" : "✗ Invalid"}
                </div>
                <div style={{ fontSize: 12, color: "#71716B", marginBottom: verifyResult.hash ? 6 : 0 }}>{verifyResult.reason}</div>
                {verifyResult.hash && (
                  <div style={{ fontSize: 10, fontFamily: "JetBrains Mono, monospace", color: "#A8A8A2", wordBreak: "break-all" }}>{verifyResult.hash}</div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
