"""
Hyperledger Fabric client for the Svitch Consent Ledger.

Calls the ConsentLedgerContract chaincode to anchor and verify consent
records on-chain. Falls back gracefully when Fabric is not configured
(development / single-server deployments use hash-chain SQLite only).

Usage:
    from client.fabric_client import FabricClient, FabricConfig

    cfg = FabricConfig(
        channel="mychannel",
        chaincode="consent",
        peer_endpoint="grpcs://peer0.org1.example.com:7051",
        tls_cert_path="/crypto/peer0/tls/ca.crt",
        msp_id="Org1MSP",
        key_path="/crypto/user/keystore/key.pem",
        cert_path="/crypto/user/signcerts/cert.pem",
    )
    client = FabricClient(cfg)
    tx_id = client.anchor_consent(consent_id, record)
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from typing import Optional

from ..ledger import ConsentRecord


@dataclass
class FabricConfig:
    channel: str
    chaincode: str
    peer_endpoint: str
    tls_cert_path: str
    msp_id: str
    key_path: str
    cert_path: str
    orderer_endpoint: str = ""
    timeout: int = 30


class FabricClient:
    """
    Thin wrapper around the Fabric peer CLI.
    In production, replace with hf-fabric-gateway (Python SDK) once stable.
    """

    def __init__(self, config: FabricConfig):
        self.cfg = config
        self._available = self._check_peer_binary()

    def _check_peer_binary(self) -> bool:
        try:
            result = subprocess.run(["peer", "version"], capture_output=True, timeout=5)
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def is_available(self) -> bool:
        return self._available

    def _env(self) -> dict:
        return {
            **os.environ,
            "CORE_PEER_LOCALMSPID":        self.cfg.msp_id,
            "CORE_PEER_TLS_ENABLED":        "true",
            "CORE_PEER_TLS_ROOTCERT_FILE":  self.cfg.tls_cert_path,
            "CORE_PEER_MSPCONFIGPATH":      os.path.dirname(self.cfg.cert_path),
            "CORE_PEER_ADDRESS":            self.cfg.peer_endpoint.replace("grpcs://", ""),
        }

    def _invoke(self, function: str, *args: str) -> str:
        """Invoke a chaincode transaction (read-write)."""
        fn_args = json.dumps({"Args": [function, *args]})
        cmd = [
            "peer", "chaincode", "invoke",
            "-o", self.cfg.orderer_endpoint or self.cfg.peer_endpoint,
            "-C", self.cfg.channel,
            "-n", self.cfg.chaincode,
            "-c", fn_args,
            "--tls", "--cafile", self.cfg.tls_cert_path,
            "--waitForEvent",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True,
                                timeout=self.cfg.timeout, env=self._env())
        if result.returncode != 0:
            raise RuntimeError(f"Fabric invoke failed: {result.stderr}")
        # Extract txid from output
        for line in result.stderr.splitlines():
            if "txid" in line.lower():
                parts = line.split()
                for i, p in enumerate(parts):
                    if "txid" in p.lower() and i + 1 < len(parts):
                        return parts[i + 1].strip(",[]")
        return "unknown"

    def _query(self, function: str, *args: str) -> dict:
        """Query chaincode state (read-only)."""
        fn_args = json.dumps({"Args": [function, *args]})
        cmd = [
            "peer", "chaincode", "query",
            "-C", self.cfg.channel,
            "-n", self.cfg.chaincode,
            "-c", fn_args,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True,
                                timeout=self.cfg.timeout, env=self._env())
        if result.returncode != 0:
            raise RuntimeError(f"Fabric query failed: {result.stderr}")
        return json.loads(result.stdout)

    def anchor_consent(self, record: ConsentRecord) -> Optional[str]:
        """
        Anchor a consent record on Hyperledger Fabric.
        Returns the Fabric transaction ID, or None if Fabric is unavailable.
        """
        if not self._available:
            return None
        tx_id = self._invoke(
            "AnchorConsent",
            record.consent_id,
            json.dumps(sorted(record.data_categories)),
            record.purpose,
            record.legal_basis,
            record.record_hash,
            record.prev_hash,
            record.version,
            str(record.granted_at_ms),
        )
        return tx_id

    def withdraw_consent(self, consent_id: str) -> Optional[str]:
        if not self._available:
            return None
        return self._invoke("WithdrawConsent", consent_id)

    def verify_consent(self, consent_id: str) -> dict:
        if not self._available:
            return {"found": False, "valid": False,
                    "reason": "Fabric not configured — using off-chain verification"}
        return self._query("VerifyConsent", consent_id)

    def get_history(self, consent_id: str) -> list[dict]:
        if not self._available:
            return []
        result = self._query("GetConsentHistory", consent_id)
        return result if isinstance(result, list) else []
