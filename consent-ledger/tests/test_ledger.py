"""
Consent Ledger tests.
Run: python consent-ledger/tests/test_ledger.py
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["SVITCH_CONSENT_DB"] = ":memory:"

import ledger as L

L.init_db()


def sep(t): print(f"\n{'─'*54}\n  {t}\n{'─'*54}")


sep("Test 1: Grant consent — Aadhaar + PAN for loan processing")

record = L.grant(
    data_principal_id="CUST-001",
    purpose="loan_processing",
    data_categories=["AADHAAR", "PAN", "BANK_ACCOUNT"],
    legal_basis="explicit_consent",
    version="2.1",
    channel="mobile_app",
    ip_address="103.21.45.67",
    agent_id="loan-processor-v1",
)

print(f"  Consent ID   : {record.consent_id}")
print(f"  Status       : {record.status}")
print(f"  Record hash  : {record.record_hash[:24]}…")
print(f"  Prev hash    : {record.prev_hash[:24]}…")
print(f"  IP hashed    : {record.ip_address_hash[:24]}… (raw IP not stored)")

assert record.consent_id
assert record.status == "active"
assert len(record.record_hash) == 64
assert record.data_principal_id != "CUST-001", "Raw customer ID must not be stored"
assert record.ip_address_hash != "103.21.45.67", "Raw IP must not be stored"
assert "AADHAAR" in record.data_categories
consent_id_1 = record.consent_id
print("  PASS — consent granted, PII fields hashed")


sep("Test 2: Verify active consent")

valid, reason, rec = L.verify(consent_id_1)
print(f"  Valid  : {valid}")
print(f"  Reason : {reason}")
assert valid
assert rec.status == "active"
print("  PASS")


sep("Test 3: Grant a second consent — KYC")

record2 = L.grant(
    data_principal_id="CUST-002",
    purpose="kyc_verification",
    data_categories=["AADHAAR", "PASSPORT_IN", "MOBILE_IN"],
    legal_basis="regulatory_obligation",
    version="2.1",
    channel="web",
)

# Chain linkage: second record's prev_hash = first record's hash
assert record2.prev_hash == record.record_hash, "Chain linkage broken!"
consent_id_2 = record2.consent_id
print(f"  Chain link verified: prev_hash = {record2.prev_hash[:16]}…")
print("  PASS — chain links correctly")


sep("Test 4: Withdraw consent")

withdrawal = L.withdraw(consent_id_1)
print(f"  Withdrawal record : {withdrawal.consent_id}")
print(f"  Status            : {withdrawal.status}")
print(f"  Withdrawn at ms   : {withdrawal.withdrawn_at_ms}")

assert withdrawal.status == "withdrawn"
assert withdrawal.withdrawn_at_ms is not None

# Original should now show withdrawn
valid2, reason2, _ = L.verify(consent_id_1)
assert not valid2
assert "withdrawn" in reason2.lower()
print(f"  Original verify: {reason2}")
print("  PASS — withdrawal recorded, original still in chain")


sep("Test 5: Cannot withdraw twice")

try:
    L.withdraw(consent_id_1)
    assert False, "Should have raised"
except ValueError as e:
    print(f"  Correctly rejected: {e}")
print("  PASS")


sep("Test 6: Full chain verification")

valid_chain, msg, count = L.verify_chain()
print(f"  Records checked : {count}")
print(f"  Chain valid     : {valid_chain}")
print(f"  Message         : {msg}")
assert valid_chain
assert count >= 3   # grant, grant, withdrawal
print("  PASS — Merkle chain intact")


sep("Test 7: Cryptographic proof generation")

p = L.proof(consent_id_2)
print(f"  Consent ID    : {p['consent_id']}")
print(f"  Purpose       : {p['purpose']}")
print(f"  Status        : {p['status']}")
print(f"  Is valid      : {p['is_valid']}")
print(f"  Record hash   : {p['record_hash'][:24]}…")
print(f"  Verify instr. : {p['verify_instructions'][:60]}…")

assert p["is_valid"]
assert p["record_hash"]
assert "SHA-256" in p["verify_instructions"]
print("  PASS — proof generated, self-verifiable without Svitch access")


sep("Test 8: List consents for a data principal")

consents = L.get_consents("CUST-001")
active   = L.get_active_consents("CUST-001")
print(f"  Total consents for CUST-001 : {len(consents)}")
print(f"  Active consents             : {len(active)}")
for c in consents:
    print(f"    [{c.status:10}] {c.purpose}")

assert len(consents) >= 2   # original grant + withdrawal record
assert len(active) == 0     # withdrawn
print("  PASS")


sep("Test 9: Hash identity — same input → same hash")

h1 = L.hash_identity("CUST-001")
h2 = L.hash_identity("CUST-001")
h3 = L.hash_identity("CUST-002")
assert h1 == h2
assert h1 != h3
print(f"  CUST-001 hash  : {h1[:32]}…")
print(f"  CUST-002 hash  : {h3[:32]}…")
print("  PASS — deterministic, one-way")


print(f"\n{'═'*54}")
print(f"  ALL CONSENT LEDGER TESTS PASSED")
print(f"{'═'*54}\n")
