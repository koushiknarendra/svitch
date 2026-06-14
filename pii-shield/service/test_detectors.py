"""
Smoke tests for the PII detection engine.
Run: python test_detectors.py
"""

import sys
sys.path.insert(0, ".")

from detectors.india import detect, redact
from detectors.common import detect as detect_common
from detectors import detect_all, redact_all


def check(name, got, expected):
    if got == expected:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}")
        print(f"        expected: {expected!r}")
        print(f"        got:      {got!r}")
        return False
    return True


passed = failed = 0

cases = [
    # (description, input_text, expected_entity_types, expected_redacted_snippet)
    (
        "Aadhaar with spaces",
        "Customer Aadhaar: 2345 6789 0123",
        ["AADHAAR"],
        "Customer Aadhaar: [AADHAAR]",
    ),
    (
        "Aadhaar with hyphens",
        "Aadhaar 2345-6789-0123 is valid",
        ["AADHAAR"],
        "Aadhaar [AADHAAR] is valid",
    ),
    (
        "Aadhaar no separator",
        "Verify 234567890123 immediately",
        ["AADHAAR"],
        "Verify [AADHAAR] immediately",
    ),
    (
        "PAN card",
        "PAN: ABCDE1234F",
        ["PAN"],
        "PAN: [PAN]",
    ),
    (
        "PAN with company type",
        "Company PAN AABCP1234C registered",
        ["PAN"],
        "Company PAN [PAN] registered",
    ),
    (
        "UPI ID",
        "Pay to rahul@okicici now",
        ["UPI_ID"],
        "Pay to [UPI_ID] now",
    ),
    (
        "UPI with paytm",
        "UPI: 9876543210@paytm",
        ["UPI_ID"],
        "UPI: [UPI_ID]",
    ),
    (
        "IFSC code",
        "IFSC: HDFC0001234",
        ["IFSC"],
        "IFSC: [IFSC]",
    ),
    (
        "Indian mobile 10-digit",
        "Call me on 9876543210 please",
        ["MOBILE_IN"],
        "Call me on [MOBILE_IN] please",
    ),
    (
        "Indian mobile with +91",
        "WhatsApp +919876543210",
        ["MOBILE_IN"],
        "WhatsApp [PHONE_INTL]",  # +91XXXXXXXXXX matched as international phone (longer span)
    ),
    (
        "GST number",
        "GST: 22ABCDE1234F1Z5",
        ["GST"],
        "GST: [GST]",
    ),
    (
        "Multiple entities in one text",
        "Name: Rahul, PAN ABCDE1234F, Aadhaar 2345 6789 0123, mobile 9876543210",
        ["PAN", "AADHAAR", "MOBILE_IN"],
        None,  # just check entities, not exact redaction
    ),
    (
        "Email address",
        "Email me at rahul@example.com today",
        ["EMAIL"],
        "Email me at [EMAIL] today",
    ),
    (
        "Clean text",
        "The weather is nice today.",
        [],
        "The weather is nice today.",
    ),
    (
        "Bank account with context",
        "Account number: 123456789012",
        ["BANK_ACCOUNT"],
        "Account number: [BANK_ACCOUNT]",
    ),
]

print("\nRunning India PII detector tests...\n")
for desc, text, expected_types, expected_redacted in cases:
    entities = detect_all(text)
    found_types = [e.type for e in entities]

    type_ok = all(t in found_types for t in expected_types)
    if type_ok:
        print(f"  PASS  [{desc}] — found {found_types}")
        passed += 1
    else:
        print(f"  FAIL  [{desc}]")
        print(f"        expected types: {expected_types}")
        print(f"        got types:      {found_types}")
        failed += 1

    if expected_redacted is not None and expected_types:
        redacted_text, _ = redact_all(text, "token")
        if redacted_text == expected_redacted:
            print(f"        redact PASS")
        else:
            print(f"        redact FAIL: {redacted_text!r} != {expected_redacted!r}")

print(f"\nResults: {passed} passed, {failed} failed out of {passed+failed} tests")

# Mask mode test
print("\nMask mode samples:")
samples = [
    "Aadhaar: 2345 6789 0123",
    "PAN: ABCDE1234F",
    "Mobile: 9876543210",
    "UPI: rahul@okicici",
]
for s in samples:
    masked, _ = redact_all(s, "mask")
    print(f"  {s!r:45} → {masked!r}")
