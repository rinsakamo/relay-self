## Original B+D Schema3 producer source-byte readback

`experiments.bd1b_schema3_source_audit_dev` reads existing frozen files
in a **separate Python process** with no Paper, Native, GPU or model
connection. It requires four explicitly supplied lowercase SHA256 pins:
the exact original generation `COMMITTED.json`, the producer's result
report, its prelogin original Schema3 manifest, and
`initial-native-paper-source.json`. These are **claims
supplied to the reader**, not an external trusted source or timestamp.

It validates the existing typed World/Self generation, FULL original A/B
Schema3 records, exact *pre-login* canonical original cognition and WAL
bytes preserved separately, matching Registry, both clear WALs, the
producer's Native/Paper initial-source record and original A-first,
A-final and B-final native logout receipt bytes and identities. A/A-reJOIN
must be distinct, B must remain the original native session, and the
producer must state that no model or physical Action was issued.

Usage after an independently preserved new-world run:

```bash
PYTHONPATH=src:. python -m experiments.bd1b_schema3_source_audit_dev \
  --evidence-dir /path/to/evidence \
  --generation /path/to/evidence/typed-world-self-generations/g-000000000000 \
  --committed-sha256 <verified-sha> \
  --report-sha256 <verified-sha> \
  --prelogin-sha256 <verified-sha> \
  --initial-source-sha256 <verified-sha>
```

The program returns `BD1B_SCHEMA3_SOURCE_BYTES_CROSSCHECK_CPU_ONLY`
on matching bytes. It never says that the model, original Paper process,
real Native listener, external operator, timestamp, independent Git
custody or real World was authenticated; the producer's own report can
be forged together with the same mutable local files. A separately
pinned trusted external witness and real source audit remain required
before any real-world qualification.

Old legacy typed generations without original FULL Schema3 and pre-login
source files fail closed. CI tests construct **synthetic original
World/Native/Paper receipt stand-ins**, including forged SHA readbacks.
They are not evidence from the user's WSL, GPU or Minecraft world.

### Strict original A/B first-login binding

The reader now also requires a **fourth independent supplied SHA pin** for
`initial-native-paper-source.json`: `--initial-source-sha256`. It requires
the complete original `InitialSourceReceipt` field inventory for each Self,
recomputes its Native and Paper revisions from raw JSON fields and binds:
- resident epoch=1 / World epoch=0, exact original Self root and original
  A/B native sessions (never the reJOIN session);
- one shared Paper boot, PID, tick ACK source, source log digest, and two
  distinct, correctly matched actor UUIDs;
- initial Native/Paper fields against the later joined producer's original
  report and the typed generation's World/branch.
Re-hashing the receipt and report together does **not** bypass these
semantic checks; adversarial tests explicitly perform that re-hashing.
Neither the revision nor the SHA is an independent real-World signature.
