# R #575 — remaining four M0.2 S50 tick-chord configs: offline preworld identity gate

Date: 2026-10-16 JST. Existing R owner: Draft #610; S product #537 / Draft #545; V #619.
**This is a read-only SHAPE / PROFILE DIFF gate, not a new engineering qualification,
science experiment, authorization, or physical re-execution.** No Java/Node/World/GPU start.

## Immutable qualified anchor and scope

The only R-qualified new-JAR profile is the original physical **BASE_ON**
(`R_M02_V7_NEW_BASE_ON_TICK_CHORD_ENGINEERING_QUALIFIED_ONLY`).
The actual S qualification #38907469772 and R original-byte rereview #38908742143
are pinned in `rsee-m02-v7-base-on-new-jar-engineering-qualification-20261016.md`.
Its 2026-10-16 one-shot grant `USER_M02_V7_TICK_CHORD_BASE_ON_20261016_ONCE`
is **CONSUMED**; the prior 2026-10-15 grant is also consumed.

Identity checks are all exact SHA256:

| Identity | Digest |
|---|---|
| Official Paper 1.21.8 build60 | `8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e` |
| Scoped new tick-chord plugin JAR | `a43afa4d0a1fdaf01c633efd2543ed24b6b53b12ee38ed62a33594057e701e8f` |
| Qualified BASE_ON tick-chord config | `939c2da60ed4ce2f5afb5609c1f784886e3b021104c28a83658c17b744159b16` |
| Original server.properties | `11aaf903bae3d92f3b667f464f301a513bee559f04acc33d722c7a2e966d03ae` |

`tests/fixtures/rsee_m02_v7_tick_base_qualified_config.yml` is a code-side
immutable **reference of the fully qualified config bytes** for negative/identity
testing, independently digest-checked by R. It was reconstructed from the S
source template by prospective `dev-enabled: true` and
`s50-tick-meter-dev: true` selection; it is *not* an authenticated substitute
for the R-reviewed original archive or an operator-supplied host source.

## Four still unqualified profiles

| Arm | BASAL multiplier | WALK multiplier | Qualified? |
|---|---:|---:|---|
| SHAM_ON | 1 | 1 | NO; exact BASE_ON config bytes **do not** confer a separate physical qualification |
| BASAL_ZERO | 0 | 1 | NO |
| WALK_ZERO | 1 | 0 | NO |
| BOTH_ZERO | 0 | 0 | NO |

R independently reconstructs precisely these two multiplier fields from the
pinned BASE_ON config and requires whole-byte equality: every other field,
including default costs, `additional`, Body target, `dev-enabled` and the
tick-chord native writer flag, remains identical. Zero WALK expected setter
input can coexist with genuine motion, and a blocked MOVE is **not WAIT**.
The quantity is expected *source write input*, never automatic native
food/saturation effect or exact sub-tick continuous path.

The new module `experiments/standard_env/m02_v7_remaining_profile_preflight.py`
and `tests/test_rsee_m02_v7_remaining_profile_preflight.py` cover the four
profiles plus negative controls for wrong arm, duplicate/aliased qualification,
altered profile cost, disabled writer, free/negative additional, source mutation,
foreign JAR, wrong World property, missing/aliased file, oversized/empty file,
and CLI read-only behavior.

Example (candidate must be independently provided; does NOT start a World):

```sh
PYTHONPATH=src:tests:. python -m experiments.standard_env.m02_v7_remaining_profile_preflight \
  --base-config-original "$PWD/tests/fixtures/rsee_m02_v7_tick_base_qualified_config.yml" \
  --candidate-config "/absolute/path/to/prospective/BASAL_ZERO/config.yml" \
  --arm BASAL_ZERO \
  --plugin-sha256 a43afa4d0a1fdaf01c633efd2543ed24b6b53b12ee38ed62a33594057e701e8f \
  --paper-sha256 8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e \
  --server-properties-sha256 11aaf903bae3d92f3b667f464f301a513bee559f04acc33d722c7a2e966d03ae
```

Passing verdict is **only**
`R_M02_V7_REMAINING_ARM_CONFIG_SHAPE_ONLY_NOT_QUALIFIED`,
`physical_world_launch_authorized=false`,
`candidate_arm_engineering_qualified=false`. Config SHA and
self-provided binary hashes **do not authenticate source provenance**.

## Strict next S/R boundary (no grant requested or issued by this gate)

For each of the four profiles separately, S must produce a **new physical
QUALIFICATION candidate** only after a *fresh explicit authorization*, with its
own run identity, exact tested source HEAD/CI, original config/JAR/Paper hashes,
isolated World and actual pose/NBT seed, real S50 native MOVE + S51 EAT,
per-tick native BASAL and horizontal tick-chord WALK writer receipts,
full Action journal, original STOP and independently witnessed Node/Java/PID/
port cleanup. Distinct SHAM world/session is obligatory despite equal config.

R must independently inspect the actual new original bytes, archived source
run and grant/attempt, not accept the S producer's `qual_engineering=false`
receipt as a PASS, and issue at most the specific profile verdict. A new JAR
revision requires separately registered identity and proof and may not inherit
this baseline. Aborted preworld gate does not create physical evidence; a
failure after Java start consumes its one-shot grant. No attempts may be
selected retrospectively.

The frozen V7 matched-path 0.005-block condition is separately FAIL, V7
SCIENCE 0/20 and V6 0/48, and G3/production NO_GO. Ecological random-map
failure/collision is a measured World outcome, not a reason to edit WALK
cost or normalize different lengths after observing them. The R qualification
of a mechanism is not evidence that a causal treatment improved survival.
