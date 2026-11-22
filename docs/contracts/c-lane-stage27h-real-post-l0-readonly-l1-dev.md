# C Lane — Stage27h original REAL runner post-L0 bounded L1 REVIEW (DEV, read-only)

This is an **opt-in execution path on the existing original Stage27h real
Paper/Mineflayer/Gemma runner**. It is not a replacement for Stage27h/i,
not a new physical issuer or autonomy qualification, not a C1 adoption or
Stage28 post-action checkpoint. It stacks on the C Lane multi-Action code
in Draft #1033; original Stage27 #990 and Stage28 #988 remain untouched.

## Runner invocation

In a *LocalCodex/operator environment* with the original jar files and a
single idle loopback llama.cpp Gemma slot, all original SHA prerequisites:

```bash
PYTHONPATH=src:. python -m experiments.p0d_stage27_real_place_move_dev \
    --paper-jar /absolute/Paper-1.21.8.jar \
    --paper-sha256 <exact-paper-jar-64-hex-sha> \
    --plugin-jar /absolute/p0d-original-plugin.jar \
    --plugin-sha256 <exact-plugin-64-hex-sha> \
    --scratch-parent /absolute/isolated-DEV-world-parent \
    --eula-accepted --real-world-dev-grant \
    --gemma-l1-endpoint http://127.0.0.1:8080/v1/chat/completions \
    --gemma-l1-model <actual-loaded-Gemma-model-name> \
    --stage27h-l0-move-loop --c-lane-stage27h-post-review
```

The flag requires Stage27h; it explicitly **rejects** Stage27i, Stage27g and
other mixed run modes *before* entering the World launcher. Stage27i's frozen
A/B + **two-initial-HTTP-POST** census remains unchanged. The real runner
still independently checks operator EULA and DEV grants, pinned jar SHA,
live Paper/native sessions, WAL and real Gemma bounded one-slot setup.

The existing Stage27h original L0 MOVE loop, PREPARED fsync snapshots, native
STOP readbacks and Paper-correlational evidence execute **unchanged**.
If its final result is not `L0_TARGET_REACHED_YIELD_EVALUATION` with 2–4
closed original physical Action/WAL rows, this opt-in HOLDS and does not make
the new L1 request. No physical Action retry follows.

If L0 reaches Target, it invokes
`capture_stage27h_real_post_l0_readonly_review` **inside the original
live motor-hook**, before its native A raw stdout audit is finished.
Before submitting the extra HTTP POST it writes the immutable
`c-stage27h-before-post-l0-l1.json` using exclusive create and fsync, including
original WAL SHA, child Action IDs, original Skill STARTED and negative
Goal/C1/authority flags. This survives a later L1/transport failure.

Then it performs exactly one new post-Action bounded review through the
existing shared resident single-slot inference lane. A *new* owned native
request-correlated probe is obtained **only after model response and GPU
idle**, correlated by an independent read of the exact original A native
stdout JSONL (request ID + seq exact-once). The original A Owner adopts it as
CURRENT WorldBody; this does **not** imply Skill success.

On success, a second immutable
`c-stage27h-post-l0-l1-witness.json` captures exact original source World,
original Action IDs/WAL digest, model selected number, model original raw
request+response SHA256, exact-once native stdout readback, and explicit
**false** flags for C1 written, Skill terminal, Goal success and physical
issue grant. The original parent still freezes its complete motor-hook
return through its original result-contract and issues no new physical
Action. Model number 2 is REVIEW_COMPLETION **only**, never the Self's
separate explicit terminal Skill/C1 approval.

This is intentionally Stage27h only: Stage27i's existing exactly two
original model calls cannot truthfully be reported as unchanged after
requesting another bounded L1. Reconciliation of that precise gait source
protocol is a later task; do not bypass its original census.

## Tests and limits

The tests use the original Stage27h 3 physical Action interpreter/Journals
and its *synthetic* native, Paper and HTTP provider. A second scripted HTTP
choice is observed after L0, matching original frozen pre-review WAL and
post-L1 native exact-once simulated stdout record. Preflight rejects
cross-World, foreign process, forged source, illegal mix of modes, terminal
Skill already adopted, etc. Missing native stdout causes HOLD even after
a model response; before-HTTP frozen source remains.

**Not proven by these tests:** true Gemma model provenance, native/Paper
causal attribution, independently issued Self acceptance, terminal Skill/C1
adoption in a real World, Stage28 post-action World+A/B COMMITTED generation,
new native rejoin or C2/L1 learning improvement.

The user has previously granted standing Minecraft EULA agreement and
real-World **DEV** permission for LocalCodex in this project. This is not
QUAL or SCIENCE approval. No fresh user prompt is necessary for those
already approved DEV prerequisites; CLI flags remain explicit so the exact
invocation is auditable. The ChatGPT GitHub runner cannot operate the local
Minecraft/Paper/Gemma host.

Classification after offline CI:
`DEV_REAL_RUNNER_READONLY_L1_HOOK_SYNTHETIC_TEST /
REAL_WORLD_POST_L0_REVIEW_NOT_RUN / REAL_SELF_APPROVAL_NOT_ATTESTED /
REAL_C1_NOT_ADOPTED / QUAL_NO_GO / SCIENCE_NOT_RUN`.
