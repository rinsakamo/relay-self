# B-NP1b-2f — opt-in original real-World runner CPU Present, no real run claimed

This stage stacks on B-NP1b-2e #1101 (exact source branch
`f13ce9491353b2580282959eb0f14c0b51745be2`).
It wires the **existing owned disposable Paper/Mineflayer DEV runner** into
the original Bridge's verified A/B Native/Paper reJOIN and periodic CPU
Present/Inquiry implementation. It does not install a second Owner, scheduler
outside the original Resident, action executor, GPU job, or Question ADOPT.

## Operator-gated DEV opt-in

The normal World runner is `experiments/p0d_real_resident_presence_dev.py`:

```bash
python -m experiments.p0d_real_resident_presence_dev \
  --paper-jar /absolute/path/paper.jar --paper-sha256 <verified-hash> \
  --plugin-jar /absolute/path/P0BRecorder.jar --plugin-sha256 <verified-hash> \
  --scratch-parent /absolute/existing/scratch \
  --eula-accepted --real-world-dev-grant \
  --exploration-schema-dev --normal-cpu-present-dev
```

**No credentials, jar hashes, filesystem paths, EULA or World grants are
created by this code.** The runner still uses the original preflight and
disposable owned server. No default mode is changed. The option must be
explicit and is fail-closed if combined with `--initial-source-dev`,
`--world-only`, `--typed-owner-cut-dev`, selected MOVE, autonomous L1,
real-LLM or model-receipt mode; exploration Schema must be bootstrapped
fresh. `--b-heartbeat-s` remains bounded to [2, 12] seconds. The
option itself does not grant a real World run.

## Original owned lifecycle

1. Launch one disposable owned Paper and two original Mineflayer native
   sessions. Register fresh original A/B Schema, physical WAL and original
   Owner exactly as the existing runner does.
2. After original Paper heartbeat readback, call the existing
   `build_initial_source_receipts` for A/B. Freeze both original initial
   receipts. Without changing B, independently wait for the later
   Paper heartbeat; `update_fresh_native(A)` receives and Owner-adopts a
   correlated A Native probe, then existing `build_current_composite_source`
   qualifies a *new* original A Native/Paper Composite. Freeze its receipt.
3. Call the original `bridge.logout(A)`. While A is **OFFLINE** and the
   original proof is retained, `update_fresh_native(B)` adopts B's next
   correlated Native observation on the *same* initial B session. The
   adapter helper requires A's original offline retirement, forbids a
   forged B receipt and crosschecks the original A retirement before and
   after the B adoption. The previous runner's read-only B probe is kept
   for all other modes.
4. Original `bridge.login(A)` produces a new A native session and Owner
   epoch. Wait an owned Paper heartbeat to establish a B PRESENT after
   A JOIN. Requalify A's original history, B's continuous session and
   newest Native, A QUIT/JOIN and B post-reJOIN main-thread Paper events.
5. `exercise_original_normal_cpu_runtime` binds original history once,
   starts two **original Resident** CPU tasks (never an external runner
   timer), observes each Self's current Present/Inquiry in one verified
   Paper cut, then **adopts another genuine B same-session Native probe**.
   A/B scheduled readouts must each advance in iteration, share the
   latest qualified Paper cut, change pair revision and demonstrate that
   B's revised Native propagates through both A and B Composites.
   It stops the DEV scheduler and retains the original Owner task ledger.
6. Freeze CPU source evidence to
   `normal-cpu-world-source-readback.json` using exclusive create,
   fsynced writes, SHA256 and immediate byte readback. Before promoting
   any classification the top-level runner independently rereads it and
   checks original A retirement session vs reJOIN, unchanged continuous
   B session, B updated request/seq/revision, distinct Paper actors,
   original per-Self CPU token epoch/task refs, both advanced iteration
   counts, A/B Paper source equality, B/A continuity reference,
   A Composite revision reference, and a deterministic recomputed
   A+B pair revision for both source cuts.
7. Run the **original** A/B logout and physical/cognition retirement
   checks. No Physical Action, L1/L2, Peer transport, QUAL or SCIENCE is
   inferred. The only new successful real-run *if ever exercised and
   independently observed* classification is
   `REAL_PAPER_AB_NORMAL_CPU_PRESENT_SCHEDULED_DEV`.

## Limits, admission and HOLD

- No real Paper, Mineflayer, Java, GPU or Minecraft World was available in
  the GitHub-only CI environment. The run was **not** executed there;
  CPU/offline fixture tests use an original decoded Native process session
  and an owned synthetic Paper stream.
- This is a *single original A logout/reJOIN* sequence. Second and further
  A reJOIN cycles are not automatically qualified: `_b_np1b_retired_login`
  and the initial history verifier are specific to the original retirement.
  The active scheduler cannot be silently rearmed across a second
  reJOIN. **MULTI_REJOIN_REARM_HOLD** is explicit.
- Frozen file SHA protects against accidental change relative to its
  recorded digest, but is **not** an independent external signature or
  authentication boundary if an adversary can rewrite both the file and
  the digest. Real success requires separately owned process and source
  evidence, not JSON fields alone.
- Paper and Native clocks remain independent. Source revision equality
  describes a verified cut at readback, **not** simultaneous clock ticks
  or causal physical action attribution. CPU periods are not realtime
  guarantees.
- Real World / real LLM, multi-reJOIN rearm, independently authenticated
  restored Schema, E2c independent SenseFrame, Question ADOPT, Physical
  Action, QUAL, SCIENCE are all HOLD/NOT RUN until their own evidence.

Parent Issue #1047, prior Draft PR #1101.
