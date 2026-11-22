# BD1b — original Paper/Native Schema3 producer opt-in

The old Stage28b real launcher still behaves exactly as before.

`experiments.stage28b_pinned_typed_cut_launch_dev` accepts
`--record-exploration-schema3` *with* `--execute-once`,
`--real-world-dev-grant`, an explicit accepted EULA and the already
pinned Paper/plugin jars. It reuses the existing one-World,
one original A/B Resident, existing native login/logouts and existing
typed generation capture. It does not create any new LLM, physical
Action, owner, side scheduler or L2 request.

With this opt-in the producer requires original Native/Paper initial
source and registers exploratory FULL before first login. The canonical
original Owner `PersistentCognition.pattern_registry` is saved before
the first native login, then the original A/B cognition and WAL bytes
are copied once into an evidence directory using exclusive writes. A
pre-login manifest records each original Self, registered module mode,
Registry revision and the corresponding original files' SHA256. An
existing cognition file, already-online Self, mismatched/partial
registration or prior WAL/Intent/Skill history fails closed.

After real A/B logout, Stage28b saves the same original Owner's new
Schema3 source in its typed `owner-state.json`, as implemented in the
previous gate. The runner checks that both saved snapshots remain
FULL, the new generation is type-validated, and an initial Native/Paper
source is present. The producer's report explicitly marks external
independent audit false.

**Do not use existing Stage28b/D9 generations without Schema3** for
a real ADOPT. Only a fresh source, independently witnessed and pinned,
can pass this new path. Neither in-process SHA256 nor our synthetic CI
tests prove real actor identity, timestamp, Paper native state, GPU,
or true model inference. There is no automatic real World launch from
GitHub Actions. DEV only; `SELF_ADOPT_ISSUER_NOT_ATTESTED`,
BD1b/BD1 and QUAL/SCIENCE remain HOLD.

### One opt-in execution on the owner's WSL (not GitHub Actions)

The following commands are an **operator-local** recipe, not a report that
the run happened. First verify the exact pinned Paper/Plugin binaries and
the WSL Java/Node/Paper preflight. Use only one new isolated World run, and
never replay a HOLD or uncertainty in the same source.

```bash
PYTHONPATH=src:. python -m experiments.stage28b_pinned_typed_cut_launch_dev \
  --paper-jar "$PAPER_JAR" --plugin-jar "$PLUGIN_JAR" \
  --scratch-parent "$SCRATCH_PARENT" --eula-accepted \
  --execute-once --real-world-dev-grant \
  --record-exploration-schema3
```

The runner prints the real path of the output report. If and only if the
run finishes without HOLD, identify its unique `evidence/` folder and
new `typed-world-self-generations/g-*/` path. Independently archive
the original logs, four source files and SHA pins BEFORE invoking the
separate-process readback:

```bash
sha256sum \
  "$GENERATION/COMMITTED.json" \
  "$EVIDENCE/resident-presence-result.json" \
  "$EVIDENCE/stage28b-schema3-prelogin.json" \
  "$EVIDENCE/initial-native-paper-source.json"
PYTHONPATH=src:. python -m experiments.bd1b_schema3_source_audit_dev \
  --evidence-dir "$EVIDENCE" --generation "$GENERATION" \
  --committed-sha256 "$COMMITTED_SHA" --report-sha256 "$REPORT_SHA" \
  --prelogin-sha256 "$PRELOGIN_SHA" \
  --initial-source-sha256 "$INITIAL_SHA"
```

All variable paths and hashes must come from the actual just-finished
isolated run; NEVER fill them from CI fixtures, old Stage28b generations,
or another Actor's files. The second command checks **internal raw
consistency**, not independent real-World authenticity: ensure a separate
trusted witness retains source identity/time/custody before any claim of
verified original Paper/Native. A successful local readback does not
authorize Gemma L1, ADOPT, physical Actions, QUAL or SCIENCE.
