# BD1b ADOPT-COMMIT CPU/offline evidence audit (DEV)

This gate checks the **already-existing original** Owner/Resident/Bridge/Lane
ADOPT path and deliberately does not grant new cognition or action authority.

## Run focused tests

```bash
python -m pytest tests/test_bd1b_adopt_commit_hostile_dev.py tests/test_bd1b_adopt_audit_dev.py
```

To retain a synthetic successful run's immutable copied input/output bytes,
use a stable pytest temporary directory:

```bash
python -m pytest --basetemp=/tmp/bd1b-audit \
  tests/test_bd1b_adopt_audit_dev.py::test_actual_cpu_adoption_bundle_passes_separate_process
find /tmp/bd1b-audit -name manifest.json -print
python -m relay_self.bd1b_adopt_audit_dev /path/to/audit-bundle
```

The producer test captures the actual synthetic original-class job's submitted
request, ticket, bounded readback, both digests and job consumption state, plus
copied before/after original `cognition.json` and physical WAL bytes. It does
not replace or modify the Self's original file when recording the evidence.

The auditor runs without a model or Minecraft process, checks bytes against
manifest hashes, independently reconstructs request/candidate digests and
validates issuer readback, consumed job binding, one new OPEN Question,
continuity revision, provenance, pending refs and unchanged physical WAL.
Modified, absent, duplicated or truncated evidence is rejected in tests.

## Important limits

- The bundle is **unsigned** and consistency checking is not a trusted seal.
  An actor with write access to the whole bundle could forge coordinated
  content and hashes. Preserve independently if stronger authenticity is needed.
- The synthetic provider and slot witness are **not** real Gemma, a verified
  physical GPU process, or live Paper/Native source attestation.
- In-memory `_Job.question_adoption_state` is **not crash-durable** and does
  not establish reboot replay safety.
- The snapshot's file `fsync` + atomic replace does not attest containing
  directory crash durability.
- This audit does not replace checkpoint freeze / separate-process restore,
  real-World verification, QUAL, SCIENCE or full BD1b/BD1 qualification.

The focused hostile tests are end-to-end commit tests, not only checks of
preceding SOURCE and ISSUER helper functions. All PASS/HOLD classifications
must be based on observed test and exact-HEAD CI results; code existence alone
does not constitute a PASS.


## CI original evidence retention

On the BD1b development head, the exact-head GitHub CI pytest job runs the
focused hostile suite before the full test suite. The successful CPU-synthetic
original bundle is copied to an exclusive archive path, re-audited in a second
subprocess, and uploaded as a GitHub Actions artifact named
`bd1b-adopt-cpu-<exact-head-sha>` for 14 days. The log prints the archive's
manifest SHA256 and every original file SHA256. Fetch the artifact, extract it
into a trusted read-only directory and run the standalone module to reproduce
its self-consistency classification. Retention is for inspection, **not** a
trusted original-owner signature or independently authenticated source.
