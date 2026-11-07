# Unified v0.5 — original D5 ATTACK/EAT durable World join (DEV)

Child of [#767](https://github.com/rinsakamo/relay-self/pull/767), implementation [#768](https://github.com/rinsakamo/relay-self/pull/768). The original #765 two-parent D5+C1 code inheritance is unchanged. **Do not merge into main or transfer independent DEV results into a joint success claim.**

## What is connected

The optional `--nonmotion-fence <evidence-directory>/original_nonmotion_fence.json` path and `S49_D5_NONMOTION_FENCE_DEV_ONLY=1` gate only affect this explicitly selected D5 World. The unchanged D4 entrypoint and previous D5 R3 workflow remain unfenced unless opted in.

Before downloading/provisioning the Paper World, `tools/bug0_d4_oneworld.py` preflights a persistent sidecar **outside the disposable World root**. It restores an existing empty same-Self ledger, or creates a new one in an already-existing evidence directory. It refuses symlink ledger/lock, malformed SHA, `PREPARED_UNRESOLVED`, or **any nonempty previous World history, even if terminal**. The existing original S49 `NormalSessionActionExecutor` passes the same object through initial D4 ATTACK(s), S49/S51 EAT if and only if naturally acquired food and original L0 admissibility permit it, and D5 second Intent ATTACK after real 600tick World respawn. The journal records each distinct original native source and terminal physical effect; S49 remains the sole issuer.

This gate does **not** provide cross-run artifact ingestion into a fresh ephemeral CI runner. A new runner cannot safely infer that it has seen every ledger from earlier runners. The one-use workflow always starts a fresh, disposable World and uploads its evidence, including an unresolved ledger when the run fails. Future resumable World sessions need an explicitly durable shared store or verified external recovery handoff; sealed old-world history is not permission to reissue an Action in a new session.

## Real-World one-use discipline

`.github/workflows/unified-v05-d5-nonmotion-fenced-oneworld.yml` is restricted to a **single docs-only trigger commit** with the exact trigger subject and parent source SHA inside its trigger document. Ordinary pushes cannot launch a Minecraft World. It pins Paper, Maven plugin artifacts and Mineflayer as the D5 R3 source did, runs preworld regression, then the bounded original D4->D5 experiment, and independently invokes both `bug0_d5_post.py` (Paper/native World truth) and `bug0_d5_fence_post.py` (restored original ATTACK/EAT Action ledger). On failure no auto-retry is scheduled. The evidence folder contains the report, original Paper log, sealed or unresolved journal, independent audits if reached, and SHA256 manifest.

## Evidence boundary and status

- A source ACK for `attack_entity` never proves death or loot. Genuine Paper `EntityDeathEvent`, natural drops, passive pickup and inventory counts remain independent.
- A genuine natural zero-drop outcome means **no EAT**; it may still legitimately proceed to the second Intent. Never synthesize missing EAT evidence. The bounded scope has **one** second-Intent ATTACK, not a complete second kill/loot/EAT experience.
- ATTACK/EAT are not S10 motion learning outcomes. No new issuer, no new permissions, no forced fight/food success, no continuous survival, no physical exactly-once claim.
- Unresolved or tampered journals **STOP/UNKNOWN**; no reset/replay, no action grant from a seal, and no optimistic promotion from DEV to QUALIFICATION/SCIENCE.

`DEV_ONLY / JOINT_WORLD_NOT_RUN_UNTIL_ONEUSE_TRIGGER / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.
