# Bug-0 D1: one disposable Paper item pickup World trigger — 2026-11-06

Unique one-shot **documentation-only** commit. Trigger message:
`run-bug0-pickup-d1-oneworld-once-20261106`.

Pre-World exact source HEAD `15d41889c54cbc372c36a6df8649f37c35f207d1`
passed [D1 offline CI #42056580797](https://github.com/rinsakamo/relay-self/actions/runs/42056580797)
Python readback negatives, Paper-item identity audit negatives, original source
contract, Ruff and isolated Paper 1.21.8 Java compiler. Existing #745 R1
World-owned 600 server tick respawn source is unchanged.

One disposable World only, no automatic retry. The Paper plugin is disabled
by default and only this test's explicit console operator stages one tagged
`rotten_flesh` ground item. The sole original Mineflayer session must
observe inventory before and after, and an independently source-audited
Paper `EntityPickupItemEvent` must report the same item UUID and
World/player scope.

**NOT** a Self-issued MOVE, Self-generated loot, zombie death, natural drop,
Self-initiated pickup Skill, EAT, Goal learning, or unlimited survival. Do not
claim any such result. Preserve exact original Paper/stdout/JSON/SHA artifact,
Node/Java cleanup, no extra sessions or unowned actions. Actual original
S49 Action count must be zero.

`DEV_ONLY / D1_ONE_WORLD_ONCE / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.
