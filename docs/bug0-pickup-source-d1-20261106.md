# Bug-0 D1 — Read-only native rotten_flesh gain + independent Paper fixture

## Why this stage
#745 verified an *operator-caused* managed zombie death and World-owned 600
server tick respawn in one Paper World, not autonomous hunting. #742 needs an
unambiguous item pickup evidence boundary before allowing composite hunting.

## Design
- Preserve original #745 respawn logic/600tick source; no change to original
S49 issuer, S14/S15/S16, #741 fixed WorldBody or P1 model.
- Native read-only `read_rotten_flesh_gain` requires correlated live
Mineflayer pre/post inventory, same session, increasing seq, health>0,
and **exactly one** extra `rotten_flesh`. The readout is explicitly labelled
NATIVE_INVENTORY_DELTA_ONLY, not causal proof of a zombie drop.
- Independent DEV Paper plugin defaults disabled and grants **only console
operator** permission to stage exactly one real, tagged ground item adjacent
to the already-present player. No permission exposed to the Self, no
general World item spawn API, no implicit resource credit.
- Independent Paper `EntityPickupItemEvent` gives the World-side pickup
source; compare the same tagged item UUID, player UUID, World UUID, item
material and spawn/take ticks. Both native inventory gain and authoritative
Paper evidence are needed for D1.
- This initial D1 experiment is **operator-staged item**, not a dropped
item from a Self-killed zombie, not a Self-directed MOVE, and not one
complete hunting cycle. D2 must establish natural drop provenance and actual
S49-controlled approach before declaring autonomous pickup.

## Gates
D1 offline: source negatives and plugin compilation.
D1 real Paper: one new disposable World, one original native session,
operator-only staged item, real pickup event and native inventory gain,
original SHA sources, cleanup, no retries.
No new Action/LLM/learning or formal R/V qualification.

DEV_ONLY / D1_PENDING_PHYSICAL_SOURCE / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.
