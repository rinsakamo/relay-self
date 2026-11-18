# Stage24g — repair independent Paper resident witness preflight (DEV)

Parent #911, predecessor #946 / Draft PR #947, child #952.

## Original immutable observation

Stage24f HEAD `732776328808c2bf0e114fcbb690f79dd4c5777e` one-shot real DEV:
Gemma selected `MOVE(relative:forward)` and native raw/WAL attested
`NATIVE_MOVE_SETTLED`, net 1.723147m, START/STOP/settling. Paper log had
`P0D_TICK_READY` and `P0B_PLAYER` but lacked `P0D_RESIDENT_READY` and
`P0D_RESIDENT event=...`. Final independent Paper join failed, hence HOLD.
World-only restart not observed. Preserve all Stage24f original 248 files; its
SHA256SUMS manifest digest is
`efddde94ae29419b6c0071699d88d6f1eaadad939f73248d9abd1118cb47288b`.

## Proven source mismatch and unproven Jar hypothesis

`ResidentPresenceWitness.java` emits Paper-main-thread resident boot and
independent JOIN/QUIT/PRESENT/MOVE. `Recorder.onEnable` registers it. The
existing `prepare_assets` previously required only `Recorder.class` and
`TickWitness.class`, allowing an older plugin to pass preflight despite
lacking the independent witness class. Whether the exact Stage24f plugin Jar
lacks the class is still to be checked by the local operator against the
original pinned SHA `cabf144a275c1582ecbbdcb6fb394b311f0705f5ca7d330bb80659437abe324e`.
Do not treat source presence as proof of compiled binary identity.

This branch adds two orthogonal fail-closed checks:

1. Before World: `prepare_assets` requires
   `io/github/rinsakamo/p0b/ResidentPresenceWitness.class` in the exact Jar
   and still verifies hash, plugin manifest, no symlinks and no model effects.
2. Before Gemma or MOVE, after authentic native A+B join, A logout and native
   B probe: read bytes **only** from `OwnedPaperWorld.read_owned_log`, archive
   those pre-inference bytes, require exactly one `P0D_RESIDENT_READY`, source
   qualified resident A/B JOIN, A QUIT and B PRESENT/MOVE after that QUIT.
   Failure is HOLD before any new model selection. This is an *observer
   readiness contract*, **not** a physiological GO/NO-GO test.

Keep the final `join_resident_paper_presence` strict: full A rejoin +
independent B movement/presence. Do not replace `P0D_RESIDENT` with
`P0B_PLAYER`, guess Paper movement from native position, infer action-ID
causation, relax UUID/boot/tick/source integrity, or generate fabricated
observation events.

## Remaining local prerequisite before a new real trial

The Stage24b launcher **still deliberately pins the historical plugin
digest**. Do not silently edit/reuse that pin to admit another jar. The
Stage24g operator must first:

1. Independently inspect the exact archived Stage24f P0BRecorder.jar
   (`sha256sum`, `jar tf`, `javap`, plugin enable/owned log). Record
   presence or absence of resident class and its linkage, as primary evidence.
2. Compile the current observer source from an isolated Stage24g worktree
   with Java 21; archive the new exact Jar SHA256 and build logs. Validate
   one owner listener and the real Paper main-thread resident events using
   independent isolated bootstrap/observer inspection.
3. Add a separately reviewed **Stage24g-specific pinned asset launcher**
   with that exact new Jar hash (not an unreviewed caller-provided digest).
   Keep historical Stage24b pin and Stage24f evidence immutable.
4. Add exact raw SystemOne HTTP request/response/status capture where source
   isolation permits. If not archived, record `model_raw_http_bytes_archived=false`;
   never reconstruct raw bytes from a parsed response.
5. Only after offline CI, independently verified pin, owner patch, and
   pre-inference Paper witness readiness may a **new** one-shot isolated real
   World and one real Gemma selection occur. No retry of Stage24f or
   manually selected MOVE. Complete World-only checkpoint/restart only after
   independent final Paper join qualifies.

Until then: `STAGE24G_OFFLINE_ONLY / REAL_WORLD_NOT_RUN /
QUAL_NO_GO / SCIENCE_NOT_RUN`. A model choice and native terminal alone are
not the Paper or checkpoint success classification.

## Local binary audit and observer-only DEV (2026-11-17)

The original Stage24f jar contains `Recorder.class`, `TickWitness.class`, and
`plugin.yml`, but no `ResidentPresenceWitness.class`; its `Recorder.onEnable`
bytecode starts only the tick witness. The archived Paper log confirms plugin
startup and tick events, with no resident boot or events. This establishes
that the executed binary lacked the resident witness registration present in
current source. The original evidence was read-only and its manifest verified.

The locally rebuilt Java 21 jar, archived at
`/home/rinsa/evidence/stage24g-witness-20261117/P0BRecorder.jar`, hashes to
`0b20dd042231618fc301bbe26ee48c5808c09dafddc946c49f4393ca48386fb5`.
Its bytecode starts the resident witness. A distinct real Paper observer-only
DEV World recorded both joins, A quit, B presence after that quit, and A rejoin.
This did not use Gemma or issue a B physical action. It does not establish MOVE
correlation or a checkpoint.

`stage24g_pinned_assets_launch_dev` independently pins this exact local jar and
provides read-only inspection. Execution deliberately remains HOLD: the
independent GPU/model/WAL gate and HTTP raw capture are not implemented. Do not
use another launcher to bypass that HOLD. This is partial DEV, not QUAL or
SCIENCE, and does not change the Stage24f terminal.

## Model/WAL/HTTP gates implementation (2026-11-18; code DEV only)

At the head of this branch, Stage24g's dedicated
`experiments.stage24g_pinned_assets_launch_dev` supports `--execute-once`
**only after all read-only source checks succeed**. It remains distinct from
the historic Stage24b launcher and its old binary pin.

The operator must discover real absolute paths/PID from this WSL2 host
(no synthetic model aliases/PIDs). Before World creation the launcher checks:
- pinned Paper 1.21.8 build 60, new independently attested observer Jar
  SHA256 `0b20dd042231618fc301bbe26ee48c5808c09dafddc946c49f4393ca48386fb5`,
  worktree-local patched Mineflayer, Java 21 and Node 22;
- GGUF as regular non-symlink file and exact independent SHA256
  `c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed`;
- operator-owned live llama-server PID with that same model pathname
  in its command line **and /proc/PID/maps**;
- matching PID in read-only `nvidia-smi --query-compute-apps=pid`,
  an RTX 3060, exact model alias from read-only GET `/v1/models`, and
  a single idle `/slots` entry `id=0`. Missing or malformed sources HOLD
  rather than bypass. No model POST or World is created during this gate.

The original World runner then creates *new* per-Self WAL files using
`PhysicalActionJournal.create` and independently restores both before
Gemma. For Stage24g, both must have zero records, no unresolved action and
equal canonical digests. The initial WAL SHA and digest are archived under
the trial's evidence root before any real inference.

Exactly one original SystemOne POST uses the existing
`LlamaCppRelayProvider` with a new private, empty evidence directory.
It fsyncs the **exact UTF-8 request entity bytes** before sending, and
the **exact response entity bytes** plus actual HTTP status/digests before
parsing and model decision adoption. A second POST on the same evidence
directory fails closed **without sending anything**. Transport failure
can leave only the request bytes; no response is fabricated. If response
or status is missing/modified, the independent final trial report remains
HOLD. This is an HTTP *body* capture, **not** full wire-level headers/TLS
bytes; do not claim packet-capture completeness.

### One-shot operator invocation (after exact HEAD CI and model startup)

First perform `--inspect-only` with the pinned assets, as before. Then
run exactly one new isolated integration experiment:

```bash
PYTHONPATH=src:. python3 -m experiments.stage24g_pinned_assets_launch_dev \
  --paper-jar "$PAPER_JAR" \
  --plugin-jar "$STAGE24G_P0B_RECORDER_JAR" \
  --scratch-parent "$NEW_EMPTY_TRIAL_SCRATCH_PARENT" \
  --eula-accepted --execute-once --real-world-dev-grant --grant-real-llm \
  --llama-endpoint "$LLAMA_ENDPOINT" \
  --systemone-endpoint "$SYSTEMONE_ENDPOINT" \
  --model "$ACTUAL_MODEL_ALIAS" \
  --gguf-path "$ACTUAL_GGUF_PATH" --llama-pid "$OWNED_LLAMA_PID" \
  --java "$JAVA21_BIN" --node "$NODE22_BIN" --timeout-s 120
```

Do not execute this from GitHub CI or substitute fake values. The model
process is assumed **already loaded by its actual owner**. This launcher
never starts/kills the model. Original Paper and native worker ownership
remains with `run_real_resident_presence`. Stage24g is a **new** World and
must not re-use or retry the prior Stage24f attempt.

A successful preflight/CI alone does **not** prove integrated World
movement or checkpoint. The final PASS/HOLD still depends on frozen L1
selection, original Native WAL and independent Paper resident events
and the World-only generation readback. `QUAL_NO_GO / SCIENCE_NOT_RUN`
until a separately attested real outcome is obtained.
