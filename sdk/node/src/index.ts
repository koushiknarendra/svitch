import * as P from './patterns.js';

export interface Entity {
  type: string;
  value: string;
  start: number;
  end: number;
}

export interface DetectResult {
  entities: Entity[];
  count: number;
}

export interface RedactResult {
  text: string;
  originalText: string;
  entities: Entity[];
  count: number;
  clean: boolean;
}

type Replacement = 'token' | 'mask';
type Locale = 'in' | 'global' | 'all';

interface PatternDef {
  pattern: RegExp;
  type: string;
  group?: number;
}

const INDIA_PATTERNS: PatternDef[] = [
  { pattern: P.AADHAAR, type: 'AADHAAR' },
  { pattern: P.AADHAAR_MASKED, type: 'AADHAAR_MASKED' },
  { pattern: P.PAN, type: 'PAN', group: 1 },
  { pattern: P.UPI, type: 'UPI_ID' },
  { pattern: P.IFSC, type: 'IFSC', group: 1 },
  { pattern: P.MOBILE_IN, type: 'MOBILE_IN', group: 1 },
  { pattern: P.GST, type: 'GST', group: 1 },
  { pattern: P.BANK_ACCOUNT, type: 'BANK_ACCOUNT', group: 1 },
];

const GLOBAL_PATTERNS: PatternDef[] = [
  { pattern: P.EMAIL, type: 'EMAIL' },
  { pattern: P.IPV4, type: 'IPV4' },
];


function findEntities(text: string, defs: PatternDef[]): Entity[] {
  const entities: Entity[] = [];

  for (const { pattern, type, group = 0 } of defs) {
    // Reset lastIndex for global patterns
    const p = new RegExp(pattern.source, pattern.flags);
    let m: RegExpExecArray | null;
    while ((m = p.exec(text)) !== null) {
      const value = group > 0 ? m[group] : m[0];
      const start = group > 0 ? (m.index + m[0].indexOf(value)) : m.index;
      const end = start + value.length;
      if (value) {
        entities.push({ type, value, start, end });
      }
    }
  }

  entities.sort((a, b) => a.start - b.start);
  return entities;
}

function deoverlap(entities: Entity[]): Entity[] {
  const result: Entity[] = [];
  for (const e of entities) {
    const last = result[result.length - 1];
    if (last && e.start < last.end) {
      if ((e.end - e.start) > (last.end - last.start)) {
        result[result.length - 1] = e;
      }
    } else {
      result.push(e);
    }
  }
  return result;
}

function maskEntity(e: Entity): string {
  if (e.type === 'AADHAAR') {
    const digits = e.value.replace(/[\s\-]/g, '');
    return `XXXX XXXX ${digits.slice(-4)}`;
  }
  if (e.type === 'PAN') return e.value.slice(0, 5) + 'XXXX' + e.value.slice(-1);
  if (e.type === 'MOBILE_IN') return `XXXXXX${e.value.slice(-4)}`;
  if (e.type === 'UPI_ID') {
    const [, provider] = e.value.split('@');
    return provider ? `XXXX@${provider}` : '[UPI_ID]';
  }
  return `[${e.type}]`;
}


export function detect(text: string, locale: Locale = 'all'): DetectResult {
  const defs = locale === 'in'
    ? INDIA_PATTERNS
    : locale === 'global'
    ? GLOBAL_PATTERNS
    : [...INDIA_PATTERNS, ...GLOBAL_PATTERNS];

  const entities = findEntities(text, defs);
  return { entities, count: entities.length };
}


export function redact(
  text: string,
  locale: Locale = 'all',
  replacement: Replacement = 'token',
): RedactResult {
  const { entities } = detect(text, locale);
  if (entities.length === 0) {
    return { text, originalText: text, entities: [], count: 0, clean: true };
  }

  const unique = deoverlap(entities);
  const parts: string[] = [];
  let cursor = 0;

  for (const e of unique) {
    parts.push(text.slice(cursor, e.start));
    parts.push(replacement === 'mask' ? maskEntity(e) : `[${e.type}]`);
    cursor = e.end;
  }
  parts.push(text.slice(cursor));

  return {
    text: parts.join(''),
    originalText: text,
    entities: unique,
    count: unique.length,
    clean: false,
  };
}


// ---------------------------------------------------------------------------
// Client wrappers
// ---------------------------------------------------------------------------

type AnyClient = Record<string | symbol, any>;

export function wrap(client: AnyClient, locale: Locale = 'all'): AnyClient {
  const name = client?.constructor?.name ?? '';

  if (name.includes('OpenAI')) return wrapOpenAI(client, locale);
  if (name.includes('Anthropic')) return wrapAnthropic(client, locale);

  throw new Error(
    `svitch.wrap() does not recognise client type "${name}". ` +
    'Supported: OpenAI, Anthropic (and their Async variants).'
  );
}

function redactMessages(messages: any[], locale: Locale): { messages: any[]; count: number } {
  let count = 0;
  const cleaned = messages.map((msg) => {
    if (typeof msg?.content === 'string' && msg.content) {
      const r = redact(msg.content, locale);
      count += r.count;
      return { ...msg, content: r.text };
    }
    return msg;
  });
  return { messages: cleaned, count };
}

function wrapOpenAI(client: AnyClient, locale: Locale): AnyClient {
  return new Proxy(client, {
    get(target, prop) {
      if (prop === 'chat') {
        return new Proxy(target.chat, {
          get(chatTarget, chatProp) {
            if (chatProp === 'completions') {
              return new Proxy(chatTarget.completions, {
                get(compTarget, compProp) {
                  if (compProp === 'create') {
                    return async (params: any) => {
                      const { messages, count } = redactMessages(params.messages ?? [], locale);
                      return compTarget.create({ ...params, messages });
                    };
                  }
                  return compTarget[compProp];
                },
              });
            }
            return chatTarget[chatProp];
          },
        });
      }
      return target[prop];
    },
  });
}

function wrapAnthropic(client: AnyClient, locale: Locale): AnyClient {
  return new Proxy(client, {
    get(target, prop) {
      if (prop === 'messages') {
        return new Proxy(target.messages, {
          get(msgTarget, msgProp) {
            if (msgProp === 'create') {
              return async (params: any) => {
                const { messages } = redactMessages(params.messages ?? [], locale);
                let system = params.system;
                if (typeof system === 'string') {
                  system = redact(system, locale).text;
                }
                return msgTarget.create({ ...params, messages, ...(system !== undefined && { system }) });
              };
            }
            return msgTarget[msgProp];
          },
        });
      }
      return target[prop];
    },
  });
}
