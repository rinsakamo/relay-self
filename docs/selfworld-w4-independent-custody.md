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

## 2026-10-19 local continuation: explicit external-trust NO_GO

The continuation adds **OFFLINE** W4 tests and a non-authorizing inventory in
`self_world_stage_w4_preflight.py`. No caller-supplied identity, UID, TEST key,
boolean or copied receipt can qualify independent custody. The original W1
consumer still returns `external_issuer_identity_qualified=false` and
`real_s10_commit_permitted=false`; it has no live S10 bridge.

Local observation: consumer uid/gid 1000, supplementary groups include sudo
and docker. `sudo -n -l` requires a password. `getfacl` is unavailable. No
separately administered archivist, immutable external destination, private-key
principal/path, signer process authentication/policy, or independently
published advance pin was supplied. No existing key was searched/read. With no
independent principal/key subject, UID/gid/groups/ACL/parent traversal,
mount/bind/symlink and privileged-access key isolation cannot be qualified.
A password prompt does not prove absence of privileged access, especially with
docker group membership. No daemon, sudo configuration, user, ACL or host OS
configuration was changed. Result: **W4_EXTERNAL_TRUST_NO_GO**.

| Predicate | Continuation disposition |
|---|---|
| W3 ZIP/raw expected digest and 7-file SHA manifest | PASS, local content integrity only |
| W3 61 frames, original session, 3 event/probe decisions, 2 Action S16/effect/geometry pairings | PASS, 31 named content checks; no independent witness identity |
| W3 original same-target Stage S | HOLD twice, unchanged delta +0.09595129995869334m |
| Independent archivist identity/storage/acquisition contract | BLOCKED, no external principal/store contract |
| Archivist signature / advance external public pin | BLOCKED, no signature or independent pin provided |
| Signer key custody, process authentication and real signing policy | BLOCKED, subject and independent administrative evidence absent |
| Signed physical evidence ↔ external archive pin | BLOCKED, synthetic checks cannot substitute for a physical signed manifest |
| Node emission completeness / Minecraft wire provenance | NOT_TESTED / NOT_ATTESTED |
| S49 source/Action identity | PASS for frozen report/raw correspondence only; external process authentication BLOCKED |
| S17 source / S10 owner-issued permission | Synthetic source negatives PASS; genuine external permission BLOCKED |
| Same disposable DB concurrent processes and fresh-process replay | DEV tests only, exactly one reservation; no S10 permission |
| Symlink, parent symlink, replaced inode, hardlink, mode, missing DB, lock | Rejection covered by new local/CI controls |
| Disposable process crash before COMMIT | DEV rollback/integrity test; no host power-loss claim |
| Disposable cloned pre-spend DB | Same grant accepted in both copies: demonstrated global single-use FAIL; qualification BLOCKED |
| WSL2 forced reboot / power loss / cross-host rollback resistance | NOT_TESTED; no host disruption |

Ledger admission now checks owner/mode 0600, single link, symlink ancestors and
stable device/inode before each reservation and before COMMIT. These checks do
not sandbox a malicious same-UID/root process or eliminate every filesystem
TOCTOU race. An externally monotonic spent-grant authority remains necessary
for global single-use; SQLite FULL and the new checks do not establish it.

`prepare_unsigned_custody_handoff` validates the W3 receipt and inventories
unaltered raw bytes/hash/session/seq/window and local transfer observation.
It deliberately leaves capture wall times, external identity, signature and
public pin absent. This is a **candidate for external receipt**, not an
append-only independent signed manifest. Historical W3 cannot gain an
acquisition-time witness from this later readback. No historical Stage R/W3
receipt is changed. Local evidence is retained outside the repo at
`/home/rinsa/w4-dev-20261019`; no private keys are published.

## W4-O / NH1 continuation trust disposition (2026-10-19)

Typed orientation and the W4 DEV S16 readback are source-content checks only.
No independent archivist/acquisition-before-run contract, external immutable
store, signed receipt/separately controlled advance pin, independent signer
identity/key isolation/policy, or global monotonic spend authority has been
provided in this continuation. **W4_EXTERNAL_TRUST_NO_GO** remains terminal for
physical launch. No TEST key, same-UID process or local SQLite result changes it.
Existing isolated clone and in-place rollback tests intentionally demonstrate
that the same grant can be consumed again from restored storage; these passing
regressions document a failed global single-use property.

The smallest next external step is a separately administered acquisition and
signer contract with authenticated principals and key custody, not another
local keypair. For global spending, an independently monotonic log needs an
atomic admission decision; a bare append-only audit log records duplication
without necessarily preventing concurrent spends. A single independently
controlled authority service with a transaction unique constraint can serialize
admission, but its own rollback/backup policy and availability become trust
requirements. No new authority service is implemented here.
