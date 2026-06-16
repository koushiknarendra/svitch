"use client";
import Link from "next/link";

const stats = [
  { label: "PII Shields Today",  value: "1,847",  delta: "+12%",  good: true,  href: "/dashboard/pii" },
  { label: "Agent Runs (24h)",   value: "94",     delta: "+8",    good: true,  href: "/dashboard/agents" },
  { label: "Active Consents",    value: "3,210",  delta: "−14",   good: false, href: "/dashboard/consent" },
  { label: "Compliance Score",   value: "87 / 100", delta: "+3", good: true,  href: "/dashboard/reports" },
];

const activity = [
  { time: "2 min ago",  type: "pii",     msg: "Aadhaar redacted in loan-agent prompt",     agent: "loan-processor-v3" },
  { time: "6 min ago",  type: "consent", msg: "Consent granted — KYC, purpose: kyc_verification", agent: "onboarding-agent" },
  { time: "14 min ago", type: "trace",   msg: "Agent run traced — 7 steps, 2 PII touches",  agent: "fraud-detector" },
  { time: "22 min ago", type: "report",  msg: "DPDP DPIA generated — score 87/100",         agent: "compliance-job" },
  { time: "41 min ago", type: "pii",     msg: "UPI ID + mobile blocked in response",         agent: "support-agent-v1" },
  { time: "1h ago",     type: "consent", msg: "Consent withdrawn — CUST-8821",               agent: "withdrawal-handler" },
];

const typeColor: Record<string, string> = {
  pii: "#1C6EF2", consent: "#16a34a", trace: "#9333ea", report: "#d97706",
};
const typeLabel: Record<string, string> = {
  pii: "PII", consent: "CONSENT", trace: "TRACE", report: "REPORT",
};

const quickLinks = [
  { href: "/dashboard/pii",     label: "Test PII Shield",       desc: "Scan text for Indian PII entities" },
  { href: "/dashboard/reports", label: "Generate DPDP DPIA",    desc: "Auto-fill from agent telemetry" },
  { href: "/dashboard/consent", label: "Grant Consent",         desc: "Add a new consent record" },
  { href: "/dashboard/agents",  label: "View Agent Runs",       desc: "Trace any agent's decisions" },
];

export default function DashboardHome() {
  return (
    <div style={{ padding: "36px 40px", maxWidth: 960, margin: "0 auto" }}>
      {/* Header */}
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, margin: "0 0 6px", fontFamily: "Space Grotesk, sans-serif", color: "#0D0D0B" }}>
          Compliance Overview
        </h1>
        <p style={{ margin: 0, fontSize: 14, color: "#71716B" }}>
          Real-time AI governance for your regulated workflows
        </p>
      </div>

      {/* Stat cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 32 }}>
        {stats.map(s => (
          <Link key={s.label} href={s.href} style={{ textDecoration: "none" }}>
            <div style={{
              background: "white", borderRadius: 12, padding: "20px 22px",
              border: "1px solid #E8E8E4", cursor: "pointer",
              transition: "box-shadow 0.15s",
            }}>
              <div style={{ fontSize: 12, color: "#71716B", marginBottom: 10, fontWeight: 500 }}>{s.label}</div>
              <div style={{ fontSize: 26, fontWeight: 700, fontFamily: "Space Grotesk, sans-serif", color: "#0D0D0B", marginBottom: 6 }}>
                {s.value}
              </div>
              <div style={{ fontSize: 12, color: s.good ? "#16a34a" : "#dc2626", fontWeight: 500 }}>{s.delta} vs yesterday</div>
            </div>
          </Link>
        ))}
      </div>

      {/* Two-col: activity + quick links */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: 20 }}>

        {/* Activity feed */}
        <div style={{ background: "white", borderRadius: 12, border: "1px solid #E8E8E4", overflow: "hidden" }}>
          <div style={{ padding: "18px 22px", borderBottom: "1px solid #F0F0EC" }}>
            <span style={{ fontSize: 14, fontWeight: 600, color: "#0D0D0B" }}>Recent Activity</span>
          </div>
          {activity.map((a, i) => (
            <div key={i} style={{
              display: "flex", alignItems: "flex-start", gap: 12,
              padding: "14px 22px", borderBottom: i < activity.length - 1 ? "1px solid #F5F5F3" : "none",
            }}>
              <span style={{
                marginTop: 1, fontSize: 9, fontWeight: 700, letterSpacing: "0.06em",
                color: typeColor[a.type], background: `${typeColor[a.type]}18`,
                borderRadius: 4, padding: "3px 6px", whiteSpace: "nowrap",
              }}>{typeLabel[a.type]}</span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13, color: "#0D0D0B", marginBottom: 2 }}>{a.msg}</div>
                <div style={{ fontSize: 11, color: "#A8A8A2" }}>
                  <span style={{ fontFamily: "JetBrains Mono, monospace" }}>{a.agent}</span>
                  {" · "}{a.time}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Quick links */}
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {quickLinks.map(q => (
            <Link key={q.href} href={q.href} style={{
              background: "white", borderRadius: 12, border: "1px solid #E8E8E4",
              padding: "18px 20px", textDecoration: "none", display: "block",
            }}>
              <div style={{ fontSize: 14, fontWeight: 600, color: "#0D0D0B", marginBottom: 4 }}>{q.label}</div>
              <div style={{ fontSize: 12, color: "#71716B" }}>{q.desc}</div>
            </Link>
          ))}
        </div>
      </div>

      {/* Services status */}
      <div style={{ marginTop: 20, background: "white", borderRadius: 12, border: "1px solid #E8E8E4" }}>
        <div style={{ padding: "18px 22px", borderBottom: "1px solid #F0F0EC" }}>
          <span style={{ fontSize: 14, fontWeight: 600, color: "#0D0D0B" }}>Service Health</span>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)" }}>
          {[
            { name: "PII Shield",       status: "live",    url: "service-sage-mu.vercel.app" },
            { name: "Compliance Engine",status: "live",    url: "compliance-engine.vercel.app" },
            { name: "Agent Tracer",     status: "local",   url: "not deployed" },
            { name: "Consent Ledger",   status: "local",   url: "not deployed" },
          ].map((s, i) => (
            <div key={i} style={{
              padding: "16px 22px",
              borderRight: i < 3 ? "1px solid #F0F0EC" : "none",
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
                <span style={{
                  width: 7, height: 7, borderRadius: "50%",
                  background: s.status === "live" ? "#16a34a" : "#d97706", display: "inline-block",
                }}/>
                <span style={{ fontSize: 13, fontWeight: 500, color: "#0D0D0B" }}>{s.name}</span>
              </div>
              <div style={{ fontSize: 11, color: "#A8A8A2", fontFamily: "JetBrains Mono, monospace" }}>{s.url}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
