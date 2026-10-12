# RelaySelf — S Lane S8: 2 controlled epochs in one source-owned World

Owner: [Self 1.0 product #537](https://github.com/rinsakamo/relay-self/issues/537). Stack **only** on S7 Draft #605 exact frozen HEAD `d23378d0c2d8271997389f6296a9bd018e488327`. S6 physical one-shot permission is **consumed**; S7 native original bytes were only offline-qualified. Main, parent S6/S7, R5 #607, L3 #606, V1 #595, existing Golden, and shared operator RSEE are read-only. No merge, cross-lane cherry-pick, or real session in this work.

## Single product increment

This is one **bounded continuous** native S49 session, not two independent starts:

1. After a qualified native Mineflayer spawn and durable `session_started`, the external operator-side S8 controller attempts a tagged NoAI zombie summon once.
2. The sole existing S49 L0 + S16 owner independently observes/re-probes the target and may request an authorized MOVE_AWAY. No extra S8 Action issuer or L0 grant exists.
3. Only after a true original S49 executed OUTCOME was verified **and durable `action_outcome` emitted**, and S3 retained at least one original observation, a new optional `on_outcome_closed` hook stages the next condition. It attempts to remove **only** the explicitly tagged controlled zombie, then summons a fresh tagged NoAI zombie near the current bot, in the **same** World/session. These two commands are not Self Actions or Minecraft execution ACKs.
4. A second original S49 decision/Action must bind to a **different native target entity ID** and a different Action ID and retain a second S3 observation. Two positive terminal outcomes are *not* proof that memory changed decision, a goal succeeded, natural survival occurred, L1 learned, or Habit improved. The actual read-only S3 `experience_read_only_hint` event must be separately inspected for context reuse.
5. All actual Python↔Mineflayer bridge stdout and outbound intent bytes must be captured via S7's original stream recorder. These are NOT raw Minecraft TCP protocol packets, server-command ACKs, or independent R1/R2/V source envelopes.

One original Java server lifetime, one Node/Mineflayer lifetime, one World; max 2 Self Action requests, max 3 *attempted* external server commands (summon, tagged kill, summon), 12 L0 events, 500 outer frames, 180 seconds, no model/LLM POST. If a command write/drain becomes uncertain, the external trial fails closed with no retry/replay, including if the first Action was already closed. Any later distinct source outcome still goes through the original S49/ActionSupervisor pathway.

## Run modes / authority

`python -m adapters.mineflayer.self_s8_trial` is a side-effect-free dry run. The real opt-in branch requires **an independently read-back, fresh #537 user grant naming the S8 two-epoch intervention** and a **distinct** `SELF-S8-TWO-EPOCH-ORIGINAL-ONE-SESSION` confirmation, EULA already acknowledged, exact RSEE #583 source hashes, a fresh external empty output root, and preflight of the shared Python/Node/Java runtimes. A URL string alone is *not* authorization. Previous S6 #6115833076 is explicitly rejected. General “進めて” does not grant a new World run. Current classification: `S8_PHYSICAL_NOT_RUN`.

No host RSEE path, World, original S6 files, physical port, GGUF, or run budget is consumed by S8 offline implementation/CI. No user-host original source readback or qualified R1/V science evidence is claimed.

## Outcome boundaries

- **Engineering**: optional post-OUTCOME hook is reachable strictly after real S49 receipt verification and durable append-only evidence; second intervention is exactly once or explicitly uncertain.
- **Behavior**: pending real S8 same-session observation of 2 distinct native encounters, 2 separately closed Actions and original bridge lines.
- **Retained context**: the S3 `experience_read_only_hint` can be present; its historical memory references cannot act as an Action grant. There is no demonstration that a reused memory changed an L0 decision.
- **Learning/science**: S10 updates 0, S11 grants 0, external goal receipt 0, trained/held-out superiority NOT_RUN. L3 #606 and V1 #595 independent G3 NO-GO remain unchanged.

## Offline verification

```bash
export PYTHONPATH="$PWD/src:$PWD/tests:$PWD"
python -m adapters.mineflayer.self_s8_trial
python -m pytest -q tests/test_self_s8_two_epoch.py tests/test_self_s7_native_originals.py tests/test_self_s6_controlled.py tests/test_self_s3_experience.py tests/test_self_continuous_host.py tests/test_self_s1_runtime.py
python -m pytest -q
python tools/check_repository.py
```

All tests in this PR are source-shaped synthetic; no real World, S8 grant, GO, or physical Action is implied. `S8_OFFLINE_TWO_EPOCH_CONTRACT` remains the ceiling until separately authorized real source evidence is captured and independently reviewed.
