# S49 forward motor admission — isolated DEV (2026-10-26)

**DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**

## Scope

A separately gated variant of the **existing original S49 single Action issuer**
may now bind an S14 `MOVE_AWAY` choice to the explicit physical action
`MOVE_FORWARD`, which S15 transports using the Mineflayer `forward` control.
The default path continues to require `MOVE_BACKWARD` / `back`.
The binding is selected **before** issuance; it is never swapped after
`ISSUED`. The original S16 consequence checks binding, dispatch, cleanup,
and observation lineage for the actual bound action.

A forward transport command is **not** equivalent to a validated escape
direction: current original S49 L0 targets zombie **distance** rather than
proving the player's facing and the World-relative escape vector.
No automatic claim of avoiding the zombie is permitted here.

- New operator gate: `S49_FORWARD_MOTOR_DEV_ONLY=1` **and**
  `qualify(..., dev_forward_motor=True)` (CLI `--dev-forward-motor`).
- Incompatible with Stage R and original additional 4th/5th/6th epochs.
- No extra reader, issuer, World writer, physical teleport, or release bypass.
- **Not yet** a DASH motor: this variant does not issue Mineflayer sprint
  input, does not prove Paper's positive forward input, and does not produce
  speed, M0, or P1 settlement evidence.
- The Paper +50% modifier remains opt-in and is not armed by this patch.
- For DEV real-world testing, observe and compare source-bound tick speed,
  on/off windows, sprint controls, directional caps and safe cleanup first.

Do not merge to main / PR #545 / PR #634, update R qualification, or
reinterpret the previously recorded backward negative control.

S16 `self_action_evidence` now retains the historical strict default
`MOVE_BACKWARD`; forward evidence must pass an explicit DEV-only flag at
capture and subsequent verification. Previous consumers are unchanged.
