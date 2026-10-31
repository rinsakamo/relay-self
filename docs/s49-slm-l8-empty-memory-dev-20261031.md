# S49 × SelfBody × L8 × M — L8 empty-memory read-only DEV shadow

Status: **SOURCE IMPLEMENTED / REAL WORLD TRIAL NOT YET VERIFIED** until
the separate exact-HEAD GitHub Actions run is read back. This design is NOT
a learning breakthrough or any change to real Action authority.

## Change

The prior one-shot real Mojang 1.21.8 DEV World at physical exact HEAD
`d53cd5a71e22b314da3f9353a51883c9a37a6d60`
established 3 original S49 L0 choices, 2 S16 OUTCOME, and 3 source-matched
post-cleanup S42 / SelfBody / L8 / M passive records. However **all L8
records had `retention_off`**, so even the empty-memory policy path was
untested with learning retention enabled.

The existing `S49SLMDevOwner` now takes
`retention_enabled: bool = False`. The S49 disposable runner
accepts the explicit `--l8-empty-memory-shadow` flag; absent it the
pre-existing OFF behavior is unchanged. The original S49
`live_probe`, L0 selection, coordinator, sole original
`NormalSessionActionExecutor`, S14/S16 and native reader remain
unchanged.

Enabled mode calls the exact existing L8 `advance_learning_epoch`
in the **post-Action/post-cleanup read-only diagnostic** with:
- new empty `PersistentCognition` for the diagnostic;
- **zero** `new_episodes`, `new_goal_labels` and
  `previous_goal_labels`;
- empty `GoalSourceAdmission`;
- actual original saved S49 probe and original S42 epoch;
- `retention_enabled=True` passed consistently to L8 and the
  original S/L8/M source-checked comparison.

It must yield `no_admissible_l1_proposal`, **not** a learned decision,
if all three original native probes are admitted and no qualified past
Goal training exists. The original S49 policy's choice still controls
the only Action issuer. The original B0 ledger remains a model-only,
non-advancing observer (no new basal/movement charge/food credits). No
per-Action Goal receipt is inferred from S16 `executed`, spatial
movement, or a zombie distance.

**IMPORTANT:** A new empty cognition instance per row is not persistent
cross-epoch learned Memory. An ON flag proves only safe admission and
abstention in the absence of qualified episodes. It does not establish
learning, next-epoch policy change, actual Minecraft physiology, Paper
P1/M0, S7 wire qualification or scientific superiority.

## Gated DEV physical test

Added branch-specific, one-shot-path-triggered workflow
`.github/workflows/s49-slm-l8-empty-memory-one-world-dev.yml`.
It can run **only** when a push explicitly modifies
`docs/s49-slm-l8-empty-memory-one-shot-trigger-20261031.md` and the
HEAD commit message exactly matches the declared one-shot grant action.
The user has granted future **this-lane real World DEV tests**. The
workflow first checks Python 3.12 focused tests, Ruff and repository
contracts; only if those PASS does it initialize exactly ONE disposable
S49 Mojang World with `--l8-empty-memory-shadow`. It stores the raw
W3 Node stdout and original S49 report as an Actions artifact even
on failure. It does not auto-retry. Any new physical attempt has a new
GitHub run/isolated root and is reported separately. This is a
GitHub-hosted Linux DEV World, not the user's local WSL2 World.

Acceptance: original `WAIT, MOVE_AWAY, MOVE_AWAY`; exactly 2 original
S16 OUTCOME, no model calls, no learned candidate, 3 `RECORDED`
source-matched rows with `l1_status=no_admissible_l1_proposal`,
0 owner errors, 0 extra native reads/Action/Habit/food credits,
successful original Node/Java cleanup and COMPLETE_NODE_STDOUT.
Actual goal attainment, per-tick motor accounting, future L1 learning
and independent QUALIFICATION/SCIENCE are NOT claimed.
