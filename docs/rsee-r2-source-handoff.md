# RSEE R2 — cross-lane original evidence handoff

Authority: #575; R1 [Draft #593](https://github.com/rinsakamo/relay-self/pull/593) is **frozen** at exact HEAD 7c9a013f10e55172f6415deb9002ce7d4417f504.
R2 is one independent child Draft; S1 #592, L1 #594, V1 #595, their exact lineage, Golden #588, original World/Model assets and protected main are not edited.

## Purpose

S owns original S49 native observation, Action/OUTCOME and session. L may consume only independently admitted observed experience, not an Action authorization. V independently evaluates original evidence and cheap comparators; neither S nor R supplies scientific GO. R2 is the read-only inspection seam between these owners, NOT a second runtime or new evidence source.

R1 already owns plan, preflight, environment/profile/World/binary hashing, source receipt index and provenance envelope. R2 reuses its schema and byte validator; no parallel preflight, Mineflayer process, model lease, scheduler, Action issuer, stateful DB, receipt rewriting or Golden grant is introduced.

A producer supplies its **existing** R1 provenance envelope, but the receiver must independently provide the expected:
- producer and consumer lane (different S/L/V owners)
- exact source commit HEAD (40 lowercase hex)
- RSEE environment profile SHA256
- native session ID
- absolute physical root of existing original raw receipt files
- optional requirement that at least one original Action/OUTCOME reference exists

R2 checks the envelope's source fields against those *independent* values, nonempty original receipt references, index/ref completeness (no unreferenced entries), no duplicates in each reference class, physical canonical originals beneath the independently chosen root, no symlink/ancestor substitution, no RelayUI timeline/replay as original source, and SHA256 of **each** referenced existing original file. The underlying R1 validation and hashing are reused; R2 does not copy or rewrite files.

An exact byte match is classified RSEE_R2_RAW_BYTES_MATCH_REVIEW_ONLY. It is explicitly **not** source authenticity, Action correlation, task-goal success, learning/Habit, cleanup proof, LLM generation qualification, lease admission, backend STOP ACK, physical permission, or science GO. Missing original, foreign source, stale session, expected SHA mismatch, symlink, drift, forged index, presentation projection or oversized/duplicate-key envelope => RSEE_R2_HANDOFF_BLOCKED.

## Operator and lane use

Dry-run without any file access (safe on any branch carrying R1+R2):

    python -m experiments.standard_env.source_handoff --from-lane S --to-lane V

Opt-in **read-only**, assuming an authorized owner already wrote an original, immutable envelope outside Git and preserved all original receipts (R2 never writes either):

    BASE=/home/rinsa/.local/share/relay-self/rsee-1.0-20261011
    export PYTHONPATH="$PWD/src:$PWD/tests:$PWD"
    export PYTHONDONTWRITEBYTECODE=1
    "$BASE/venv/bin/python" -m experiments.standard_env.source_handoff \
      --from-lane S --to-lane V \
      --envelope /absolute/path/to/existing/provenance.json \
      --receipt-root /absolute/path/to/existing/native-originals \
      --expected-head <EXACT_SOURCE_HEAD_FROM_INDEPENDENT_AUTHORITY> \
      --expected-profile-sha256 <RSEE_PROFILE_SHA256_INDEPENDENTLY_CHECKED> \
      --expected-session <NATIVE_SESSION_ID_INDEPENDENTLY_CHECKED> \
      --require-action-outcome

API for V/L: audit_file(path, producer_lane="S", consumer_lane="V",
expected_head=..., expected_profile_sha256=..., expected_session=...,
receipt_root=..., require_action_outcome=True). The incoming envelope cannot select or overwrite the consumer's expected identity. R2 is not permitted to fabricate an envelope for missing #588 evidence or use the Golden index alone as a stand-in for raw originals.

The returned digest of the canonical envelope JSON is a *derived* index for cross-lane comparison, not a digital signature. Cleanup observations are returned as **claims only**, with STOP ACK / GPU / lease qualification explicitly false. A receiving L or V lane must independently validate typed S49 Action identity, evidence source, exact revisions and scientific comparison rules. R2 does not elevate any such claim.

## Tests and ceilings

tests/test_rsee_source_handoff.py exercises S/L/V lane pairs, default no-I/O plan, exact independent HEAD/profile/session mismatch, absent Action proof, empty originals, tampered/missing/ref drift, unreferenced index, foreign root, symlinked ancestry, display timeline masquerade, duplicate refs/JSON keys and oversized envelope. Exact R1 branch ancestry is asserted by dedicated GitHub CI: focused + full inherited Python + Ruff/repository contracts + existing Mineflayer adapter.

No real WSL2 native originals or current GPU/lease conditions are observable in GitHub CI. A green offline CI is SOURCE-CONTRACT_ONLY; operator source readback remains NOT_RUN until performed on the actual machine. Golden approvals are consumed; no Java/Node Minecraft, Mineflayer physical connection, llama-server/model/GPU, LLM POST, native Action, evidence file mutation or live experiment is authorized by R2.
