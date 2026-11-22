## Original B+D Schema3 producer source-byte readback

`experiments.bd1b_schema3_source_audit_dev` reads existing frozen files
in a **separate Python process** with no Paper, Native, GPU or model
connection. It requires three explicitly supplied lowercase SHA256 pins:
the exact original generation `COMMITTED.json`, the producer's result
report, and its prelogin original Schema3 manifest. These are **claims
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
  --prelogin-sha256 <verified-sha>
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
