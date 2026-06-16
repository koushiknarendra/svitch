"""
Enclave integration test — runs without Docker or GPU.
Spins up a mock vLLM server and the Svitch inference server in-process,
then fires requests through and verifies PII is blocked.

Run: python test_enclave.py
"""

import sys
import os
import json
import threading
import time
import urllib.request
import urllib.error

# ── Path setup ────────────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "pii-shield", "service"))
sys.path.insert(0, os.path.join(ROOT, "agent-tracer"))
os.environ.setdefault("SVITCH_DB_PATH", ":memory:")

# ── Shared port constants ─────────────────────────────────────────────────────
MOCK_LLM_PORT    = 19871
ENCLAVE_PORT     = 19872


def _start_mock_llm():
    """Tiny in-process mock that mimics OpenAI chat completions."""
    from fastapi import FastAPI, Request
    import uvicorn

    mock = FastAPI()

    @mock.get("/health")
    def health():
        return {"status": "ok"}

    @mock.get("/v1/models")
    def models():
        return {"object": "list", "data": [{"id": "llama-3.1-8b-instruct", "object": "model"}]}

    @mock.post("/v1/chat/completions")
    async def chat(request: Request):
        body = await request.json()
        last_msg = body.get("messages", [{}])[-1].get("content", "")
        return {
            "id": "mock-001",
            "object": "chat.completion",
            "model": body.get("model", "llama-3.1-8b-instruct"),
            "choices": [{"index": 0, "message": {"role": "assistant", "content": f"Echo: {last_msg}"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
        }

    config = uvicorn.Config(mock, host="127.0.0.1", port=MOCK_LLM_PORT, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    return server


def _start_enclave():
    os.environ["VLLM_BASE_URL"]  = f"http://127.0.0.1:{MOCK_LLM_PORT}"
    os.environ["ENCLAVE_ID"]     = "test-enclave"
    os.environ["PII_MODE"]       = "redact"
    os.environ["TRACER_ENABLED"] = "true"

    import uvicorn
    sys.path.insert(0, os.path.join(ROOT, "private-enclave", "inference"))
    import importlib
    spec = importlib.util.spec_from_file_location("server", os.path.join(ROOT, "private-enclave", "inference", "server.py"))
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    config = uvicorn.Config(mod.app, host="127.0.0.1", port=ENCLAVE_PORT, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    return server


def _wait_for(url, timeout=10):
    for _ in range(timeout * 4):
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except Exception:
            time.sleep(0.25)
    return False


def _post(url, payload):
    data = json.dumps(payload).encode()
    req  = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def sep(title):
    print(f"\n{'─'*54}\n  {title}\n{'─'*54}")


# ── Run ───────────────────────────────────────────────────────────────────────
print("\nStarting servers...")
_start_mock_llm()
_start_enclave()

assert _wait_for(f"http://127.0.0.1:{MOCK_LLM_PORT}/health"), "Mock LLM failed to start"
assert _wait_for(f"http://127.0.0.1:{ENCLAVE_PORT}/health"),  "Enclave failed to start"
print("  Both servers healthy.")


sep("Test 1: Health check")
h = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{ENCLAVE_PORT}/health").read())
print(f"  pii_shield : {h['pii_shield']}")
print(f"  tracer     : {h['tracer']}")
assert h["status"] == "ok"
print("  PASS")


sep("Test 2: PII is redacted before reaching vLLM")
resp = _post(f"http://127.0.0.1:{ENCLAVE_PORT}/v1/chat/completions", {
    "model": "llama-3.1-8b-instruct",
    "messages": [{"role": "user", "content": "Customer Aadhaar: 2345 6789 0123, PAN: ABCDE1234F"}],
})
# The mock LLM echoes the message — check echo doesn't contain raw PII
echo = resp["choices"][0]["message"]["content"]
print(f"  LLM received: {echo}")
assert "2345 6789 0123" not in echo, "Aadhaar leaked to LLM!"
assert "ABCDE1234F"     not in echo, "PAN leaked to LLM!"
assert "[AADHAAR]"      in echo
assert "[PAN]"          in echo

svitch_meta = resp.get("svitch", {})
print(f"  PII blocked  : {svitch_meta.get('pii_blocked')}")
print(f"  PII types    : {svitch_meta.get('pii_types')}")
print("  PASS — Aadhaar and PAN redacted before LLM call")


sep("Test 3: Clean prompt passes through unchanged")
resp2 = _post(f"http://127.0.0.1:{ENCLAVE_PORT}/v1/chat/completions", {
    "model": "llama-3.1-8b-instruct",
    "messages": [{"role": "user", "content": "What is the capital of India?"}],
})
echo2 = resp2["choices"][0]["message"]["content"]
assert "capital of India" in echo2
assert resp2["svitch"]["pii_blocked"] is False
print(f"  Clean prompt passed through: {echo2[:60]}")
print("  PASS")


sep("Test 4: UPI + mobile redacted together")
resp3 = _post(f"http://127.0.0.1:{ENCLAVE_PORT}/v1/chat/completions", {
    "model": "llama-3.1-8b-instruct",
    "messages": [
        {"role": "system", "content": "You are a banking assistant."},
        {"role": "user",   "content": "Transfer ₹5000 from 9876543210 to rahul@okicici"},
    ],
})
echo3 = resp3["choices"][0]["message"]["content"]
assert "9876543210"    not in echo3, "Mobile leaked!"
assert "rahul@okicici" not in echo3, "UPI leaked!"
pii_types = resp3["svitch"]["pii_types"]
assert "MOBILE_IN" in pii_types
assert "UPI_ID"    in pii_types
print(f"  PII types blocked: {pii_types}")
print("  PASS — mobile and UPI redacted")


print(f"\n{'═'*54}")
print(f"  ALL ENCLAVE TESTS PASSED")
print(f"{'═'*54}\n")
