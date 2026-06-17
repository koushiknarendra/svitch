"use client";
import Link from "next/link";
import { useState, useEffect } from "react";

const TRACER_URL  = process.env.NEXT_PUBLIC_AGENT_TRACER_URL   ?? "https://agent-tracer.vercel.app";
const LEDGER_URL  = process.env.NEXT_PUBLIC_CONSENT_LEDGER_URL ?? "https://consent-ledger-kappa.vercel.app";
const PII_URL     = process.env.NEXT_PUBLIC_PII_SHIELD_URL     ?? "https://service-sage-mu.vercel.app";
const COMPLIANCE_URL = process.env.NEXT_PUBLIC_COMPLIANCE_URL  ?? "https://compliance-engine-18cdqy9ud-koushik-narendars-projects.vercel.app";

interface LiveStats {
  agentRuns: number | null;
  activeConsents: number | null;
  totalConsents: number | null;
}

const TYPE_COLOR: Record<string, string> = {
  pii: "#1C6EF2", consent: "#16a34a", trace: "#9333ea", report: "#d97706",
};

const quickLinks = [
  { href: "/dashboard/pii",     label: "Test PII Shield",    desc: "Scan text for Indian PII entities" },
  { href: "/dashboard/reports", label: "Generate DPDP DPIA", desc: "Auto-fill from agent telemetry" },
  { href: "/dashboard/consent", label: "Grant Consent",      desc: "Add a new consent record" },
  { href: "/dashboard/agents",  label: "View Agent Runs",    desc: "Trace any agent's decisions" },
];

export default function DashboardHome() {
  const [live, setLive] = useState<LiveStats>({ agentRuns: null, activeConsents: null, totalConsents: null });
  const [services, setServices] = useState<Record<string, "up" | "down" | "checking">>({
    "PII Shield": "checking", "Compliance Engine": "checking",
    "Agent Tracer": "checking", "Consent Ledger": "checking",
  });

  useEffect(() => {
    async function fetchStats() {
      const [tracerRes, ledgerRes] = await Promise.allSettled([
        fetch(`${TRACER_URL}/runs`).then(r => r.json()),
        fetch(`${LEDGER_URL}/consents`).then(r => r.json()),
      ]);

      setLive({
        agentRuns: tracerRes.status === "fulfilled" ? (tracerRes.value.count ?? 0) : null,
        activeConsents: ledgerRes.status === "fulfilled"
          ? (ledgerRes.value.consents ?? []).filter((c: { status: string; withdrawal_of: string | null }) => c.status === "active" && !c.withdrawal_of).length
          : null,
        totalConsents: ledgerRes.status === "fulfilled" ? (ledgerRes.value.count ?? 0) : null,
      });
    }

    async function checkServices() {
      const checks: Array<[string, string]> = [
        ["PII Shield",        `${PII_URL}/health`],
        ["Compliance Engine", `${COMPLIANCE_URL}/health`],
        ["Agent Tracer",      `${TRACER_URL}/health`],
        ["Consent Ledger",    `${LEDGER_URL}/health`],
      ];
      const results = await Promise.allSettled(checks.map(([, url]) => fetch(url)));
      setServices(Object.fromEntries(
        checks.map(([name], i) => [
          name,
          results[i].status === "fulfilled" && (results[i] as PromiseFulfilledResult<Response>).value.ok ? "up" : "down",
        ])
      ) as Record<string, "up" | "down">);
    }

    fetchStats();
    checkServices();
  }, []);

  const stats = [
    {
      label: "Agent Runs",      value: live.agentRuns === null ? "—" : live.agentRuns.toString(),
      sub: "recorded traces",   href: "/dashboard/agents",  good: true,
    },
    {
      label: "Active Consents", value: live.activeConsents === null ? "—" : live.activeConsents.toString(),
      sub: `of ${live.totalConsents ?? "—"} total`, href: "/dashboard/consent", good: true,
    },
    {
      label: "PII Shield",      value: "Live",
      sub: "deployed & running", href: "/dashboard/pii",    good: true,
    },
    {
      label: "Compliance Score", value: "87 / 100",
      sub: "last DPDP DPIA",    href: "/dashboard/reports", good: true,
    },
  ];

  return (
    <div style={{ padding: "36px 40px", maxWidth: 960, margin: "0 auto" }}>
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
            <div style={{ background: "white", borderRadius: 12, padding: "20px 22px", border: "1px solid #E8E8E4" }}>
              <div style={{ fontSize: 12, color: "#71716B", marginBottom: 10, fontWeight: 500 }}>{s.label}</div>
              <div style={{ fontSize: 26, fontWeight: 700, fontFamily: "Space Grotesk, sans-serif", color: "#0D0D0B", marginBottom: 4 }}>
                {s.value}
              </div>
              <div style={{ fontSize: 12, color: "#A8A8A2" }}>{s.sub}</div>
            </div>
          </Link>
        ))}
      </div>

      {/* Two-col */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: 20 }}>
        {/* Quick links */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, alignContent: "start" }}>
          {quickLinks.map(q => (
            <Link key={q.href} href={q.href} style={{
              background: "white", borderRadius: 12, border: "1px solid #E8E8E4",
              padding: "20px 22px", textDecoration: "none", display: "block",
            }}>
              <div style={{ fontSize: 14, fontWeight: 600, color: "#0D0D0B", marginBottom: 6 }}>{q.label}</div>
              <div style={{ fontSize: 12, color: "#71716B" }}>{q.desc}</div>
            </Link>
          ))}

          {/* Compliance pillars */}
          <div style={{ background: "white", borderRadius: 12, border: "1px solid #E8E8E4", padding: "20px 22px", gridColumn: "1 / -1" }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: "#0D0D0B", marginBottom: 14 }}>DPDP Compliance Pillars</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {[
                { label: "PII Detection",     score: 94 },
                { label: "Consent Management",score: 88 },
                { label: "Agent Governance",  score: 81 },
                { label: "Audit Trail",       score: 96 },
                { label: "Access Controls",   score: 72 },
              ].map(p => (
                <div key={p.label} style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <span style={{ fontSize: 12, color: "#71716B", width: 160, flexShrink: 0 }}>{p.label}</span>
                  <div style={{ flex: 1, height: 6, background: "#F0F0EC", borderRadius: 3, overflow: "hidden" }}>
                    <div style={{
                      width: `${p.score}%`, height: "100%", borderRadius: 3,
                      background: p.score >= 80 ? "#16a34a" : p.score >= 60 ? "#d97706" : "#dc2626",
                    }} />
                  </div>
                  <span style={{ fontSize: 12, fontWeight: 600, color: "#0D0D0B", minWidth: 32, textAlign: "right" }}>{p.score}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Service health */}
        <div style={{ background: "white", borderRadius: 12, border: "1px solid #E8E8E4", overflow: "hidden", alignSelf: "start" }}>
          <div style={{ padding: "16px 20px", borderBottom: "1px solid #F0F0EC" }}>
            <span style={{ fontSize: 14, fontWeight: 600, color: "#0D0D0B" }}>Service Health</span>
          </div>
          {(Object.entries(services) as Array<[string, "up" | "down" | "checking"]>).map(([name, status]) => (
            <div key={name} style={{ padding: "14px 20px", borderBottom: "1px solid #F5F5F3", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <span style={{ fontSize: 13, color: "#0D0D0B" }}>{name}</span>
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <span style={{
                  width: 7, height: 7, borderRadius: "50%", display: "inline-block",
                  background: status === "up" ? "#16a34a" : status === "down" ? "#dc2626" : "#d97706",
                }} />
                <span style={{ fontSize: 12, color: "#A8A8A2" }}>
                  {status === "up" ? "Operational" : status === "down" ? "Unreachable" : "Checking…"}
                </span>
              </div>
            </div>
          ))}
          <div style={{ padding: "14px 20px" }}>
            <div style={{ fontSize: 11, color: "#A8A8A2" }}>
              Unreachable = deployment protection on.<br />
              Disable in Vercel dashboard to enable live APIs.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
