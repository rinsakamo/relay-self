# RelaySelf — SelfWorld W4: independent raw custody / external issuer qualification

Authority: #633, #537, #627, #575, Draft #634. **DEV inspection only; no new physical run, Action or S10 permission.** This is an operator handoff and an explicit fail-closed qualification contract, not an independently witnessed result.

## Input / frozen history

- W2 Stage R artifact `12139674420` has parsed report, not a qualified uninterrupted original receive stream. W2 was stopped at `RAW_NATIVE_SOURCE_NOT_ATTESTED`; historical source cannot be backfilled.
- W3 *new* DEV artifact `12164748068` in run `39203276695` has uploaded ZIP SHA256 `7a3971983dd8a7b2ce1ce6fa1fb74e58dc4878a873ba163c9d0d73f4ddcdd254`, `w3-node-stdout.raw.jsonl` SHA256 `7eb8d8f769c90ca31dbcdb7d719bf80787fc2693c856911b608d37976638c0e5`, 30,682 bytes, 61 frames seq 0..60 in session `f24f0136-d636-4d4f-8eaf-6375bf0c107d`. It was recorded **at the Python receiver of Node bridge stdout**, not at the Minecraft TCP boundary. Producer completeness remains unqualified.
- W3 31/31 offline replay and correspondence are source *content* checks; self-created receipt/upload SHA is **not** a pre-existing independent archivist pin.
- Both W3 Action same-target `distance_delta_m=0.09595129995869334`, hence **HOLD** under unchanged Stage S `delta_m=0.100`. No non-HOLD S17, S10 permission or learned policy assertion from W3.

## Priority / trust graph

```text
 original S49 single Action issuer / Node stdout producer
        | captured source bytes + original closed S16 receipts
        v
 W4 independent archivist custody (separately managed identity and storage)
        | raw-file digest + immutable capture-window/inventory receipt
        | detached archivist signature; public trust key pinned out of band
        v
 W4 independent source auditor (read-only raw vs W3 ZIP/report replay)
        | source admissibility; cannot mint S10 authority
        v
 separate S10 issuer / signer (independent private-key principal)
        | scope-bound S17+Action+session+next-probe request; signed grant
        v
 consumer (separate principal): external public pins + spent-once ledger
        | may submit validated reservation, not self-grant
        v
 original S10 owner (NO LIVE INSTALL / NO PHYSICAL COMMIT IN W4)
```

Neither `distinct Python process` nor `different keypair` nor `different UID in a user namespace` establishes this boundary by itself. W4 **MUST NOT** qualify trust from caller-supplied `issuer_id`, an envelope's embedded key, a self-minted public-key pin, or a copied attestation file.

## W4 ordered tasks and receipts

1. **Freeze exact HEAD and evidence scope**. Independent clean worktree; record branch SHA, OS/UID/group/ACL context, original W3 artifact locator and exact ZIP/raw hashes, original Node bridge producer and Python receive window. Verify 7/7 ZIP manifest and raw/reported S49 Action/geometry concordance *without* writing to any original archive or rerunning Minecraft. Do not assert raw Minecraft network packet capture or complete Node emission.
2. **Independent original custody**. Before *future* physical acquisitions, provision an archivist identity, key, append-only or immutable/versioned external evidence store and a custody procedure independently from the S49 producer, W1 request preparer, S10 signer and consumer. Store the *unaltered received bytes*, byte count, session/seq/window, receive origin, capture start/end, original ZIP digest, acquisition/transfer time and chain-of-custody history. Have archivist seal/sign this manifest. Record a hash/pin through a separately administered channel **before** consumer grant requests (and preferably at acquisition). Uploading the bytes by the producer to GitHub Actions does not on its own prove independent collection or control before upload.
3. **Independent signer**. Provision S10 issuer private key outside repo, Actions secrets, consumer filesystem and original S49 Action owner account, with a different independently controlled principal. Authenticate and pin *issuer public key and authority scope* via an external administratively controlled channel. Evidence must show issuer UID/credentials, path ownership, parent traversal ACL/group/mount access, actual process UID, key identity, signer policy and audit log. The consumer must fail to read/derive/export private material **and** fail to request signatures on arbitrary synthetic source documents. `openssl verify` proves key control, **not issuer authorization**.
4. **Cross-boundary evidence challenge**. Under a distinct consumer account compare independently held W3 raw archive/receipt against raw replay, original S49 typed action, Stage S criterion and exact original session/action/probe/source. Refuse forged extraction, changed source scope, altered or missing frames, producer-only hash, independently unavailable capture, mismatch between pinned source and signer request, foreign same-target event, and external signer not in the pinned trust registry. Independently authenticate both archivist and issuer, never with a trust anchor sent in the untrusted envelope.
5. **Persistent grant replay**. On a disposable ledger only, verify same-grant concurrency (one process succeeds and all others fail), fresh-process replay denial, DB schema/lock failures, replaced public/raw pin failures. Test DB restore/rollback/copy and crash semantics in disposable isolated storage, not on production host or its WSL VHD. Until an independent monotonic or external spent-grant authority rules out cloned/rolled-back DBs, classify global spend-once **NOT QUALIFIED**.
6. **Complete report**. Preserve raw and signed custody attestations, only PUBLIC PEM, fingerprints, sealed manifest, original source/replay discrepancies, OS permissions and principal audit, positive/negative case exit codes, independent verifier name, lifecycle cleanup and new evidence SHA manifest. Do not post private PEM, bearer tokens or secrets to GitHub. Evidence that could contain private host paths or identifying data should be summarized or redacted in public PR discussion; keep originals in controlled custody.

## W4 qualification matrix

| Predicate | Required | Current state from W2/W3 |
|---|---|---|
| S49 original Node stdout bytes as Python received | 1 exact W3 DEV session | **DEV CONTENT PASS** |
| Independently controlled raw custody / advance externally controlled pin | Actual non-producer archivist, signed inventory, custody trail | **NOT ATTESTED** |
| Emitter completeness and Minecraft wire provenance | Separate evidence if claiming full World source | **NOT ATTESTED** |
| Independent original S49 raw/report/source readback | Frozen W3 pair with documented limitations | **31/31 content PASS; trust NOT PROVEN** |
| Separate external S10 signer authority / consumer isolation | Out-of-band trust anchor, policy and principal evidence | **NOT ATTESTED** |
| Cross-process ledger replay | Disposable same-key concurrency/restarts | **W2 DEV PASS only** |
| Host crash, ledger rollback/clone global replay safety | Isolated independent tests | **NOT TESTED** |
| Live directional original S10 update and next epoch | Fresh separately gated physical trial | **NO_GO** |
| Near-zombie WAIT safety or V science | Separate formal qualification/preregistration | **NO_GO** |

**Stop rule:** any missing independent source custody or signer principal/trust proof => `W4_INDEPENDENT_CUSTODY_OR_ISSUER_NO_GO`, no trusted S10 approval and no qualification promotion. PASS for content-only replay is never an override.

## Distinct future non-HOLD physical trial

See `docs/selfworld-w4-nonhold-prereg.md` for a **new prospectively registered DEV scenario**. Stage S `delta_m=0.100` and motion minimum `0.050` remain fixed. W3 observed 9.595 cm cannot be re-scored by threshold tuning or retroactive new geometry. Do not start the separate trial until its implementation, exact source HEAD, scenario/geometry, controls, stop conditions and independent receipt plan have been frozen and reviewed. This W4 handoff does **not** authorize a physical run.
