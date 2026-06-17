"use client";
import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  async function submit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });
    if (res.ok) {
      router.push("/dashboard");
    } else {
      setError("Incorrect password");
      setLoading(false);
    }
  }

  return (
    <div style={{
      minHeight: "100vh", background: "#0D0D0B",
      display: "flex", alignItems: "center", justifyContent: "center",
    }}>
      <div style={{
        background: "#1A1A18", border: "1px solid rgba(255,255,255,0.08)",
        borderRadius: 16, padding: "40px 44px", width: 360,
      }}>
        {/* Logo */}
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 32 }}>
          <span style={{
            width: 32, height: 32, borderRadius: 8, background: "#1C6EF2",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 16, fontWeight: 700, color: "white", fontFamily: "Space Grotesk, sans-serif",
          }}>S</span>
          <span style={{ color: "white", fontSize: 17, fontWeight: 600, fontFamily: "Space Grotesk, sans-serif" }}>
            Svitch Dashboard
          </span>
        </div>

        <h1 style={{
          fontSize: 20, fontWeight: 700, color: "white", margin: "0 0 6px",
          fontFamily: "Space Grotesk, sans-serif",
        }}>Sign in</h1>
        <p style={{ fontSize: 13, color: "#71716B", margin: "0 0 28px" }}>
          Enter your dashboard password to continue
        </p>

        <form onSubmit={submit}>
          <label style={{ fontSize: 12, fontWeight: 500, color: "#A8A8A2", display: "block", marginBottom: 6 }}>
            Password
          </label>
          <input
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            autoFocus
            required
            placeholder="••••••••"
            style={{
              width: "100%", padding: "10px 14px", borderRadius: 8,
              border: `1px solid ${error ? "#dc2626" : "rgba(255,255,255,0.1)"}`,
              background: "rgba(255,255,255,0.04)", color: "white", fontSize: 14,
              fontFamily: "inherit", outline: "none", boxSizing: "border-box",
              marginBottom: 8,
            }}
          />
          {error && (
            <div style={{ fontSize: 12, color: "#dc2626", marginBottom: 12 }}>{error}</div>
          )}
          <button
            type="submit"
            disabled={loading || !password}
            style={{
              width: "100%", padding: "10px", borderRadius: 8,
              background: "#1C6EF2", color: "white", border: "none",
              fontSize: 14, fontWeight: 600, cursor: loading ? "wait" : "pointer",
              opacity: loading || !password ? 0.7 : 1, fontFamily: "inherit",
              marginTop: error ? 0 : 12,
            }}
          >
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <p style={{ fontSize: 11, color: "#4A4A44", textAlign: "center", marginTop: 24, marginBottom: 0 }}>
          Set <code style={{ fontFamily: "JetBrains Mono, monospace", color: "#71716B" }}>DASHBOARD_PASSWORD</code> in Vercel env vars
        </p>
      </div>
    </div>
  );
}
