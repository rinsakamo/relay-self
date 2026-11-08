# D14 R4 — natural World, original S49 bounded owner reactions (DEV)

Parent: #807 (natural R3 observer), #805 (Paper 10,000-tick horizon). This
child starts from R3 verified HEAD `e66f8d91adda6f502e20b58726dee132918c91b7`.
The uncommitted LocalCodex changes on the user's WSL are **not imported**.

## Change

- `tools/bug0_d14_natural_world.py` retains its R3 passive default.
  A separate opt-in callback runs between Paper timeline reads; it does not
  fabricate source ticks or overwrite the R3 observer/audit.
- `tools/bug0_d14_natural_active_world.py` requires the R3 three DEV grants
  **and** `D14_R4_NATURAL_S49_ONEWORLD_ONLY=1`.
- One Self, World, Mineflayer session, active Intent, and original
  `NormalSessionActionExecutor` / `ActionSupervisor`. L0 observes **two
  fresh native probes** per decision. A genuine close, stable single zombie
  may cause S49's ATTACK fallback; safe native appetite/food may request EAT.
  Both still require the existing S49 typed two-stage admission.
- The original S49/S51 native effect and S16 OUTCOME path is unchanged.
  `OriginalS49NonMotionFence` fsyncs **PREPARED** before physical ISSUE and
  closes only on genuine outcome. `UNKNOWN` is unresolved and a hard stop.
  The owner does not auto-repeat or resurrect.
- The append-only derivative journals each native L0 decision and closed
  Action alongside Paper original markers; report and nonmotion fence are
  stored *outside* the disposable World root. Independent R4 post audit
  matches Paper tick sources, typed persisted physical receipts, IDs, and
  the report. Source-only observation cannot prove causality or learning.
- R4 caps **64 L0 decisions and 32 nonmotion Actions** per one-use World,
  then observes passively to real Self death or Paper's 10,000-tick limit.
  This cap is a resource boundary, **not** an attainment criterion.

## What this does NOT yet connect

The original S49 MOVE_AWAY path requires the S14 execution binding and its
separate durable MOVE fence. R4 refuses to synthesize it from ATTACK, teleport,
native Mineflayer movement, or a weaker World. Post-MOVE STOP/settling and a
generalized Intent rearm remain unconnected. REST expresses only a passive
intent; it cannot attest fixed-world fatigue recovery. No C1 Intent result
commit, Memory write, Habit promotion, or L2/Gemma request occurs.

R4 therefore is a bounded natural active owner **increment**, not a finished
10,000-tick self-sufficient life loop or a successful MOVE/EAT rotation.
It can correctly yield zero S49 Actions, observed death, failed ATTACK admission
or a natural zero drop. Those are evidence, never reasons for an automatic
rerolled World or artificial Hunger/Health changes.

## World constraints

R3 `minecraft:normal` terrain, Survival, normal difficulty, unmodified ambient
Mob spawning, vanilla zombie AI and health, unchanged daylight combustion,
hunger/food, drops and death. Only the already-declared experiment-owned
managed initial zombie and genuine death+600 Paper ticks respawn are retained.
No imported D4/D8 operator commands or enemy teleports.

## Offline and real-use gate

Offline workflow:
`.github/workflows/unified-v05-d14-r4-natural-s49-offline.yml` runs repository
contracts, R3/D14/D12 negative regressions, R4 L0/fence negatives, Ruff,
Paper Java plugin build and pure Java tick/respawn tests.

Separate **one-use** workflow:
`.github/workflows/unified-v05-d14-r4-natural-s49-oneworld.yml`.
The World run does not fire on normal pushes. It requires an explicit subsequent
documentation-only commit of the exact trigger message and parent source SHA.
Artifacts preserve even failed/partial originals and SHA256SUMS.
An independent audit is run only after a clean source report, never rewrites
a failed original job. The evidence directory includes original Paper log,
derivative JSONL, owner nonmotion ledger, report, independent audit and
SHA256 manifest. No automatic retry.

Classification: `DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.


## Original first real-World attempt: preserved FAIL, **not** a Self-life result

- Real run: https://github.com/rinsakamo/relay-self/actions/runs/42531022524
- Original artifact: https://github.com/rinsakamo/relay-self/actions/runs/42531022524/artifacts/13637695441
- Executed one-use HEAD: `d91678313b5543543b106a4ac2a52e82c8ab4648`.
- Paper original SHA256:
  `91c19fd5a22dead7a3ed55fbad4b82894f54cc46528c0c7c494743e04d5665d2`.
- Report SHA256:
  `5682f1a258fdd91c16d8488f6e6f596e5c92adbe62d260841c0d644dbb7afd30`.
- Paper log: `RSELF_RESPAWN_FAULT reason=INITIAL_ANCHOR_OR_MANAGED_ENTITY world=null generation=0`.
  The arbitrary generated World had no valid supporting ground at the
  former fixed +6X, same-Y managed zombie spawn. **World initialization**
  failed before an endurance START. Not a Self death or 10,000tick run.
- Real S49 physical Actions **0**, S16 outcomes **0**, native L0 life
  decisions **0**, C1 experiences/learning **0**. Java and Node exit 0,
  report status **FAIL**, original source/audit not rewritten.
- The evidence ZIP contains 6 files (including the originally empty
  derivative journal, durable nonmotion fence, SHA256SUMS). No retry
  on that original.

## Corrective change — natural terrain anchor, not artificial survival aid

The Paper plugin had blindly placed the experiment-owned initial zombie
at `Self position +6 X`, **using Self's Y coordinate**. A normal hilly
World legitimately leaves that proposed block inside stone, unsupported
air or water. R4 now searches a deterministic, bounded list of sites
4–9 horizontal blocks away and ±8 vertical blocks, strictly using
real, unmodified Paper block passability and solid supporting terrain.
No player teleport, no block changes, no biome/seed intervention,
no zombie weakness or AI manipulation. If no safe anchor exists,
World still fails closed. On accepted natural site, the Paper original
now logs `RSELF_NATURAL_ANCHOR` with actual Self/zombie coordinates.

This is an explicit adjustment to the experimental **managed zombie
placement** rule; it does not make the World unmodified vanilla. The
600-server-tick genuine-death respawn rule stays unchanged.

A second World attempt, if triggered, is a **separate DEV run** with
a separate execution HEAD and evidence ZIP; it does not replace or
convert the failed first report.
