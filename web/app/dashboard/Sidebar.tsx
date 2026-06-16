"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const nav = [
  { href: "/dashboard",         label: "Overview",        icon: IconOverview },
  { href: "/dashboard/pii",     label: "PII Shield",      icon: IconShield },
  { href: "/dashboard/agents",  label: "Agent Tracer",    icon: IconTrace },
  { href: "/dashboard/reports", label: "Reports",         icon: IconReport },
  { href: "/dashboard/consent", label: "Consent Ledger",  icon: IconConsent },
];

export default function Sidebar() {
  const path = usePathname();

  return (
    <aside style={{
      width: 232, minWidth: 232, background: "#0D0D0B", display: "flex",
      flexDirection: "column", padding: "24px 0", position: "sticky", top: 0, height: "100vh",
    }}>
      {/* Logo */}
      <Link href="/" style={{ display: "flex", alignItems: "center", gap: 10, padding: "0 20px 28px", textDecoration: "none" }}>
        <span style={{
          width: 28, height: 28, borderRadius: 7, background: "#1C6EF2",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 14, fontWeight: 700, color: "white", fontFamily: "Space Grotesk, sans-serif",
        }}>S</span>
        <span style={{ color: "white", fontSize: 15, fontWeight: 600, fontFamily: "Space Grotesk, sans-serif" }}>
          Svitch
        </span>
        <span style={{
          marginLeft: "auto", fontSize: 10, fontWeight: 600, color: "#1C6EF2",
          background: "rgba(28,110,242,0.15)", borderRadius: 4, padding: "2px 6px", letterSpacing: "0.05em",
        }}>BETA</span>
      </Link>

      {/* Section label */}
      <div style={{ padding: "0 20px 10px", fontSize: 10, fontWeight: 700, color: "#4A4A44", letterSpacing: "0.1em", textTransform: "uppercase" }}>
        Compliance
      </div>

      {/* Nav */}
      <nav style={{ flex: 1, padding: "0 10px" }}>
        {nav.map(({ href, label, icon: Icon }) => {
          const active = href === "/dashboard" ? path === "/dashboard" : path.startsWith(href);
          return (
            <Link key={href} href={href} style={{
              display: "flex", alignItems: "center", gap: 10,
              padding: "9px 10px", borderRadius: 8, marginBottom: 2,
              color: active ? "white" : "#7A7A74",
              background: active ? "rgba(255,255,255,0.09)" : "transparent",
              textDecoration: "none", fontSize: 14, fontWeight: active ? 500 : 400,
              transition: "background 0.1s, color 0.1s",
            }}>
              <Icon size={16} color={active ? "#1C6EF2" : "#4A4A44"} />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Bottom */}
      <div style={{ padding: "16px 10px 0", borderTop: "1px solid rgba(255,255,255,0.07)" }}>
        <a href="https://github.com/koushiknarendra/svitch" target="_blank" rel="noreferrer" style={{
          display: "flex", alignItems: "center", gap: 10, padding: "9px 10px", borderRadius: 8,
          color: "#7A7A74", textDecoration: "none", fontSize: 14,
        }}>
          <IconGithub size={16} color="#4A4A44" />
          GitHub
        </a>
        <Link href="/dashboard" style={{
          display: "flex", alignItems: "center", gap: 10, padding: "9px 10px", borderRadius: 8,
          color: "#7A7A74", textDecoration: "none", fontSize: 14,
        }}>
          <IconDocs size={16} color="#4A4A44" />
          Docs
        </Link>
      </div>
    </aside>
  );
}

function IconOverview({ size, color }: { size: number; color: string }) {
  return <svg width={size} height={size} viewBox="0 0 16 16" fill="none"><rect x="1" y="1" width="6" height="6" rx="1.5" fill={color}/><rect x="9" y="1" width="6" height="6" rx="1.5" fill={color} opacity="0.5"/><rect x="1" y="9" width="6" height="6" rx="1.5" fill={color} opacity="0.5"/><rect x="9" y="9" width="6" height="6" rx="1.5" fill={color} opacity="0.5"/></svg>;
}
function IconShield({ size, color }: { size: number; color: string }) {
  return <svg width={size} height={size} viewBox="0 0 16 16" fill="none"><path d="M8 1.5L2 4v4c0 3.3 2.5 5.8 6 6.5 3.5-.7 6-3.2 6-6.5V4L8 1.5z" stroke={color} strokeWidth="1.4" strokeLinejoin="round"/><path d="M5.5 8l1.7 1.7L11 6" stroke={color} strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/></svg>;
}
function IconTrace({ size, color }: { size: number; color: string }) {
  return <svg width={size} height={size} viewBox="0 0 16 16" fill="none"><circle cx="3" cy="4" r="1.5" fill={color}/><circle cx="13" cy="4" r="1.5" fill={color} opacity="0.5"/><circle cx="3" cy="12" r="1.5" fill={color} opacity="0.5"/><circle cx="13" cy="12" r="1.5" fill={color} opacity="0.5"/><path d="M4.5 4h7M3 5.5v5M13 5.5v5M4.5 12h7" stroke={color} strokeWidth="1.2" strokeLinecap="round" opacity="0.5"/></svg>;
}
function IconReport({ size, color }: { size: number; color: string }) {
  return <svg width={size} height={size} viewBox="0 0 16 16" fill="none"><rect x="2.5" y="1.5" width="11" height="13" rx="1.5" stroke={color} strokeWidth="1.4"/><path d="M5 5.5h6M5 8h6M5 10.5h4" stroke={color} strokeWidth="1.2" strokeLinecap="round"/></svg>;
}
function IconConsent({ size, color }: { size: number; color: string }) {
  return <svg width={size} height={size} viewBox="0 0 16 16" fill="none"><rect x="3" y="7" width="10" height="7.5" rx="1.5" stroke={color} strokeWidth="1.4"/><path d="M5.5 7V5a2.5 2.5 0 015 0v2" stroke={color} strokeWidth="1.4" strokeLinecap="round"/><circle cx="8" cy="10.5" r="1" fill={color}/></svg>;
}
function IconGithub({ size, color }: { size: number; color: string }) {
  return <svg width={size} height={size} viewBox="0 0 16 16" fill={color}><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/></svg>;
}
function IconDocs({ size, color }: { size: number; color: string }) {
  return <svg width={size} height={size} viewBox="0 0 16 16" fill="none"><path d="M2 13V3a1 1 0 011-1h6.586a1 1 0 01.707.293l2.414 2.414A1 1 0 0113 5.414V13a1 1 0 01-1 1H3a1 1 0 01-1-1z" stroke={color} strokeWidth="1.4"/><path d="M9 2v4h4" stroke={color} strokeWidth="1.4" strokeLinejoin="round"/></svg>;
}
