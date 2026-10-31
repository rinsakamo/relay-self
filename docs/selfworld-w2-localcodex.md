# RelaySelf SelfWorld — W2 LocalCodex operator handoff (DEV/QUALIFICATION boundary)

**Authority:** SelfWorld #633, S Integration #537, Adaptive Cognition #426,
existing Draft #634. Primary language for execution report: Japanese.

**Do not change** main, historical/frozen Stage R source evidence, consumed
one-shot grants, original S49 Action control, original S10 owner, or V Science.
Never treat a local signer or a self-minted pin as an externally trusted issuer.

## Status and scope

W1 implements (1) a canonical extracted evidence document with independently
provided SHA-256, (2) Stage V exact signed request verification using a
separately pinned public RSA key, (3) SQLite spend-once reservations across
consumer object restarts. W2 must inspect *actual* process and filesystem
boundaries on the operator's WSL2 host. W2 may carry out harmless disposable
DEV rehearsal without asking for a new physical Minecraft grant. It **must
not** run real Minecraft, enable real S10 commit or near-zombie physical
WAIT without a separate reviewed qualification and bounded grant.

### Important source limitation

The currently implemented S49 runner's `execution_evidence` stores parsed
before/after source samples and effects, but does NOT by itself establish
independently captured and sealed raw Mineflayer receive-stream continuity.
Do not label `native_report.json`, an extracted Stage W1 JSON document, or
server stderr as authenticated *original raw Node/Minecraft packets*.
If no independent original native raw stream exists, mark
`RAW_NATIVE_SOURCE_NOT_ATTESTED` and stop at that boundary. A new future
DEV run may acquire such evidence under a separate grant and instrumentation,
but cannot retroactively repair frozen prior one-shot evidence.

## LocalCodex sequence

1. Read exact Draft #634 HEAD and record `git rev-parse HEAD`, worktree,
   uncommitted diff, operating system, `id -u`, Python/OpenSSL/sqlite versions,
   `wsl --status` from Windows if accessible, and existing worktree isolation.
   Use a *new disposable* WSL2 root and never rewrite old receipts.
2. Run only the new focused offline tests and existing FAST workflow commands
   against this exact HEAD. Example:
   ```bash
   PYTHONPATH=src:tests:. python -m pytest -q \
     tests/test_self_world_stage_w_gate.py \
     tests/test_self_world_stage_w2_local.py
   ```
   Do not import private keys or snapshot data from a previous SCIENCE run.
3. Prepare a **separately provisioned** issuer OS identity / user namespace and
   consumer OS identity in a disposable environment *only if operator
   privileges and the user's authorization permit*. Do not create sudo users,
   weaken ACLs, change global `/etc` configuration, or edit production keys
   merely to make a test pass. Keep a private RSA PEM outside the repo and
   outside all consumer-readable directories. Obtain issuer public PEM
   fingerprint from an independent operator channel, not the signed envelope.
4. Under the *consumer OS identity*, directly attempt a no-content read-open
   of the issuer key; absence/inaccessible location is **not** proof of
   custody. Validate user IDs, parent path ownership, permissions, ACLs,
   private-path symlinks, and the signer process's actual UID. Confirm the
   consumer can access only public key. Record exact evidence and
   independently attest key-file identity on issuer side. Distinct UIDs alone
   are insufficient if the consumer can read the private key via group,
   supplementary groups, ACLs, root/sudo, bind mounts, or file descriptors.
5. Pin original unmodified raw Mineflayer/Node bytes *outside the consumer
   request/envelope* and separately record file identity, SHA256, source
   process/seq/window and whether capture covers the entire relevant stream.
   Compare these real raw records against W1's extracted source. If the raw
   stream is not captured, emit **BLOCKED**, do not fabricate an extraction.
6. Use the existing `StageWPersistentGrantLedger.provision_new` for a
   one-off absolute path owned by the consumer (0600). Run two independent
   **consumer subprocesses** with the *same* request, pinned source/archive
   and pinned public key, using
   `python -m adapters.mineflayer.self_world_stage_w2_ledger_worker`.
   Exactly one read-only reservation may be written; the other must be
   denied. A third newly started process must also be denied. Test missing
   DB, changed issuer pin, altered archive pin, forged feedback, missing
   event and lock contention. Receipt output is exclusive-create, never
   overwrite old evidence.
7. Check the ledger path's owner, mode, schema and integrity and issue a
   **read-only environment report** under the consumer identity using
   `python -m adapters.mineflayer.self_world_stage_w2_local_preflight`:
   ```bash
   PYTHONPATH=src:. python -m adapters.mineflayer.self_world_stage_w2_local_preflight \
     --public-pem /ABS/SEPARATELY_PINNED/issuer-public.pem \
     --public-sha256 <64-lowercase-hex-from-separate-operator> \
     --raw-source /ABS/RAW/IMMUTABLE/original-native-stream.jsonl \
     --raw-sha256 <64-lowercase-hex-from-separate-archivist> \
     --ledger /ABS/DISPOSABLE/spent.sqlite3 \
     --issuer-private-key /ABS/ISSUER_ONLY/private.pem \
     --issuer-uid <actual-issuer-uid> \
     --consumer-uid <actual-consumer-uid> \
     --report /ABS/NEW/w2-local-preflight.json
   ```
   This CLI checks local file existence/mode, expected source/public digests,
   database read-only integrity, consumer UID and lack of consumer *read*
   access to issuer private key. It does NOT read private key bytes and
   NEVER validates raw stream completeness. **A zero exit means
   `W2_LOCAL_FILESYSTEM_PRECHECK_ONLY`, not W2 real-world PASS.**
   Review the receipt's false attestation flags before any result claim.
8. Crash/restart, storage rollback/restore and cross-machine copied-ledger
   attacks must be run against **disposable copies**. SQLite FULL synchronous
   in a CI/container test does not prove true WSL2 host crash durability.
   If safe isolated crash testing is not possible, mark it NOT TESTED;
   do not forcibly reboot the user's host or corrupt their live WSL VHD.
9. Preserve W2 synthetic trial inputs/receipts, stdout/stderr, exit codes,
   user IDs, file metadata, raw/archive hashes, ledger rows (no private PEM),
   exact SHA256 manifest and cleanup proof. Post a bounded GitHub report with
   an explicit list of BLOCKED qualifications. **No experimental success
   promotion**. User may return the LocalCodex final readout for independent
   review before continuing.

## Local W2 test result taxonomy

- `W2_LOCAL_FILESYSTEM_PRECHECK_ONLY`: all checked local metadata predicates
  passed. This does **not** verify raw stream provenance or grant issuer trust.
- `W2_LOCAL_PREFLIGHT_BLOCKED`: one or more local isolation/file/pin/ledger
  predicates absent. No actual S10 grant.
- `W2_PROCESS_REPLAY_DEV_PASS`: separately proven concurrent and restarted
  consumer-process single-use in disposable DB. No physical S10 permission.
- `RAW_NATIVE_SOURCE_NOT_ATTESTED`: exact original Mineflayer receive stream
  not available or cannot be independently compared with extracted evidence.
- `W2_EXTERNAL_ISSUER_TRUST_UNQUALIFIED`: signer public PEM was self-minted
  or its authorization/custody lacks independent witness.
- `QUALIFICATION_NO_GO`: any attempted promotion to physical non-HOLD S10,
  near-zombie WAIT, or R/V SCIENCE without separate gated evidence.

Even a successful operator preflight is only an **environment metadata
observation**, not an attestation of physical World behavior. The W1/W2
consumer never constructs `LearningUpdateAuthority`. Its receipt fields
for `physical_wait_permitted` and `real_s10_commit_permitted` remain false.
