"use client";

import { useState, useCallback } from "react";

const DEMO_TEXT = `Dear Rahul Sharma,

Your loan application has been received. We have verified:
- Aadhaar: 2345 6789 0123
- PAN: ABCDE1234F
- Mobile: 9876543210
- UPI: rahul@okicici
- IFSC: HDFC0001234
- Email: rahul.sharma@example.com

Your account number 123456789012 will receive the disbursement.
GST Number: 22ABCDE1234F1Z5`;

interface Entity {
  type: string;
  value: string;
  start: number;
  end: number;
}

const TYPE_COLORS: Record<string, { bg: string; text: string; label: string }> = {
  AADHAAR:      { bg: "bg-red-100",    text: "text-red-700",    label: "Aadhaar" },
  PAN:          { bg: "bg-orange-100", text: "text-orange-700", label: "PAN" },
  UPI_ID:       { bg: "bg-purple-100", text: "text-purple-700", label: "UPI" },
  MOBILE_IN:    { bg: "bg-blue-100",   text: "text-blue-700",   label: "Mobile" },
  IFSC:         { bg: "bg-teal-100",   text: "text-teal-700",   label: "IFSC" },
  EMAIL:        { bg: "bg-yellow-100", text: "text-yellow-800", label: "Email" },
  GST:          { bg: "bg-pink-100",   text: "text-pink-700",   label: "GST" },
  BANK_ACCOUNT: { bg: "bg-indigo-100", text: "text-indigo-700", label: "Bank A/C" },
};

export default function Home() {
  const [input, setInput] = useState(DEMO_TEXT);
  const [result, setResult] = useState<{ text: string; entities: Entity[]; count: number } | null>(null);
  const [loading, setLoading] = useState(false);

  const run = useCallback(async () => {
    if (!input.trim()) return;
    setLoading(true);
    try {
      const res = await fetch("/api/redact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: input }),
      });
      setResult(await res.json());
    } finally {
      setLoading(false);
    }
  }, [input]);

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Nav */}
      <nav className="border-b border-gray-800 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 bg-indigo-500 rounded-md" />
          <span className="font-semibold text-lg tracking-tight">Svitch</span>
        </div>
        <div className="flex items-center gap-6 text-sm text-gray-400">
          <a href="https://github.com/koushiknarendra/svitch" target="_blank" className="hover:text-white transition-colors">GitHub</a>
          <a href="https://github.com/koushiknarendra/svitch" target="_blank" className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-1.5 rounded-md transition-colors">Get started</a>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-4xl mx-auto px-6 pt-20 pb-12 text-center">
        <div className="inline-flex items-center gap-2 bg-indigo-950 border border-indigo-800 text-indigo-300 text-xs px-3 py-1 rounded-full mb-6">
          <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-pulse" />
          DPDP enforcement begins May 2027 · ₹250 crore penalty for data breaches
        </div>
        <h1 className="text-5xl font-bold tracking-tight mb-4">
          Stop customer data from<br />
          <span className="text-indigo-400">leaking into ChatGPT</span>
        </h1>
        <p className="text-lg text-gray-400 max-w-2xl mx-auto mb-8">
          Svitch detects and redacts Aadhaar, PAN, UPI IDs, and 8 other Indian PII types
          before they reach any LLM. Three lines of code. Zero config.
        </p>
        <div className="flex items-center justify-center gap-3 flex-wrap">
          <code className="bg-gray-900 border border-gray-700 text-green-400 text-sm px-4 py-2 rounded-lg font-mono">
            pip install svitch
          </code>
          <a href="https://github.com/koushiknarendra/svitch" target="_blank"
            className="bg-indigo-600 hover:bg-indigo-500 px-5 py-2 rounded-lg text-sm font-medium transition-colors">
            View on GitHub →
          </a>
        </div>
      </section>

      {/* Live Demo */}
      <section className="max-w-5xl mx-auto px-6 pb-20">
        <div className="text-center mb-8">
          <h2 className="text-2xl font-semibold mb-2">Live Demo</h2>
          <p className="text-gray-400 text-sm">Paste any text — Svitch detects and redacts Indian PII instantly, in your browser.</p>
        </div>

        <div className="grid md:grid-cols-2 gap-4">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-gray-500 uppercase tracking-wider">Input</span>
              <button onClick={() => { setInput(DEMO_TEXT); setResult(null); }}
                className="text-xs text-gray-500 hover:text-gray-300 transition-colors">
                Load sample
              </button>
            </div>
            <textarea
              value={input}
              onChange={e => { setInput(e.target.value); setResult(null); }}
              className="w-full h-80 bg-gray-900 border border-gray-700 rounded-xl p-4 text-sm font-mono text-gray-200 resize-none focus:outline-none focus:border-indigo-500 transition-colors"
              placeholder="Paste text with Aadhaar, PAN, UPI, mobile numbers..."
            />
            <button
              onClick={run}
              disabled={loading || !input.trim()}
              className="mt-3 w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed py-2.5 rounded-lg text-sm font-medium transition-colors"
            >
              {loading ? "Detecting..." : "Detect & Redact →"}
            </button>
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-gray-500 uppercase tracking-wider">Redacted Output</span>
              {result && (
                <span className="text-xs text-indigo-400 font-medium">
                  {result.count} {result.count === 1 ? "entity" : "entities"} removed
                </span>
              )}
            </div>
            <div className="w-full h-80 bg-gray-900 border border-gray-700 rounded-xl p-4 text-sm font-mono text-gray-200 overflow-y-auto">
              {result ? (
                <span className="whitespace-pre-wrap">{result.text}</span>
              ) : (
                <span className="text-gray-600">Redacted text appears here...</span>
              )}
            </div>

            {result && result.entities.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-2">
                {result.entities.map((e, i) => {
                  const c = TYPE_COLORS[e.type] ?? { bg: "bg-gray-800", text: "text-gray-300", label: e.type };
                  return (
                    <span key={i} className={`inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full ${c.bg} ${c.text}`}>
                      <span className="font-semibold">{c.label}</span>
                      <span className="opacity-60 font-mono">{e.value.length > 14 ? e.value.slice(0, 14) + "…" : e.value}</span>
                    </span>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Code */}
      <section className="border-t border-gray-800 bg-gray-900">
        <div className="max-w-3xl mx-auto px-6 py-16">
          <h2 className="text-2xl font-semibold text-center mb-8">Three lines of code</h2>
          <div className="bg-gray-950 border border-gray-800 rounded-xl p-6 font-mono text-sm leading-7">
            <div className="text-gray-600"># Wrap your existing OpenAI client</div>
            <div><span className="text-purple-400">import</span> <span className="text-white">svitch</span><span className="text-gray-500">, </span><span className="text-white">openai</span></div>
            <div className="mt-2">
              <span className="text-blue-400">client</span>
              <span className="text-gray-400"> = </span>
              <span className="text-yellow-400">svitch</span>
              <span className="text-gray-400">.</span>
              <span className="text-green-400">wrap</span>
              <span className="text-gray-400">(</span>
              <span className="text-yellow-400">openai</span>
              <span className="text-gray-400">.</span>
              <span className="text-green-400">OpenAI</span>
              <span className="text-gray-400">())</span>
            </div>
            <div className="mt-4 text-gray-600"># Use exactly like before — PII is auto-redacted</div>
            <div>
              <span className="text-blue-400">response</span>
              <span className="text-gray-400"> = </span>
              <span className="text-blue-400">client</span>
              <span className="text-gray-400">.chat.completions.</span>
              <span className="text-green-400">create</span>
              <span className="text-gray-400">(model=</span>
              <span className="text-orange-300">"gpt-4o"</span>
              <span className="text-gray-400">, messages=[...])</span>
            </div>
          </div>
        </div>
      </section>

      <footer className="border-t border-gray-800 px-6 py-8 text-center text-sm text-gray-600">
        Apache 2.0 · Built for India&apos;s DPDP Act ·{" "}
        <a href="https://github.com/koushiknarendra/svitch" target="_blank" className="hover:text-gray-400 transition-colors">
          GitHub
        </a>
      </footer>
    </div>
  );
}
