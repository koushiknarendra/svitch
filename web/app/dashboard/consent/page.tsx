"use client";
import { useState, useEffect, useCallback } from "react";

const LEDGER_URL = process.env.NEXT_PUBLIC_CONSENT_LEDGER_URL ?? "https://consent-ledger-kappa.vercel.app";

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

const CAT_COLOR: Record<string, string> = {
  AADHAAR_IN: "#1C6EF2", PAN_IN: "#9333ea", UPI_IN: "#d97706",
  MOBILE_IN: "#16a34a",  IFSC_IN: "#0891b2", BANK_ACCOUNT_IN: "#dc2626",
  GST_IN: "#7c3aed",     EMAIL: "#ea580c",
};

function fmt(ms: number) {
  return new Date(ms).toLocaleString("en-IN", { dateStyle: "short", timeStyle: "short" });
}

export default function ConsentLedgerPage() {
  const [records, setRecords] = useState<ConsentRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [apiError, setApiError] = useState("");
  const [verifyId, setVerifyId] = useState("");
  const [verifyResult, setVerifyResult] = useState<{ valid: boolean; reason: string; hash: string } | null>(null);
  const [verifying, setVerifying] = useState(false);
  const [withdrawing, setWithdrawing] = useState<string | null>(null);
  const [granting, setGranting] = useState(false);
  const [grantError, setGrantError] = useState("");
  const [form, setForm] = useState({
    customerId: "", purpose: "loan_processing", channel: "web", version: "2.1",
    categories: ["AADHAAR_IN", "PAN_IN"],
  });

  const fetchRecords = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${LEDGER_URL}/consents`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setRecords(data.consents ?? []);
      setApiError("");
    } catch (e: unknown) {
      setApiError(e instanceof Error ? e.message : "Failed to connect");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchRecords(); }, [fetchRecords]);

  async function grantConsent() {
    if (!form.customerId.trim() || form.categories.length === 0) return;
    setGranting(true);
    setGrantError("");
    try {
      const res = await fetch(`${LEDGER_URL}/consent/grant`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          data_principal_id: form.customerId,
          purpose: form.purpose,
          data_categories: form.categories,
          legal_basis: "explicit_consent",
          channel: form.channel,
          version: form.version,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setForm(f => ({ ...f, customerId: "" }));
      await fetchRecords();
    } catch (e: unknown) {
      setGrantError(e instanceof Error ? e.message : "Failed to grant");
    } finally {
      setGranting(false);
    }
  }

  async function withdraw(id: string) {
    setWithdrawing(id);
    try {
      const res = await fetch(`${LEDGER_URL}/consent/${id}/withdraw`, { method: "POST" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await fetchRecords();
    } finally {
      setWithdrawing(null);
    }
  }

  async function verify() {
    if (!verifyId.trim()) return;
    setVerifying(true);
    setVerifyResult(null);
    try {
      const res = await fetch(`${LEDGER_URL}/consent/${verifyId.trim()}/verify`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      // Also fetch the record hash from proof
      let hash = "";
      try {
        const proofRes = await fetch(`${LEDGER_URL}/consent/${verifyId.trim()}/proof`);
        if (proofRes.ok) { const p = await proofRes.json(); hash = p.record_hash ?? ""; }
      } catch {}
      setVerifyResult({ valid: data.valid, reason: data.reason, hash });
    } catch (e: unknown) {
      setVerifyResult({ valid: false, reason: e instanceof Error ? e.message : "Error", hash: "" });
    } finally {
      setVerifying(false);
    }
  }

  function toggleCategory(cat: string) {
    setForm(f => ({
      ...f,
      categories: f.categories.includes(cat) ? f.categories.filter(c => c !== cat) : [...f.categories, cat],
    }));
  }

  const active = records.filter(r => r.status === "active" && !r.withdrawal_of);
  const withdrawn = records.filter(r => r.status === "withdrawn" || r.withdrawal_of);

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
          { label: "Total records", value: loading ? "…" : records.length.toString() },
          { label: "Active",        value: loading ? "…" : active.length.toString() },
          { label: "Withdrawn",     value: loading ? "…" : withdrawn.length.toString() },
          { label: "Chain",         value: apiError ? "⚠ Error" : "✓ Intact" },
        ].map(s => (
          <div key={s.label} style={{ background: "white", borderRadius: 10, padding: "16px 18px", border: "1px solid #E8E8E4" }}>
            <div style={{ fontSize: 11, color: "#71716B", marginBottom: 6, fontWeight: 500, textTransform: "uppercase", letterSpacing: "0.05em" }}>{s.label}</div>
            <div style={{ fontSize: 22, fontWeight: 700, fontFamily: "Space Grotesk, sans-serif", color: s.label === "Chain" && !apiError ? "#16a34a" : "#0D0D0B" }}>{s.value}</div>
          </div>
        ))}
      </div>

      {apiError && (
        <div style={{ marginBottom: 20, padding: "12px 16px", borderRadius: 8, background: "#FFF0F0", border: "1px solid #FDD", fontSize: 13, color: "#dc2626" }}>
          Could not reach Consent Ledger API ({apiError}). Set <code>NEXT_PUBLIC_CONSENT_LEDGER_URL</code> to override.
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 340px", gap: 20, alignItems: "start" }}>
        {/* Records */}
        <div style={{ background: "white", borderRadius: 12, border: "1px solid #E8E8E4", overflow: "hidden" }}>
          <div style={{ padding: "16px 22px", borderBottom: "1px solid #F0F0EC", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: 14, fontWeight: 600, color: "#0D0D0B" }}>Consent Records</span>
            <button onClick={fetchRecords} style={{
              padding: "4px 12px", borderRadius: 6, border: "1px solid #E8E8E4",
              background: "white", color: "#71716B", fontSize: 12, cursor: "pointer", fontFamily: "inherit",
            }}>Refresh</button>
          </div>

          {loading ? (
            <div style={{ padding: "32px 22px", textAlign: "center", color: "#A8A8A2", fontSize: 13 }}>Loading…</div>
          ) : records.length === 0 ? (
            <div style={{ padding: "32px 22px", textAlign: "center" }}>
              <div style={{ fontSize: 13, color: "#71716B", marginBottom: 8 }}>No consent records yet.</div>
              <div style={{ fontSize: 12, color: "#A8A8A2" }}>Use the form to grant your first consent.</div>
            </div>
          ) : (
            records.filter(r => !r.withdrawal_of).map((r, i) => (
              <div key={r.consent_id} style={{
                padding: "16px 22px",
                borderBottom: i < records.filter(x => !x.withdrawal_of).length - 1 ? "1px solid #F5F5F3" : "none",
                background: r.status === "withdrawn" ? "#FAFAF8" : "white",
              }}>
                <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 8 }}>
                  <div>
                    <div style={{ fontSize: 12, fontFamily: "JetBrains Mono, monospace", color: "#71716B", marginBottom: 4 }}>
                      {r.consent_id.slice(0, 8)}…
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
                      <button onClick={() => withdraw(r.consent_id)} disabled={withdrawing === r.consent_id} style={{
                        padding: "3px 10px", borderRadius: 6, border: "1px solid #FDD",
                        background: "white", color: "#dc2626", fontSize: 11, cursor: "pointer", fontFamily: "inherit",
                        opacity: withdrawing === r.consent_id ? 0.5 : 1,
                      }}>{withdrawing === r.consent_id ? "…" : "Withdraw"}</button>
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
                <div style={{ display: "flex", gap: 16, fontSize: 11, color: "#A8A8A2", flexWrap: "wrap" }}>
                  <span>Granted {fmt(r.granted_at_ms)}</span>
                  {r.withdrawn_at_ms && <span>Withdrawn {fmt(r.withdrawn_at_ms)}</span>}
                  <span>{r.channel} · v{r.version}</span>
                  <span style={{ marginLeft: "auto", fontFamily: "JetBrains Mono, monospace" }}>{r.record_hash.slice(0, 12)}…</span>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Right column */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {/* Grant form */}
          <div style={{ background: "white", borderRadius: 12, border: "1px solid #E8E8E4", padding: "20px 22px" }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: "#0D0D0B", marginBottom: 16 }}>Grant Consent</div>

            {[
              { key: "customerId", label: "Customer ID", placeholder: "CUST-1234" },
            ].map(f => (
              <div key={f.key} style={{ marginBottom: 12 }}>
                <label style={{ fontSize: 12, color: "#71716B", display: "block", marginBottom: 4 }}>{f.label}</label>
                <input value={form.customerId} onChange={e => setForm(prev => ({ ...prev, customerId: e.target.value }))}
                  placeholder={f.placeholder}
                  style={{ width: "100%", border: "1px solid #E8E8E4", borderRadius: 7, padding: "7px 10px", fontSize: 13, outline: "none", fontFamily: "inherit", boxSizing: "border-box" }} />
              </div>
            ))}

            <div style={{ marginBottom: 12 }}>
              <label style={{ fontSize: 12, color: "#71716B", display: "block", marginBottom: 4 }}>Purpose</label>
              <select value={form.purpose} onChange={e => setForm(f => ({ ...f, purpose: e.target.value }))}
                style={{ width: "100%", border: "1px solid #E8E8E4", borderRadius: 7, padding: "7px 10px", fontSize: 13, outline: "none", fontFamily: "inherit", background: "white", boxSizing: "border-box" }}>
                {PURPOSES.map(p => <option key={p} value={p}>{p.replace(/_/g, " ")}</option>)}
              </select>
            </div>

            <div style={{ marginBottom: 12 }}>
              <label style={{ fontSize: 12, color: "#71716B", display: "block", marginBottom: 6 }}>Data Categories</label>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {CATEGORIES.map(c => (
                  <button key={c} onClick={() => toggleCategory(c)} style={{
                    padding: "3px 9px", borderRadius: 5,
                    border: `1px solid ${form.categories.includes(c) ? CAT_COLOR[c] ?? "#71716B" : "#E8E8E4"}`,
                    background: form.categories.includes(c) ? `${CAT_COLOR[c] ?? "#71716B"}15` : "white",
                    color: form.categories.includes(c) ? CAT_COLOR[c] ?? "#71716B" : "#71716B",
                    fontSize: 11, fontWeight: 600, cursor: "pointer", fontFamily: "inherit",
                  }}>{c}</button>
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

            {grantError && <div style={{ fontSize: 12, color: "#dc2626", marginBottom: 10 }}>{grantError}</div>}

            <button onClick={grantConsent} disabled={granting || !form.customerId.trim() || form.categories.length === 0} style={{
              width: "100%", padding: "9px", borderRadius: 8, background: "#0D0D0B", color: "white",
              border: "none", fontSize: 13, fontWeight: 500, cursor: "pointer", fontFamily: "inherit",
              opacity: granting || !form.customerId.trim() || form.categories.length === 0 ? 0.5 : 1,
            }}>{granting ? "Granting…" : "Grant Consent"}</button>
          </div>

          {/* Verify */}
          <div style={{ background: "white", borderRadius: 12, border: "1px solid #E8E8E4", padding: "20px 22px" }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: "#0D0D0B", marginBottom: 12 }}>Verify Record</div>
            <input value={verifyId} onChange={e => { setVerifyId(e.target.value); setVerifyResult(null); }}
              placeholder="Paste a consent_id…"
              style={{ width: "100%", border: "1px solid #E8E8E4", borderRadius: 7, padding: "7px 10px", fontSize: 12, outline: "none", fontFamily: "JetBrains Mono, monospace", marginBottom: 10, boxSizing: "border-box" }} />
            <button onClick={verify} disabled={verifying || !verifyId.trim()} style={{
              width: "100%", padding: "8px", borderRadius: 8, background: "#1C6EF2", color: "white",
              border: "none", fontSize: 13, fontWeight: 500, cursor: "pointer", fontFamily: "inherit",
              opacity: verifying || !verifyId.trim() ? 0.5 : 1,
            }}>{verifying ? "Verifying…" : "Verify"}</button>
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
