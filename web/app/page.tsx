"use client";

import { useState, useEffect, useRef, useCallback, ReactNode } from "react";

// ─── Constants ───────────────────────────────────────────────────────────────
const ACCENT    = "#2A6FDB";
const ACCENT_BG = "#EAF1FC";
const MONO      = "'DM Mono', monospace";
const CODE_FONT = "'JetBrains Mono', monospace";
const DISPLAY   = "'Space Grotesk', sans-serif";

const DEMO_TEXT =
  "Please verify customer Aadhaar 4123 8890 0123 and PAN ABCDE1234F. Refund via UPI ravi@okhdfc, bank IFSC HDFC0001234. Contact 9876543210.";

const CODE_TEXT = [
  "from svitch import Svitch",
  "from openai import OpenAI",
  "",
  "client = Svitch.wrap(OpenAI())   # one line. done.",
  "# PII redacted · queries routed · every call logged",
  "",
  "client.chat.completions.create(",
  '    model="auto",               # Svitch picks the cheapest fit',
  '    messages=[{"role": "user", "content": user_input}],',
  ")",
].join("\n");

// ─── PII Detection ────────────────────────────────────────────────────────────
interface Entity {
  type: string;
  value: string;
  start: number;
  end: number;
  masked: string;
  pos: string;
}

const DETECTORS: Array<{ type: string; re: RegExp; mask: (v: string) => string }> = [
  { type: "AADHAAR", re: /\b\d{4}\s\d{4}\s\d{4}\b/g,        mask: (v) => "XXXX XXXX " + v.replace(/\s/g, "").slice(-4) },
  { type: "PAN",     re: /\b[A-Z]{5}[0-9]{4}[A-Z]\b/g,      mask: (v) => v.slice(0, 2) + "XXX" + v.slice(5) },
  { type: "IFSC",    re: /\b[A-Z]{4}0[A-Z0-9]{6}\b/g,       mask: (v) => v },
  { type: "UPI",     re: /\b[a-zA-Z0-9._-]{2,}@[a-zA-Z]{2,}\b/g, mask: (v) => { const [u, d] = v.split("@"); return u.slice(0, 3) + "***@" + d; } },
  { type: "PHONE",   re: /\b[6-9]\d{9}\b/g,                  mask: (v) => v.slice(0, 2) + "XXXX" + v.slice(-4) },
];

function detectAll(text: string): Entity[] {
  const found: Entity[] = [];
  DETECTORS.forEach((d) => {
    const re = new RegExp(d.re.source, d.re.flags);
    let m: RegExpExecArray | null;
    while ((m = re.exec(text)) !== null) {
      found.push({ type: d.type, value: m[0], start: m.index, end: m.index + m[0].length, masked: d.mask(m[0]), pos: `chars ${m.index}–${m.index + m[0].length}` });
    }
  });
  found.sort((a, b) => a.start - b.start);
  const out: Entity[] = [];
  let lastEnd = -1;
  found.forEach((f) => { if (f.start >= lastEnd) { out.push(f); lastEnd = f.end; } });
  return out;
}

// ─── Sub-components ───────────────────────────────────────────────────────────
function Annotated({ text, entities }: { text: string; entities: Entity[] }) {
  const nodes: ReactNode[] = [];
  let last = 0;
  entities.forEach((e, i) => {
    if (e.start > last) nodes.push(text.slice(last, e.start));
    nodes.push(<span key={i} style={{ borderBottom: `1px solid ${ACCENT}`, background: ACCENT_BG, padding: "0 1px" }}>{text.slice(e.start, e.end)}</span>);
    last = e.end;
  });
  if (last < text.length) nodes.push(text.slice(last));
  return <>{nodes}</>;
}

function HeroTerminal({ step }: { step: number }) {
  const Hl = ({ children }: { children: ReactNode }) => (
    <span style={{ borderBottom: `1px solid ${ACCENT}`, background: ACCENT_BG }}>{children}</span>
  );
  const lines: ReactNode[] = [
    <div key={0}><span style={{ color: "#9A9A92" }}>$ </span>svitch shield wrap openai</div>,
    <div key={1} style={{ color: ACCENT }}>✓ client wrapped · context preserved</div>,
    <div key={2} style={{ height: 10 }} />,
    <div key={3} style={{ color: "#9A9A92" }}>→ scanning outbound prompt</div>,
    <div key={4} style={{ lineHeight: 1.8 }}>
      {`  "verify Aadhaar `}<Hl>4123 8890 0123</Hl>{", PAN "}<Hl>ABCDE1234F</Hl>{","}
      <br />{"   UPI "}<Hl>ravi@okhdfc</Hl>{`"`}
    </div>,
    <div key={5} style={{ height: 10 }} />,
    <div key={6}><span style={{ color: ACCENT }}>⚠ 3 entities redacted</span>{" · 0 bytes to model"}</div>,
  ];
  const visible = lines.slice(0, Math.min(step, lines.length));
  return (
    <div style={{ fontFamily: CODE_FONT, fontSize: 13, color: "#0D0D0B", lineHeight: 1.65 }}>
      {visible.map((l, i) => <div key={i} style={{ marginBottom: 2 }}>{l}</div>)}
      <div><span className="blink" style={{ color: ACCENT }}>▍</span></div>
    </div>
  );
}

function CodeBlock() {
  const lines: Array<Array<{ t: string; c?: string }>> = [
    [{ c: ACCENT, t: "from" }, { t: " svitch " }, { c: ACCENT, t: "import" }, { t: " Svitch" }],
    [{ c: ACCENT, t: "from" }, { t: " openai " }, { c: ACCENT, t: "import" }, { t: " OpenAI" }],
    [{ t: " " }],
    [{ t: "client = Svitch.wrap(OpenAI())   " }, { c: "#9A9A92", t: "# one line. done." }],
    [{ c: "#9A9A92", t: "# PII redacted · queries routed · every call logged" }],
    [{ t: " " }],
    [{ t: "client.chat.completions.create(" }],
    [{ t: "    model=" }, { c: ACCENT, t: '"auto"' }, { t: ",               " }, { c: "#9A9A92", t: "# Svitch picks the cheapest fit" }],
    [{ t: '    messages=[{"role": "user", "content": user_input}],' }],
    [{ t: ")" }],
  ];
  return (
    <>
      {lines.map((line, i) => (
        <div key={i}>
          {line.map((part, j) => <span key={j} style={part.c ? { color: part.c } : undefined}>{part.t}</span>)}
        </div>
      ))}
    </>
  );
}

// ─── Canvas hook ──────────────────────────────────────────────────────────────
function useHeroCanvas(ref: React.RefObject<HTMLCanvasElement | null>) {
  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    let w = 0, h = 0, lanes: number[] = [], junctions: number[] = [];
    interface Pkt { x: number; y: number; lane: number; speed: number; switching: boolean; fromLane: number; toLane: number; sx: number; ex: number; hist: Array<{x:number;y:number}>; }
    let packets: Pkt[] = [];
    const SWITCH_LEN = 72;

    const setup = () => {
      const N = 5, top = h * 0.17, bot = h * 0.83;
      lanes = Array.from({ length: N }, (_, i) => Math.round(top + (bot - top) * (i / (N - 1))));
      junctions = [];
      for (let x = 172 * 0.6; x < w; x += 172) junctions.push(Math.round(x));
      packets = Array.from({ length: 6 }, (_, i) => {
        const lane = Math.floor(Math.random() * N);
        return { x: (i / 6) * w + Math.random() * 50, y: lanes[lane], lane, speed: 0.45 + Math.random() * 0.45, switching: false, fromLane: lane, toLane: lane, sx: 0, ex: 0, hist: [] };
      });
    };

    const resize = () => {
      const dpr = window.devicePixelRatio || 1;
      const r = canvas.getBoundingClientRect();
      w = r.width; h = r.height;
      if (!w || !h) return;
      canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      setup();
    };
    resize();
    window.addEventListener("resize", resize);

    const draw = () => {
      if (!w || !h || !lanes.length) return;
      ctx.clearRect(0, 0, w, h);
      const topY = lanes[0], botY = lanes[lanes.length - 1];
      ctx.strokeStyle = "rgba(13,13,11,0.07)"; ctx.lineWidth = 1; ctx.beginPath();
      lanes.forEach((y) => { ctx.moveTo(0, y + 0.5); ctx.lineTo(w, y + 0.5); });
      ctx.stroke();
      junctions.forEach((jx) => {
        ctx.strokeStyle = "rgba(13,13,11,0.045)"; ctx.beginPath(); ctx.moveTo(jx + 0.5, topY - 9); ctx.lineTo(jx + 0.5, botY + 9); ctx.stroke();
        ctx.fillStyle = "rgba(13,13,11,0.15)"; lanes.forEach((y) => ctx.fillRect(jx - 1, y - 1, 2, 2));
      });
      packets.forEach((p) => {
        p.x += p.speed;
        if (!p.switching) {
          p.y = lanes[p.lane];
          junctions.forEach((jx) => {
            if (p.x >= jx && p.x - p.speed < jx && Math.random() < 0.5) {
              const dir = Math.random() < 0.5 ? -1 : 1; let target = p.lane + dir;
              if (target < 0) target = p.lane + 1; if (target >= lanes.length) target = p.lane - 1;
              if (target !== p.lane) { p.switching = true; p.fromLane = p.lane; p.toLane = target; p.sx = jx; p.ex = jx + SWITCH_LEN; }
            }
          });
        } else {
          const tt = Math.min(1, (p.x - p.sx) / (p.ex - p.sx)), e = tt * tt * (3 - 2 * tt);
          p.y = lanes[p.fromLane] + (lanes[p.toLane] - lanes[p.fromLane]) * e;
          ctx.strokeStyle = "rgba(42,111,219,0.22)"; ctx.beginPath(); ctx.moveTo(p.sx, lanes[p.fromLane]); ctx.lineTo(p.ex, lanes[p.toLane]); ctx.stroke();
          ctx.fillStyle = "rgba(42,111,219,0.5)"; ctx.fillRect(p.sx - 2, lanes[p.fromLane] - 2, 4, 4); ctx.fillRect(p.ex - 2, lanes[p.toLane] - 2, 4, 4);
          if (tt >= 1) { p.switching = false; p.lane = p.toLane; p.y = lanes[p.lane]; }
        }
        if (p.x > w + 30) { p.x = -30; p.lane = Math.floor(Math.random() * lanes.length); p.switching = false; p.y = lanes[p.lane]; p.hist = []; }
        p.hist.push({ x: p.x, y: p.y }); if (p.hist.length > 10) p.hist.shift();
        p.hist.forEach((h, i) => { ctx.fillStyle = `rgba(42,111,219,${0.24 * (i / p.hist.length)})`; ctx.fillRect(h.x - 1, h.y - 1, 2, 2); });
        ctx.fillStyle = "rgba(42,111,219,0.78)"; ctx.fillRect(p.x - 2, p.y - 2, 4, 4);
      });
    };
    const id = setInterval(draw, 33);
    return () => { clearInterval(id); window.removeEventListener("resize", resize); };
  }, [ref]);
}

// ─── Main ─────────────────────────────────────────────────────────────────────
export default function Home() {
  const [input,    setInput]    = useState(DEMO_TEXT);
  const [results,  setResults]  = useState<Entity[] | null>(null);
  const [copied,   setCopied]   = useState(false);
  const [heroStep, setHeroStep] = useState(0);
  const [wmSize,   setWmSize]   = useState("200px");

  const canvasRef  = useRef<HTMLCanvasElement>(null);
  const wordmarkRef = useRef<HTMLDivElement>(null);
  const copyTimer  = useRef<ReturnType<typeof setTimeout> | null>(null);

  useHeroCanvas(canvasRef);

  useEffect(() => {
    const id = setInterval(() => setHeroStep((s) => (s + 1 > 11 ? 0 : s + 1)), 620);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    const fit = () => {
      const el = wordmarkRef.current;
      if (!el?.parentElement) return;
      const parent = el.parentElement;
      const cs = getComputedStyle(parent);
      const avail = parent.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
      if (avail <= 0) return;
      const cur = parseFloat(getComputedStyle(el).fontSize) || 200;
      const sw = el.scrollWidth;
      if (sw <= 0) return;
      const size = Math.round((avail / sw) * cur * 10) / 10;
      if (Math.abs(size - cur) > 0.5) setWmSize(size + "px");
    };
    fit();
    const t = setTimeout(fit, 300);
    window.addEventListener("resize", fit);
    document.fonts?.ready?.then(fit);
    return () => { clearTimeout(t); window.removeEventListener("resize", fit); };
  }, []);

  const onDetect = useCallback(() => setResults(detectAll(input)), [input]);
  const onClear  = useCallback(() => setResults(null), []);
  const copyCode = useCallback(() => {
    try { navigator.clipboard?.writeText(CODE_TEXT); } catch {}
    setCopied(true);
    if (copyTimer.current) clearTimeout(copyTimer.current);
    copyTimer.current = setTimeout(() => setCopied(false), 1400);
  }, []);

  return (
    <div style={{ background: "#FAFAF8", minHeight: "100vh", fontFamily: "'Satoshi', system-ui, sans-serif" }}>

      {/* ── NAV ── */}
      <nav style={{ position: "sticky", top: 0, zIndex: 50, background: "rgba(250,250,248,0.88)", backdropFilter: "saturate(180%) blur(8px)", borderBottom: "1px solid #E8E8E4" }}>
        <div className="r-nav-inner">
          {/* Logo mark + wordmark */}
          <a href="#" style={{ display: "flex", alignItems: "center", gap: 8, textDecoration: "none" }}>
            <span style={{ width: 22, height: 22, background: ACCENT, borderRadius: 4, display: "inline-flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                <path d="M2 6h4M6 6l2.5-2.5M6 6l2.5 2.5" stroke="#fff" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </span>
            <span style={{ fontFamily: DISPLAY, fontSize: 18, fontWeight: 700, letterSpacing: "-0.03em", color: "#0D0D0B" }}>Svitch</span>
          </a>

          <div className="r-nav-links" style={{ fontFamily: MONO, fontSize: 13, color: "#71716B" }}>
            <a href="#process" style={{ color: "#71716B" }}>Products</a>
            <a href="#demo"    style={{ color: "#71716B" }}>Docs</a>
            <a href="#code"    style={{ color: "#71716B" }}>Pricing</a>
            <a href="https://github.com/koushiknarendra/svitch" target="_blank" style={{ color: "#71716B" }}>GitHub</a>
          </div>

          <a href="#demo" className="r-nav-cta" style={{ fontFamily: MONO, fontSize: 13, color: ACCENT, whiteSpace: "nowrap" }}>
            <span className="r-cta-full">Request access</span>
            <span className="r-cta-short">Get access</span>
            &nbsp;→
          </a>
        </div>
      </nav>

      {/* ── HERO ── */}
      <section style={{ position: "relative", overflow: "hidden" }}>
        <canvas ref={canvasRef} style={{ position: "absolute", inset: 0, width: "100%", height: "100%", zIndex: 0, pointerEvents: "none" }} />
        <div style={{ position: "relative", zIndex: 1 }}>
          <div className="r-section">
            <div className="r-hero-grid">
              <div>
                <div style={{ fontFamily: MONO, fontSize: 11, letterSpacing: "0.12em", textTransform: "uppercase", color: "#71716B", marginBottom: 24 }}>
                  Svitch · the AI control layer
                </div>
                <h1 className="r-hero-h1">
                  Your AI stack.<br />Your data.<br /><span style={{ color: ACCENT }}>Always.</span>
                </h1>
                <p className="r-hero-p">
                  Switch between LLMs without losing context. Block every data leak. Cut costs 80%. Prove compliance on demand.
                </p>
                <div style={{ display: "flex", alignItems: "center", gap: 28, flexWrap: "wrap" }}>
                  <a href="#demo" style={{ fontFamily: MONO, fontSize: 14, color: ACCENT }}>Get early access&nbsp;→</a>
                  <a href="https://github.com/koushiknarendra/svitch" target="_blank" style={{ fontFamily: MONO, fontSize: 14, color: "#71716B" }}>View on GitHub</a>
                </div>
              </div>

              {/* Terminal */}
              <div style={{ border: "1px solid #E8E8E4", background: "#FFFFFF", borderRadius: 6, overflow: "hidden" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "11px 14px", borderBottom: "1px solid #E8E8E4", background: "#F4F3F0" }}>
                  <span style={{ width: 9, height: 9, borderRadius: "50%", background: "#D8D8D2", display: "inline-block" }} />
                  <span style={{ width: 9, height: 9, borderRadius: "50%", background: "#D8D8D2", display: "inline-block" }} />
                  <span style={{ width: 9, height: 9, borderRadius: "50%", background: "#D8D8D2", display: "inline-block" }} />
                  <span style={{ fontFamily: MONO, fontSize: 11, color: "#9A9A92", marginLeft: 8 }}>svitch — shield</span>
                </div>
                <div style={{ padding: "20px 18px", minHeight: 200 }}>
                  <HeroTerminal step={heroStep} />
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <div className="r-outer"><div style={{ borderTop: "1px solid #E8E8E4" }} /></div>

      {/* ── LOGO STRIP ── */}
      {(() => {
        const names = ["Razorbank","Meridian","Kosh","Northwind","Tessellate","Anvaya","Settl"];
        // Duplicate for seamless loop
        const items = [...names, ...names];
        return (
          <section style={{ borderBottom: "1px solid #E8E8E4", padding: "20px 0" }}>
            <div style={{ fontFamily: MONO, fontSize: 10, letterSpacing: "0.12em", color: "#B0B0A8", textAlign: "center", marginBottom: 14 }}>
              TRUSTED BY TEAMS AT
            </div>
            <div className="r-marquee-outer">
              <div className="r-marquee-track">
                {items.map((name, i) => (
                  <span key={i} style={{ display: "inline-flex", alignItems: "center", gap: 0 }}>
                    <span style={{ fontSize: 15, fontWeight: 700, letterSpacing: "-0.02em", color: "#B0B0A8", padding: "0 36px", whiteSpace: "nowrap" }}>
                      {name}
                    </span>
                    <span style={{ width: 3, height: 3, borderRadius: "50%", background: "#D8D8D2", display: "inline-block", flexShrink: 0 }} />
                  </span>
                ))}
              </div>
            </div>
          </section>
        );
      })()}

      {/* ── PROCESS ── */}
      <section id="process" style={{ background: "#FFFFFF", borderTop: "1px solid #E8E8E4", borderBottom: "1px solid #E8E8E4" }}>
        <div className="r-section">
          <div style={{ fontFamily: MONO, fontSize: 11, letterSpacing: "0.12em", color: "#71716B", marginBottom: 18 }}>HOW IT WORKS</div>
          <h2 className="r-h2-lg">
            One line of code. Five layers of <span style={{ color: ACCENT }}>protection.</span>
          </h2>
          <div className="r-grid-3">
            {[
              { num: "[01]", title: "Wrap",   desc: <p style={{ fontSize: 15, lineHeight: 1.6, color: "#71716B", margin: 0 }}>Wrap any client — <span style={{ fontFamily: CODE_FONT, fontSize: 13, color: "#0D0D0B" }}>svitch.wrap(openai.client)</span>. Context and tools carry across every model.</p> },
              { num: "[02]", title: "Shield", desc: <p style={{ fontSize: 15, lineHeight: 1.6, color: "#71716B", margin: 0 }}>PII is detected and redacted before the prompt ever leaves your codebase. Eleven Indian entity types, on by default.</p> },
              { num: "[03]", title: "Route",  desc: <p style={{ fontSize: 15, lineHeight: 1.6, color: "#71716B", margin: 0 }}>Each query is complexity-scored. Routine work is auto-routed to a cheaper model — up to 80% off.</p> },
            ].map(({ num, title, desc }) => (
              <div key={num} className="r-process-step">
                <div style={{ fontFamily: MONO, fontSize: 13, color: "#71716B", marginBottom: 10 }}>{num}</div>
                <div style={{ fontSize: 18, fontWeight: 700, letterSpacing: "-0.02em", marginBottom: 18 }}>{title}</div>
                {desc}
              </div>
            ))}
          </div>

          {/* Connecting trace — desktop only */}
          <div className="r-process-line" style={{ position: "relative", margin: "0 0 0", height: 1, background: "#D0D0CC" }}>
            {[16.66, 50, 83.33].map((pct) => (
              <span key={pct} style={{ position: "absolute", left: `calc(${pct}% - 3px)`, top: -2.5, width: 6, height: 6, borderRadius: "50%", background: ACCENT, display: "inline-block" }} />
            ))}
          </div>
        </div>
      </section>

      {/* ── LIVE DEMO ── */}
      <section id="demo" style={{ background: "#F4F7F5", borderBottom: "1px solid #E8E8E4" }}>
        <div className="r-section">
          <div className="r-grid-demo">
            <div className="r-sticky">
              <div style={{ fontFamily: MONO, fontSize: 11, letterSpacing: "0.1em", color: "#71716B", marginBottom: 18 }}>SVITCH SHIELD · LIVE DEMO</div>
              <h2 className="r-h2-demo">
                Paste any text. Watch PII <span style={{ color: ACCENT }}>disappear.</span>
              </h2>
              <p style={{ fontSize: 15, lineHeight: 1.65, color: "#71716B", margin: 0 }}>
                Runs entirely in your browser — the same engine runs server-side, before any model sees a single token.
              </p>
            </div>

            <div style={{ background: "#FFFFFF", border: "1px solid #E8E8E4", borderRadius: 6, padding: 20 }}>
              <div style={{ fontFamily: MONO, fontSize: 11, color: "#71716B", marginBottom: 10 }}>INPUT</div>
              <textarea
                value={input}
                onChange={(e) => { setInput(e.target.value); setResults(null); }}
                spellCheck={false}
                style={{ width: "100%", height: 108, resize: "vertical", border: "1px solid #E8E8E4", borderRadius: 4, background: "#F4F3F0", padding: 13, fontSize: 13, lineHeight: 1.6, color: "#0D0D0B", outline: "none", fontFamily: CODE_FONT, boxSizing: "border-box" }}
              />
              <div style={{ display: "flex", alignItems: "center", gap: 16, marginTop: 14 }}>
                <button onClick={onDetect} style={{ fontFamily: "'Satoshi',sans-serif", fontSize: 14, fontWeight: 500, color: "#0D0D0B", background: "transparent", border: "1px solid #0D0D0B", borderRadius: 4, padding: "9px 18px", cursor: "pointer" }}>
                  Detect &amp; Redact
                </button>
                <button onClick={onClear} style={{ fontFamily: MONO, fontSize: 12, color: "#71716B", background: "transparent", border: "none", cursor: "pointer" }}>
                  clear
                </button>
              </div>

              {results && (
                <div>
                  <div style={{ fontFamily: MONO, fontSize: 11, color: "#71716B", margin: "22px 0 10px" }}>
                    ANNOTATED · {results.length} {results.length === 1 ? "ENTITY" : "ENTITIES"} FOUND
                  </div>
                  <div style={{ border: "1px solid #E8E8E4", borderRadius: 4, background: "#FBFBF9", padding: 14, fontFamily: CODE_FONT, fontSize: 13, lineHeight: 1.85, color: "#0D0D0B", whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
                    <Annotated text={input} entities={results} />
                  </div>
                  {results.length > 0 && (
                    <div style={{ marginTop: 18, border: "1px solid #E8E8E4", borderRadius: 4, overflow: "hidden" }}>
                      <div style={{ display: "grid", gridTemplateColumns: "1.1fr 1.6fr 1.1fr", background: "#F4F3F0", borderBottom: "1px solid #E8E8E4" }}>
                        {["Entity type","Value","Position"].map((h, i) => (
                          <div key={h} style={{ padding: "9px 14px", fontSize: 12, fontWeight: 500, color: "#71716B", borderRight: i < 2 ? "1px solid #E8E8E4" : undefined }}>{h}</div>
                        ))}
                      </div>
                      {results.map((row, i) => (
                        <div key={i} style={{ display: "grid", gridTemplateColumns: "1.1fr 1.6fr 1.1fr", borderTop: "1px solid #E8E8E4" }}>
                          <div style={{ padding: "9px 14px", fontFamily: MONO, fontSize: 12, color: ACCENT, borderRight: "1px solid #E8E8E4" }}>{row.type}</div>
                          <div style={{ padding: "9px 14px", fontFamily: MONO, fontSize: 12, color: "#0D0D0B", borderRight: "1px solid #E8E8E4", wordBreak: "break-all" }}>{row.masked}</div>
                          <div style={{ padding: "9px 14px", fontFamily: MONO, fontSize: 12, color: "#71716B" }}>{row.pos}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* ── CODE ── */}
      <section id="code" style={{ background: "#FFFFFF", borderBottom: "1px solid #E8E8E4" }}>
        <div className="r-section">
          <div className="r-grid-code">
            <div>
              <div style={{ fontFamily: MONO, fontSize: 11, letterSpacing: "0.12em", color: "#71716B", marginBottom: 18 }}>THE SDK</div>
              <h2 className="r-h2-code">
                Three lines.<br />Zero <span style={{ color: ACCENT }}>friction.</span>
              </h2>
              <p style={{ fontSize: 16, lineHeight: 1.65, color: "#71716B", margin: "0 0 18px" }}>
                Drop Svitch in front of the SDK you already use. No prompt rewrites, no proxy config, no new mental model.
              </p>
              <p style={{ fontFamily: MONO, fontSize: 12, lineHeight: 2, color: "#71716B", margin: 0 }}>
                OpenAI · Anthropic · Gemini · Llama<br />+ any OpenAI-compatible endpoint
              </p>
            </div>
            <div style={{ position: "relative", background: "#F4F3F0", border: "1px solid #E8E8E4", borderRadius: 4, minWidth: 0, overflow: "hidden" }}>
              <button onClick={copyCode} style={{ position: "absolute", top: 12, right: 12, fontFamily: MONO, fontSize: 11, color: "#71716B", background: "#FFFFFF", border: "1px solid #E8E8E4", borderRadius: 3, padding: "5px 10px", cursor: "pointer" }}>
                {copied ? "copied" : "copy"}
              </button>
              <pre style={{ margin: 0, padding: "24px 22px", overflowX: "auto", WebkitOverflowScrolling: "touch" as const, fontFamily: CODE_FONT, fontSize: 13, lineHeight: 1.7, color: "#0D0D0B" }}>
                <CodeBlock />
              </pre>
            </div>
          </div>
        </div>
      </section>

      {/* ── PRODUCTS ── */}
      <section style={{ background: "#FAFAF8" }}>
        <div className="r-products-hd">
          <div style={{ fontFamily: MONO, fontSize: 11, letterSpacing: "0.12em", color: "#71716B" }}>WHAT&apos;S INSIDE SVITCH</div>
        </div>

        {/* SHIELD */}
        <div className="r-product-row">
          <div className="r-grid-2">
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 14 }}>
                <span style={{ fontFamily: MONO, fontSize: 12, letterSpacing: "0.08em", color: "#0D0D0B" }}>SVITCH SHIELD</span>
                <span style={{ fontFamily: MONO, fontSize: 11, color: ACCENT }}>● LIVE</span>
              </div>
              <h3 style={{ fontSize: 22, fontWeight: 700, letterSpacing: "-0.02em", margin: "0 0 12px" }}>PII redaction before the prompt</h3>
              <p style={{ fontSize: 15, lineHeight: 1.65, color: "#71716B", margin: 0 }}>Detects Aadhaar, PAN, UPI, IFSC and seven more Indian entity types and strips them out before data reaches any model. Reversible, deterministic, logged.</p>
            </div>
            <div style={{ border: "1px solid #E8E8E4", background: "#FFFFFF", borderRadius: 6, padding: 18, fontFamily: CODE_FONT, fontSize: 12.5, lineHeight: 1.9, color: "#0D0D0B" }}>
              <div style={{ color: "#71716B", fontSize: 11, marginBottom: 8 }}>prompt — redacted</div>
              <div>verify <span style={{ borderBottom: `1px solid ${ACCENT}`, background: ACCENT_BG }}>████ ████ 0123</span></div>
              <div>pan <span style={{ borderBottom: `1px solid ${ACCENT}`, background: ACCENT_BG }}>█████1234█</span> · upi <span style={{ borderBottom: `1px solid ${ACCENT}`, background: ACCENT_BG }}>███@okhdfc</span></div>
              <div style={{ color: ACCENT, marginTop: 10 }}>✓ 3 redacted · 0 bytes to model</div>
            </div>
          </div>
        </div>

        {/* ROUTER */}
        <div className="r-product-row">
          <div className="r-grid-2">
            <div style={{ border: "1px solid #E8E8E4", background: "#FFFFFF", borderRadius: 6, padding: 18, fontFamily: CODE_FONT, fontSize: 12.5, color: "#0D0D0B" }}>
              <div style={{ color: "#71716B", fontSize: 11, marginBottom: 14 }}>query router</div>
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10, flexWrap: "wrap" }}>
                <span style={{ border: "1px solid #E8E8E4", borderRadius: 3, padding: "5px 9px", background: "#F4F3F0" }}>query</span>
                <span style={{ color: "#71716B" }}>→</span>
                <span style={{ border: "1px solid #E8E8E4", borderRadius: 3, padding: "5px 9px" }}>score 0.18</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                <span style={{ color: "#71716B" }}>→</span>
                <span style={{ border: `1px solid ${ACCENT}`, color: ACCENT, borderRadius: 3, padding: "5px 9px", background: ACCENT_BG }}>haiku · cheap</span>
                <span style={{ color: "#71716B" }}>vs</span>
                <span style={{ border: "1px solid #E8E8E4", borderRadius: 3, padding: "5px 9px", color: "#B0B0A8", textDecoration: "line-through" }}>opus</span>
              </div>
              <div style={{ marginTop: 14, fontSize: 11, color: "#71716B" }}>cost this call&nbsp;<span style={{ color: "#0D0D0B" }}>−81%</span></div>
            </div>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 14 }}>
                <span style={{ fontFamily: MONO, fontSize: 12, letterSpacing: "0.08em", color: "#0D0D0B" }}>SVITCH ROUTER</span>
                <span style={{ fontFamily: MONO, fontSize: 11, color: ACCENT }}>● LIVE</span>
              </div>
              <h3 style={{ fontSize: 22, fontWeight: 700, letterSpacing: "-0.02em", margin: "0 0 12px" }}>The right model for every query</h3>
              <p style={{ fontSize: 15, lineHeight: 1.65, color: "#71716B", margin: 0 }}>Routine queries score low and route to cheap models; hard ones escalate. You set the ceiling, Svitch spends under it — cutting model cost up to 80%.</p>
            </div>
          </div>
        </div>

        {/* TRACER */}
        <div className="r-product-row">
          <div className="r-grid-2">
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 14 }}>
                <span style={{ fontFamily: MONO, fontSize: 12, letterSpacing: "0.08em", color: "#0D0D0B" }}>SVITCH TRACER</span>
                <span style={{ fontFamily: MONO, fontSize: 11, color: ACCENT }}>● LIVE</span>
              </div>
              <h3 style={{ fontSize: 22, fontWeight: 700, letterSpacing: "-0.02em", margin: "0 0 12px" }}>A tamper-proof record of every decision</h3>
              <p style={{ fontSize: 15, lineHeight: 1.65, color: "#71716B", margin: 0 }}>Every prompt, redaction, route and response is hashed into an append-only chain. Break a link and the whole trail flags. Export for any auditor.</p>
            </div>
            <div style={{ border: "1px solid #E8E8E4", background: "#FFFFFF", borderRadius: 6, padding: 18, fontFamily: CODE_FONT, fontSize: 12, color: "#0D0D0B" }}>
              <div style={{ color: "#71716B", fontSize: 11, marginBottom: 12 }}>audit chain</div>
              <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
                {["a91f…","3c0d…","7be2…"].map((h) => (
                  <span key={h} style={{ border: "1px solid #E8E8E4", borderRadius: 3, padding: "6px 8px", background: "#F4F3F0" }}>{h}</span>
                ))}
                <span style={{ color: ACCENT }}>−</span>
                <span style={{ border: `1px solid ${ACCENT}`, color: ACCENT, borderRadius: 3, padding: "6px 8px", background: ACCENT_BG }}>f04a…</span>
              </div>
              <div style={{ marginTop: 12, fontSize: 11, color: "#71716B" }}>prev_hash verified · <span style={{ color: ACCENT }}>chain intact</span></div>
            </div>
          </div>
        </div>

        {/* ENCLAVE */}
        <div className="r-product-row">
          <div className="r-grid-2">
            <div style={{ border: "1px solid #E8E8E4", background: "#FFFFFF", borderRadius: 6, padding: 18, fontFamily: CODE_FONT, fontSize: 12, color: "#0D0D0B" }}>
              <div style={{ color: "#71716B", fontSize: 11, marginBottom: 16 }}>network topology · zero egress</div>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
                <span style={{ border: "1px solid #E8E8E4", borderRadius: 3, padding: "8px 11px", background: "#F4F3F0" }}>your VPC</span>
                <span style={{ flex: 1, borderTop: `1px dashed ${ACCENT}`, margin: "0 8px", minWidth: 16 }} />
                <span style={{ fontSize: 10, color: ACCENT }}>WireGuard</span>
                <span style={{ flex: 1, borderTop: `1px dashed ${ACCENT}`, margin: "0 8px", minWidth: 16 }} />
                <span style={{ border: `1px solid ${ACCENT}`, color: ACCENT, borderRadius: 3, padding: "8px 11px", background: ACCENT_BG }}>enclave</span>
              </div>
              <div style={{ marginTop: 16, fontSize: 11, color: "#71716B" }}>model weights resident · <span style={{ color: "#0D0D0B" }}>no outbound route</span></div>
            </div>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 14 }}>
                <span style={{ fontFamily: MONO, fontSize: 12, letterSpacing: "0.08em", color: "#0D0D0B" }}>SVITCH ENCLAVE</span>
                <span style={{ fontFamily: MONO, fontSize: 11, color: "#71716B" }}>○ COMING SOON</span>
              </div>
              <h3 style={{ fontSize: 22, fontWeight: 700, letterSpacing: "-0.02em", margin: "0 0 12px" }}>Inference that never leaves your perimeter</h3>
              <p style={{ fontSize: 15, lineHeight: 1.65, color: "#71716B", margin: 0 }}>An encrypted on-premise enclave runs open models inside your own network over a WireGuard tunnel. Zero egress — sensitive data stays put.</p>
            </div>
          </div>
        </div>

        {/* LEDGER */}
        <div className="r-product-last">
          <div className="r-grid-2">
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 14 }}>
                <span style={{ fontFamily: MONO, fontSize: 12, letterSpacing: "0.08em", color: "#0D0D0B" }}>SVITCH LEDGER</span>
                <span style={{ fontFamily: MONO, fontSize: 11, color: "#71716B" }}>○ COMING SOON</span>
              </div>
              <h3 style={{ fontSize: 22, fontWeight: 700, letterSpacing: "-0.02em", margin: "0 0 12px" }}>Consent, recorded on a shared ledger</h3>
              <p style={{ fontSize: 15, lineHeight: 1.65, color: "#71716B", margin: 0 }}>A Hyperledger consent chain records who agreed to what, when. Prove lawful basis for every data subject — ready for DPDP grievance officers.</p>
            </div>
            <div style={{ border: "1px solid #E8E8E4", background: "#FFFFFF", borderRadius: 6, padding: 18, fontFamily: CODE_FONT, fontSize: 12, color: "#0D0D0B" }}>
              <div style={{ color: "#71716B", fontSize: 11, marginBottom: 12 }}>consent ledger</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {[{ id:"subject_8821",status:"granted",live:true},{ id:"subject_8822",status:"granted",live:true},{ id:"subject_8823",status:"withdrawn",live:false}].map((row) => (
                  <div key={row.id} style={{ display: "flex", justifyContent: "space-between", border: "1px solid #E8E8E4", borderRadius: 3, padding: "7px 10px", background: "#F4F3F0" }}>
                    <span>{row.id}</span>
                    <span style={{ color: row.live ? ACCENT : "#71716B" }}>{row.status}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── COMPLIANCE STATS ── */}
      <section style={{ background: "#0D0D0B", color: "#FFFFFF" }}>
        <div className="r-section-sm">
          <div className="r-grid-stats">
            {[
              { stat: "11",       label: "Indian PII types\ndetected" },
              { stat: "May 2027", label: "DPDP enforcement\ndeadline" },
              { stat: "₹250 Cr",  label: "Max penalty per\nbreach" },
            ].map(({ stat, label }) => (
              <div key={stat}>
                <div className="r-stat-num" style={{ fontFamily: DISPLAY }}>{stat}</div>
                <div style={{ width: 36, height: 1, background: "#3A3A36", marginBottom: 16 }} />
                <div style={{ fontFamily: MONO, fontSize: 13, color: "#9A9A92", lineHeight: 1.5, whiteSpace: "pre-line" }}>{label}</div>
              </div>
            ))}
          </div>
          <div style={{ fontFamily: MONO, fontSize: 13, color: "#71716B", marginTop: 56, paddingTop: 28, borderTop: "1px solid #26261F" }}>
            Svitch makes your AI stack audit-ready before regulators come knocking.
          </div>
        </div>
      </section>

      {/* ── FOOTER ── */}
      <footer style={{ background: "#FAFAF8", borderTop: "1px solid #E8E8E4" }}>
        <div className="r-section-sm">
          <div className="r-grid-footer">
            <div>
              <div style={{ fontFamily: DISPLAY, fontSize: 20, fontWeight: 700, letterSpacing: "-0.03em", marginBottom: 10 }}>Svitch</div>
              <div style={{ fontFamily: MONO, fontSize: 12, color: "#71716B" }}>Apache 2.0 · open source</div>
            </div>
            <div style={{ display: "flex", gap: 28, fontFamily: MONO, fontSize: 13, color: "#71716B", justifyContent: "center", flexWrap: "wrap" }}>
              <a href="#process" style={{ color: "#71716B" }}>Products</a>
              <a href="#demo"    style={{ color: "#71716B" }}>Docs</a>
              <a href="https://github.com/koushiknarendra/svitch" target="_blank" style={{ color: "#71716B" }}>GitHub</a>
              <a href="#"        style={{ color: "#71716B" }}>Changelog</a>
            </div>
            <div className="r-text-right">
              <a href="#demo" style={{ fontFamily: MONO, fontSize: 13, color: ACCENT }}>Request early access&nbsp;→</a>
            </div>
          </div>
        </div>

        {/* Oversized wordmark */}
        <div className="r-wm-wrap">
          <div
            ref={wordmarkRef}
            style={{ display: "inline-block", fontFamily: DISPLAY, fontWeight: 700, letterSpacing: "-0.055em", lineHeight: 0.74, color: "#E4E3DC", fontSize: wmSize, marginBottom: "-0.1em", userSelect: "none", whiteSpace: "nowrap" }}
            aria-hidden="true"
          >
            Svitch
          </div>
        </div>
      </footer>

    </div>
  );
}
