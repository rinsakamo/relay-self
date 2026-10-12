# RSEE R4 — S3 derived Memory → R2 originals → V review-only handoff

Authority #575. R3 Draft #600 exact `464b289174ab827e0a8d3b7b2ee8c6797c155801` remains frozen. This is a separate R-only Draft. S3 #598, latest S4 #599, L1 #594, V1 #595, R2 #596, main, original Golden and historical physical run evidence are not modified.

## Actual boundary found by source audit

S3's existing owner saves `session_events.jsonl`, `s3_observed_memory.json` and `owned_cleanup.json` in a disposable *operator output* directory. It records `experience_retained_observation` only after a qualified existing S49/S16 terminal. These are S-generated **derived records**, not original raw native observations or a signed World goal. The digest in S3 Memory identifies a canonicalized decoded native frame representation; it does **not** equal the hash of an arbitrary original file, so R4 deliberately does not equate them.

The last separately authorized S2 physical World run recorded 181 outer observations and **zero** correlated probe, Action or OUTCOME. S4 correctly observes that it archived no individual raw outer native frame. It is *not* an S3 retained-Memory trial, and R4 must not invent S3 output or reconstruct native frames from the event count. Original WSL2 source and R1 envelope were not provided to this lane; physical handoff remains NOT_RUN.

## R4 behavior

`experiments/standard_env/s3_v_projection.py` is a passive consumer. Default `plan()` / CLI invocation reads no files and starts no process. Opt-in independent operator input consists of:

- expected exact S3 source HEAD `6f493b7a559dd72ea365998b9eadbd35fd7eb9b4`, expected RSEE profile SHA256, expected original Mineflayer session ID;
- already-existing physical S3 output directory, containing the three named files above;
- **separately-existing** R1 provenance envelope and raw native/Action originals under an independently selected physical root.

It loads the S3 event JSONL with bounded length, duplicate-key prevention, exact session/index/order/terminal/source checks. It decodes the existing `PersistentCognition` snapshot using the project's original Memory owner and compares the original S3 event retention IDs/digests/source sequence against the stored L1 `L1_SOURCE_EPISODE_V1` content. Contradictory, absent or extra retained records, UNKNOWN, unexpected S10/S11 grants, missing cleanup, derived-path symlink, missing terminal or forged Action authority BLOCK the handoff.

**Zero retained Action** ⇒ `RSEE_R4_NO_RETAINED_ACTION_NOT_V_ADMISSIBLE` and **CLI exit code 2** (not success). R2 original bytes remain `NOT_CHECKED`, no V admission, no science/physical success. This is a negative result about an existing S3 projection only, not proof of complete World observation.

**One or more matching derived observations** ⇒ R2 must independently check the actual immutable raw original and Action/OUTCOME files using an independently supplied existing R1 envelope. Missing or tampered original or source mismatch blocks. The S3 Memory/event/cleanup/envelope files are forbidden as original native evidence. Positive status `RSEE_R4_DERIVED_MEMORY_MATCH_R2_BYTES_REVIEW_ONLY` confirms **derived record consistency plus file byte matches**, not native Action semantics, independent execution authenticity, task-goal success, backend STOP ACK, resource release, S10 learning, S11 Habit or a scientific result. V must still independently adjudicate all of those.

### Usage

Default side-effect-free plan:

```bash
python -m experiments.standard_env.s3_v_projection
```

Operator *read-only* inspection after independently obtaining a genuine, already-existing R1 envelope and raw originals (illustrative paths, do **not** create placeholders or fabricate a source record):

```bash
BASE=/home/rinsa/.local/share/relay-self/rsee-1.0-20261011
export PYTHONPATH="$PWD/src:$PWD/tests:$PWD"
export PYTHONDONTWRITEBYTECODE=1
"$BASE/venv/bin/python" -m experiments.standard_env.s3_v_projection --verify \
  --derived-root /absolute/original/s3-operator-output \
  --original-root /absolute/original/native-receipts \
  --envelope /absolute/existing/r1-provenance.json \
  --expected-head 6f493b7a559dd72ea365998b9eadbd35fd7eb9b4 \
  --expected-profile-sha256 '<independently-verified-real-profile-sha256>' \
  --expected-session '<independently-verified-original-session-id>'
```

The R4 program does **not** write a V record or provide an admissible Action grant. Tests use isolated mock fixtures to exercise the negative paths; they are NOT historical recreation or physical native source qualification.

## CI and ownership

Dedicated offline GitHub Actions workflow runs R4/R3/R2 focused tests, full inherited regression, Ruff/contracts and Mineflayer adapter, plus independently checks the frozen S3/L1/V1 behavior and S4 offline observation audit at their exact original HEADs in separate ephemeral checkouts. No branch merges; no R changes to S/L/V/S4. GitHub CI does not read the operator's WSL2 RSEE model, stopped World or raw native originals.

S owns original Mineflayer receipt and S16 terminal semantics; L owns historical Memory and read-only hints; V owns independent outcome/science qualification (existing G3 NO-GO). R only compares existing bytes, identities and derived source representation. Physical trial authorization, model leases, native source generation and science GO are never conveyed by R4.
