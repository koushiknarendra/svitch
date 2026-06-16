/**
 * Svitch Consent Ledger — Hyperledger Fabric Chaincode
 *
 * Deployed on a permissioned Fabric network where:
 *   - Svitch operates one peer node
 *   - The enterprise (bank/NBFC) operates one peer node
 *   - Optionally: DSCI / RBI-appointed auditor operates a third node
 *
 * Any node can independently verify consent records without trusting others.
 * Consent hashes from the off-chain SQLite ledger are anchored here for
 * third-party verifiability.
 *
 * Install:
 *   npm install && npm run build
 *   peer chaincode install -n consent -v 1.0 -p ./dist
 *   peer chaincode instantiate -n consent -v 1.0 -C mychannel
 */

import { Contract, Context, Info, Returns, Transaction } from "fabric-contract-api";

interface ConsentAnchor {
  consentId: string;
  dataCategories: string[];
  purpose: string;
  legalBasis: string;
  status: "active" | "withdrawn" | "expired";
  grantedAtMs: number;
  withdrawnAtMs: number | null;
  recordHash: string;    // SHA-256 from off-chain ledger — the verifiable proof
  prevHash: string;      // chain linkage
  version: string;
  anchoredAtMs: number;  // when this was written to Fabric
  anchoredBy: string;    // MSP ID of the submitting organisation
}

interface VerifyResult {
  found: boolean;
  valid: boolean;
  reason: string;
  anchor?: ConsentAnchor;
}

@Info({ title: "SvitchConsentLedger", description: "DPDP consent records on Hyperledger Fabric" })
export class ConsentLedgerContract extends Contract {

  constructor() {
    super("SvitchConsentLedger");
  }

  @Transaction(false)
  @Returns("string")
  async Ping(_ctx: Context): Promise<string> {
    return JSON.stringify({ status: "ok", chaincode: "SvitchConsentLedger", version: "1.0" });
  }

  /**
   * Anchor a consent grant on-chain.
   * Called by the enterprise's peer when a customer grants consent.
   */
  @Transaction()
  async AnchorConsent(
    ctx: Context,
    consentId: string,
    dataCategories: string,      // JSON array
    purpose: string,
    legalBasis: string,
    recordHash: string,
    prevHash: string,
    version: string,
    grantedAtMs: string,
  ): Promise<void> {
    const existing = await ctx.stub.getState(consentId);
    if (existing && existing.length > 0) {
      throw new Error(`Consent ${consentId} already anchored on chain`);
    }

    const mspId = ctx.clientIdentity.getMSPID();
    const now = Date.now();

    const anchor: ConsentAnchor = {
      consentId,
      dataCategories: JSON.parse(dataCategories),
      purpose,
      legalBasis,
      status: "active",
      grantedAtMs: parseInt(grantedAtMs),
      withdrawnAtMs: null,
      recordHash,
      prevHash,
      version,
      anchoredAtMs: now,
      anchoredBy: mspId,
    };

    await ctx.stub.putState(consentId, Buffer.from(JSON.stringify(anchor)));

    // Emit event for off-chain listeners
    ctx.stub.setEvent("ConsentGranted", Buffer.from(JSON.stringify({
      consentId, purpose, grantedAtMs: anchor.grantedAtMs, anchoredBy: mspId,
    })));
  }

  /**
   * Record consent withdrawal on-chain.
   * The original grant record remains — withdrawal is append-only.
   */
  @Transaction()
  async WithdrawConsent(ctx: Context, consentId: string): Promise<void> {
    const data = await ctx.stub.getState(consentId);
    if (!data || data.length === 0) {
      throw new Error(`Consent ${consentId} not found on chain`);
    }

    const anchor: ConsentAnchor = JSON.parse(data.toString());
    if (anchor.status !== "active") {
      throw new Error(`Consent ${consentId} is already ${anchor.status}`);
    }

    anchor.status = "withdrawn";
    anchor.withdrawnAtMs = Date.now();

    await ctx.stub.putState(consentId, Buffer.from(JSON.stringify(anchor)));

    ctx.stub.setEvent("ConsentWithdrawn", Buffer.from(JSON.stringify({
      consentId, withdrawnAtMs: anchor.withdrawnAtMs,
    })));
  }

  /**
   * Verify a consent record — callable by any peer without Svitch access.
   * Regulators use this to confirm consent existed independently of Svitch.
   */
  @Transaction(false)
  @Returns("string")
  async VerifyConsent(ctx: Context, consentId: string): Promise<string> {
    const data = await ctx.stub.getState(consentId);

    if (!data || data.length === 0) {
      const result: VerifyResult = {
        found: false, valid: false,
        reason: "Consent record not found on chain",
      };
      return JSON.stringify(result);
    }

    const anchor: ConsentAnchor = JSON.parse(data.toString());
    const now = Date.now();

    let valid = true;
    let reason = "Consent is valid and active on chain";

    if (anchor.status === "withdrawn") {
      valid = false;
      reason = `Consent withdrawn at ${new Date(anchor.withdrawnAtMs!).toISOString()}`;
    } else if (anchor.status === "expired") {
      valid = false;
      reason = "Consent has expired";
    }

    const result: VerifyResult = { found: true, valid, reason, anchor };
    return JSON.stringify(result);
  }

  /**
   * Get full consent history for an anchored record.
   */
  @Transaction(false)
  @Returns("string")
  async GetConsentHistory(ctx: Context, consentId: string): Promise<string> {
    const iterator = await ctx.stub.getHistoryForKey(consentId);
    const history = [];

    while (true) {
      const res = await iterator.next();
      if (res.done) break;
      const { value } = res;
      history.push({
        txId: value.txId,
        timestamp: value.timestamp,
        isDelete: value.isDelete,
        value: value.value ? JSON.parse(value.value.toString()) : null,
      });
    }
    await iterator.close();
    return JSON.stringify(history);
  }

  /**
   * Bulk verify: given a list of record hashes, confirm they exist on-chain.
   * Used by auditors to spot-check a sample of consents without full DB access.
   */
  @Transaction(false)
  @Returns("string")
  async BulkVerifyHashes(ctx: Context, hashesJson: string): Promise<string> {
    const hashes: string[] = JSON.parse(hashesJson);
    const results: Record<string, boolean> = {};

    // Query by composite key: hash → consentId mapping
    for (const hash of hashes) {
      const iterator = await ctx.stub.getStateByPartialCompositeKey("hash~consent", [hash]);
      let found = false;
      while (true) {
        const res = await iterator.next();
        if (res.done) break;
        found = true;
      }
      await iterator.close();
      results[hash] = found;
    }

    return JSON.stringify(results);
  }
}
