# BD1b live original issuer admission (DEV)

`relay_self.bd1b_real_issuer_preflight_dev.inspect_bd1b_real_issuer` is
a read-only **before first POST** guard. It requires the real original
`OwnedResidentPhysicalBridge`, its one Resident RLock and original
A/B online owners. Both owners must already hold a qualified FULL
exploration Schema with EXPLORATION_NEED before this source cut. Their
registry revisions, Native probe, Paper source and prepared OPEN inquiry
are checked again on both sides of the read-only live model gate.

The second check binds exactly the previously prepared `CoverageAdoptionTurn`
and the same owned PID/GGUF, loopback socket, GPU, model alias, one idle
slot via `verify_stage24g_model_gate`. The gate **never** injects
an exploration mode, target, Preset, number choice, Ticket or synthetic
response and **does not** itself call the provider or attach the GPU lane.

**Critical current blocker**: Stage28c2b source snapshots do not
persist/audit Schema activation. `bootstrap_restored_schemas` intentionally
refuses restoration, so recovered original Owners with just a restored
PatternRegistry cannot qualify. Trying to set `_present_schemas` or
`pattern_registry` on an active restored Owner to force a real ADOPT
is a provenance violation. This preflight reports
`RESTORED_SCHEMA_ACTIVATION_NOT_ATTESTED` before any POST. Do not use
a test-only monkeypatch as a substitute for trusted activation or a
successful independent checkpoint verification.

A future fresh-World original B+D runner may use
`bootstrap_fresh_schemas` during owner creation before the first login
and then call this gate. A restored run needs a separately qualified
activation receipt in the persisted generation; not derived from a
UUID, a local hash, a previous synthetic result or the model's answer.

CPU tests use synthetic source/model receipts only; they attest neither
real-Paper nor real-Gemma provenance, and do not upgrade
`SELF_ADOPT_ISSUER_NOT_ATTESTED`, BD1b/BD1, checkpoint
freeze, QUAL or SCIENCE.
