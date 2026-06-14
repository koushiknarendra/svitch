import { NextRequest, NextResponse } from "next/server";

// Inline the detection patterns — no external dependency needed in API routes
const AADHAAR = /(?<!\+)(?<!\d)([2-9][0-9]{3})[\s\-]?([0-9]{4})[\s\-]?([0-9]{4})(?!\d)/g;
const AADHAAR_MASKED = /\b[Xx*]{4}[\s\-]?[Xx*]{4}[\s\-]?[0-9]{4}\b/g;
const PAN = /\b([A-Z]{5}[0-9]{4}[A-Z])\b/g;
const UPI_PROVIDERS = "paytm|gpay|phonepe|okicici|okhdfcbank|oksbi|okaxis|ybl|axl|apl|ibl|icici|hdfcbank|sbi|upi|freecharge|airtel|jio|amazon|indus|boi|aubank|dbs|federal|idfc|kotak|pnb|bob|barb|nkgsb|saraswat";
const UPI = new RegExp(`\\b[\\w.\\-]{2,256}@(?:${UPI_PROVIDERS})\\b`, "gi");
const IFSC = /\b([A-Z]{4}0[A-Z0-9]{6})\b/g;
const MOBILE_IN = /(?<!\d)(?:\+91[\s\-]?|91[\s\-]?|0)?([6-9][0-9]{9})(?!\d)/g;
const GST = /\b([0-3][0-9][A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]Z[0-9A-Z])\b/g;
const EMAIL = /\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b/g;
const BANK_ACCOUNT = /(?:account\s*(?:number|no\.?|#)|a\/?c\s*(?:no\.?|#)|bank\s*a\/?c)[\s:]*([0-9]{9,18})/gi;

interface Entity {
  type: string;
  value: string;
  start: number;
  end: number;
}

function detect(text: string): Entity[] {
  const entities: Entity[] = [];

  const patterns: Array<[RegExp, string, number]> = [
    [AADHAAR, "AADHAAR", 0],
    [AADHAAR_MASKED, "AADHAAR_MASKED", 0],
    [PAN, "PAN", 1],
    [UPI, "UPI_ID", 0],
    [IFSC, "IFSC", 1],
    [MOBILE_IN, "MOBILE_IN", 1],
    [GST, "GST", 1],
    [BANK_ACCOUNT, "BANK_ACCOUNT", 1],
    [EMAIL, "EMAIL", 0],
  ];

  for (const [pattern, type, group] of patterns) {
    const p = new RegExp(pattern.source, pattern.flags);
    let m: RegExpExecArray | null;
    while ((m = p.exec(text)) !== null) {
      const value = group > 0 ? m[group] : m[0];
      if (!value) continue;
      const start = group > 0 ? m.index + m[0].indexOf(value) : m.index;
      entities.push({ type, value, start, end: start + value.length });
    }
  }

  entities.sort((a, b) => a.start - b.start);
  return entities;
}

function redact(text: string): { text: string; entities: Entity[] } {
  const all = detect(text);

  // Deoverlap — longer match wins
  const unique: Entity[] = [];
  for (const e of all) {
    const last = unique[unique.length - 1];
    if (last && e.start < last.end) {
      if (e.end - e.start > last.end - last.start) unique[unique.length - 1] = e;
    } else {
      unique.push(e);
    }
  }

  if (!unique.length) return { text, entities: [] };

  const parts: string[] = [];
  let cursor = 0;
  for (const e of unique) {
    parts.push(text.slice(cursor, e.start));
    parts.push(`[${e.type}]`);
    cursor = e.end;
  }
  parts.push(text.slice(cursor));

  return { text: parts.join(""), entities: unique };
}

export async function POST(req: NextRequest) {
  try {
    const { text } = await req.json();
    if (!text || typeof text !== "string") {
      return NextResponse.json({ error: "text is required" }, { status: 400 });
    }
    const result = redact(text.slice(0, 5000));
    return NextResponse.json({
      text: result.text,
      original_text: text,
      entities: result.entities,
      count: result.entities.length,
    });
  } catch {
    return NextResponse.json({ error: "Invalid request" }, { status: 400 });
  }
}
