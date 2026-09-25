# Svitch

Multi-provider LLM routing — auto model selection, failover, and prompt-cache stabilization, OpenAI-compatible.

```bash
pip install svitch
```

```python
from svitch import Router
import openai, anthropic

router = Router()
router.add("openai", openai.OpenAI())
router.add("anthropic", anthropic.Anthropic())

# Auto-routing: Svitch classifies complexity and picks provider + model
r = router.chat(messages=[{"role": "user", "content": "What is Aadhaar?"}])
print(r.content, r.provider, r.model, r.tier)

# Explicit provider/model
r = router.chat(messages=[...], model="anthropic/claude-sonnet-4-6")

# Failover: try OpenAI, fall back to Anthropic on error
r = router.chat(messages=[...], model="openai/gpt-4o", fallback="anthropic/claude-sonnet-4-6")
```

## Hosted gateway

`api/server.py` is an OpenAI-compatible `/v1/chat/completions` endpoint — point your existing OpenAI client at it and get routing across providers with zero code changes beyond the `base_url`:

```python
client = openai.OpenAI(base_url="https://your-svitch-deployment.vercel.app/v1", api_key="any")
```

## Status

Extracted from an earlier project (Governor) where LLM routing and PII/compliance tooling lived in one codebase. Split into its own product — this repo is routing only, no compliance/redaction logic. [Governor](https://github.com/koushiknarendra/governor) is the separate compliance layer; the two are designed to compose (e.g. point Governor's redaction at a client built from this router) but neither depends on the other.

Not yet actively developed/marketed — code lives here clean and ready, GTM focus is currently on Governor.
