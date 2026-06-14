# Svitch

**The AI data security layer for regulated enterprises.**

Svitch sits between your application and any LLM provider — detecting and redacting sensitive data before it leaves your infrastructure, and logging every agent decision for regulatory audit.

```python
import svitch
import openai

client = svitch.wrap(openai.OpenAI(api_key="..."))

# Aadhaar, PAN, UPI IDs — automatically redacted before hitting OpenAI
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Customer Rahul Sharma, Aadhaar 2345 6789 0123, PAN ABCDE1234F needs a loan summary."}]
)
# OpenAI receives: "Customer [NAME], Aadhaar [AADHAAR], PAN [PAN] needs a loan summary."
```

## What It Detects

**India (DPDP-critical):**
- Aadhaar numbers (12-digit, masked and unmasked formats)
- PAN cards (ABCDE1234F format)
- UPI IDs (name@bankcode)
- IFSC codes (ABCD0123456)
- Indian mobile numbers (10-digit, +91 prefix variants)
- Indian Passport numbers
- Voter ID (EPIC numbers)
- GST numbers
- Bank account numbers

**Global:**
- Email addresses
- Generic phone numbers
- IPv4/IPv6 addresses

## Quickstart

### Python

```bash
pip install svitch
```

```python
import svitch

# Detect PII in text
result = svitch.detect("Call me on 9876543210, my PAN is ABCDE1234F")
# result.entities: [Entity(type='MOBILE_IN', value='9876543210', ...), Entity(type='PAN', ...)]

# Redact PII from text
redacted = svitch.redact("My Aadhaar is 2345 6789 0123")
# redacted.text: "My Aadhaar is [AADHAAR]"

# Wrap any OpenAI-compatible client
import openai
client = svitch.wrap(openai.OpenAI())
# Use exactly like openai.OpenAI() — PII is redacted automatically
```

### Node.js

```bash
npm install svitch
```

```typescript
import { detect, redact, wrap } from 'svitch';
import OpenAI from 'openai';

const { entities } = detect("My UPI is rahul@okicici");
const { text } = redact("PAN: ABCDE1234F, Aadhaar: 2345 6789 0123");

const client = wrap(new OpenAI({ apiKey: process.env.OPENAI_API_KEY }));
```

### Self-hosted Service

```bash
cd pii-shield/service
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

```bash
curl -X POST http://localhost:8000/redact \
  -H "Content-Type: application/json" \
  -d '{"text": "Aadhaar: 2345 6789 0123, PAN: ABCDE1234F"}'
```

## Why Svitch

No existing tool — not AWS Bedrock Guardrails, not Azure Content Safety, not NeMo Guardrails — properly detects Indian PII entities (Aadhaar, PAN, UPI IDs) across multiple LLM providers.

Under India's DPDP Act (full enforcement May 2027), sending unredacted personal data to a third-party LLM provider exposes your company to penalties up to ₹250 crore.

## Architecture

```
Your App → Svitch SDK → [PII detected & redacted] → LLM Provider
                ↓
         Audit Log (append-only, hash-chained)
```

The SDK runs locally — no data sent to Svitch servers. The optional hosted service adds audit trails, dashboards, and compliance reports.

## Roadmap

- [x] India PII detection (Aadhaar, PAN, UPI, IFSC, mobile, passport, voter ID, GST)
- [x] Python SDK with OpenAI + Anthropic wrappers
- [x] Node.js SDK
- [x] Self-hosted FastAPI service
- [ ] Agent decision lineage (LangGraph, CrewAI, AutoGen)
- [ ] DPDP compliance report generator
- [ ] Private AI inference enclave (run Llama/Mistral on your own server)
- [ ] Blockchain consent ledger
- [ ] GDPR / HIPAA mode

## License

Apache 2.0 — free to use, modify, and distribute.
