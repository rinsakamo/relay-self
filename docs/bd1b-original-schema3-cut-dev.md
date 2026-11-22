# BD1b original Owner exploration Schema — typed checkpoint v3

**Opt-in CPU DEV proof, not source authentication of a real Self.**

Existing `SelfOwnerCut` Schema 1/2 JSON encodings are unchanged. The first
original retired A/B cohort with **actual previously registered** exploratory
Schema snapshots uses Schema 3, adding `exploration_schema` and an exact
`cognition_sha256` to the canonical owner-state snapshot. The value
records Self, original Registry revision, module/version/provenance and
explicit `FULL` or `OFF`. It does not derive `FULL` from the
existence of an exploration pattern or a new restore-time setting.

`ResidentCognitiveWorkOwner.retired_recorded_schemas()` requires both A/B
to be completely retired and the snapshots to agree with the exact original
Owner registries. Stage28b reads them from the same original Resident under
its existing lock after the bridge's physical/GPU/native quiescence gate.
A partial A/B registration, foreign snapshot, registry change, or mismatch
between original cognition's persisted Registry and Owner Registry is a
pre-Paper-stop HOLD. Both typed owner files are copied into the existing
generation with the normal bytewise COMMITTED manifest, not a separate
unbound sidecar. Old Stage28b with no registrations stays schema1/2 and
cannot infer activation later.

Stage28c2's inert original A/B rebuild only calls
`bootstrap_restored_schemas(..., source_cuts=...)` when the signed-off
**same generation** contains the records. It performs full-cohort checks
before replaying either original registration while both Self are OFFLINE
and at epoch zero. A caller config can only agree with the cut; it cannot
raise `OFF` to `FULL`. Legacy and partial records HOLD. The replay
does not issue L1, physical Actions, L2 work, any external messages, or
a fresh WorldBody, and remains in observation-only mode.

This closes the **schema missing from typed source format** gap for
newly produced Schema 3 generations. It does NOT retroactively validate
old D9 / Stage28b generations without a Schema 3 source, prove the
origin of a purported original Owner or timestamp, trust a checksum
against an attacker able to rewrite the whole generation, prove crash
durability, or justify real-Gemma/Paper qualification. A real trial
requires a NEW source cut, independently verified original Paper/native
evidence, the model PID/GGUF/GPU/slot gate and a separate-process raw audit.

`BD1b1A2_ADOPT_COMMIT_CPU_OFFLINE_PASS` remains independent; real
`SELF_ADOPT_ISSUER_NOT_ATTESTED`, BD1b/BD1 and QUAL/SCIENCE remain HOLD.
