# S49 startup custody — scoped adoption candidate v1 (2026-10-21)

**Scope: isolated implementation and CI evaluation, not live World authority.**

## Explicit approval and provenance

The requester explicitly said **「承認する」** in the 2026-10-21 conversation
after receiving the exact-source decision packet:
`docs/s49-protected-owner-decision-packet.md` at
`5e03f7c02cff635996c86c8a850071bb7d639f20`.
This is recorded as **user authorization to prepare a scoped candidate**.
The ChatGPT GitHub connection cannot establish that the requester possesses
each independent source owner's required role, or that W4's separate source
guardian has signed off. **Do not report independent owner attestation from
this statement alone.**

Original instrumented DEV candidate:
`b8a51ac369a31399349d5401cf802304f63e522c`.
Branch for separately checked adoption/CI trial:
`self/product-self-one-command-s49scoped-20261021`.

This review version does not alter the four existing implementation files
or their Git blobs. It modifies only the narrow CI path allowlist and W4
frozen-blob test logic to recognize either:
1. all 19 original frozen SHA1 Git blobs, unchanged; OR
2. the same 15 original blobs **and all four exact S49 reviewed candidate
   blobs together**, with no partial selection and no additional changes.

The immutable original list remains literally unchanged as
`PROTECTED_BLOBS` in `tests/test_self_world_stage_w4_lease.py`; the
candidate fingerprints are a *separate* `S49_APPROVED_CANDIDATE_BLOBS_V1`
constant. This is a candidate matching rule, not an authorization to edit any
future protected source to an unreviewed SHA.

## Four fixed protected blob pairs

| Source | Frozen original Git blob | Approved review candidate v1 Git blob |
|---|---|---|
| `adapters/mineflayer/process_session.py` | `6eec8f80621c581d47154f7c76e72303e00c04f0` | `cf5a979d9da38acbe670973c11d7186ade49dbfe` |
| `adapters/mineflayer/s31a_real_server_ci.py` | `7ee3e95af66e1b981f72509a3dd661d79ef95744` | `04a4b20278844528082f9f5c731350418ac3553c` |
| `adapters/mineflayer/s34_native_world_cognition_ci.py` | `eaecb117ad26059d6d2abb2c12bca61b2dce1f01` | `66728a9667734f4b7164de23f244a938a756dbdc` |
| `adapters/mineflayer/s49_normal_session_real_ci.py` | `fd2b06e9dbed17be0e35b3a1bbd0ed423b9af258` | `c48e22980d19c79e68c381566fb0edc09b346f1e` |

In particular, the S49 target includes the earlier isolated cancellation-safe
finalizer as well as the six-line startup diagnostic propagation. Do not
describe this as an approval for a mere six-line change.

## Explicitly narrowed workflow scope

`.github/workflows/self-demo.yml` continues to compare **all paths since**
the original `B0_PARENT`, and retains its default deny for paths outside
the allowlist. Its three inherited omissions are narrowly corrected:
- `adapters/mineflayer/s31a_real_server_ci.py`;
- `tests/test_s49_native_os_custody.py`;
- `docs/s49-native-os-custody-dev.md`.

One additional exact pathname permits this receipt:
`docs/s49-scoped-adoption-v1.md`.
No wildcard for a protected directory, bypass conditional, or disabling the
existing guard is introduced. Permission to change a path in a candidate
branch is not permission to change its SHA beyond the precise four-blob v1
pairing.

## Regression contract and limits

The W4 historical source test must:
- accept the original 19 historical blob SHA combination;
- accept the atomic four-blob reviewed candidate combination;
- reject any single/pair/triple mix of original and candidate;
- reject arbitrary edits to one of the four candidate protected sources;
- reject edits to any fifth original and any modified protected inventory;
- preserve its original identity checks for the original Node session and S34
  startup owner, and preserve all frozen S18 architecture tests.

Validate Python 3.11/3.12 focused, W4 lease/prehost, Ruff, Node adapter,
repository-contracts, and all tests on one exact HEAD. Distinguish whole-CI
SKIPPED from successful tests. Earlier WSL2 PID/run evidence is DEV context,
**not** execution/qualification evidence for a newly selected candidate HEAD.

The CI rule records only whether source hashes match these exact reviewed
variants. Independent owner approval, the existing single stdout receiver,
the single Action issuer, real Minecraft success-path startup, fresh World
permissions, qualified physical OUTCOME and science preregistration are
independent gates and do not follow from CI green.

**W4_LIVE_NO_GO / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**
until those separate requirements are met. No Minecraft World/bridge was
launched in preparing this versioned policy.
