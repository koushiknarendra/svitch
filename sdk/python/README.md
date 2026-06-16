# svitch

AI data security layer — detect and redact Indian and global PII from LLM prompts and responses.

```bash
pip install svitch
```

## Quickstart

```python
import svitch

# Detect PII
entities = svitch.detect("Customer Aadhaar: 2345 6789 0123, PAN: ABCDE1234F")
# [Entity(type='AADHAAR', ...), Entity(type='PAN', ...)]

# Redact PII
result = svitch.redact("Call me on 9876543210, UPI: rahul@okicici")
# result.text  → "Call me on [MOBILE_IN], UPI: [UPI_ID]"
# result.count → 2
# result.clean → False

# Wrap any OpenAI-compatible client
import openai
client = svitch.wrap(openai.OpenAI())
# Use exactly like openai.OpenAI() — PII is redacted before every API call
```

## What It Detects

**India (DPDP-critical):** Aadhaar, PAN, UPI IDs, IFSC, mobile numbers, GST, bank accounts, Voter ID, Passport

**Global:** Email addresses, IPv4/IPv6, international phone numbers

## Mask mode

```python
result = svitch.redact("Aadhaar: 2345 6789 0123", replacement="mask")
# result.text → "Aadhaar: XXXX XXXX 0123"
```

## Anthropic

```python
import anthropic
client = svitch.wrap(anthropic.Anthropic())
```

## License

Apache 2.0
