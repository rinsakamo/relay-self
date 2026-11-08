# D14 R3 — Natural Survival World, bounded 10,000 Paper server ticks

## Motivation

The historical D4/D8/D12 one-World runner deliberately constructed a staged arena: Hunger effect 70 seconds, amplifier 20; zombie NoAI with Health 0.8/1.6; force-teleporting an enemy behind/near Self; disabling ambient mob spawning; and physical-food completion criteria. Those tests are historically valid but do NOT test what happens when Self is placed into a complex, naturally changing World.

This D14 R3 child of PR #805 leaves all historical test code and results unchanged. It introduces a separate DEV-only natural-World runner, not a variant of the staged D4 driver.

## Natural World contract

- New disposable Paper 1.21.8 World; pinned official Paper JAR and pinned zombie respawn plugin JAR, one local Mineflayer session.
- Ordinary generated terrain (minecraft:normal), survival mode, forced survival, normal difficulty. Natural mob spawning stays enabled. No Hunger effect, NoAI data changes, zombie Health injection, mob-kill or teleport command, food/inventory creation, daytime time manipulation, loot RNG tuning or success-mandatory food cycle.
- World-owned experimental rule: a maximum of one managed zombie, with a newly spawned tagged zombie only after a genuine managed-zombie death and exactly 600 Paper server ticks. No generation-number ceiling, but if a zombie never dies, it stays the same generation.
- The managed initial zombie is anchored six blocks from the player for source identification; this *management* intervention and respawn timer are explicitly not unmodified vanilla ecology. In natural mode the zombie retains AI, vanilla health and natural daylight burning (the D4 arena sun-immunity stays the default for older runs).
- Paper-owned observation at START, each 200 ticks, and LIMIT at 10,000 ticks, or EARLY_TERMINAL on genuine Self death/disconnect/World scope loss. A terminal before the limit is an observed early stop, not horizon PASS.
- Append-only derivative JSONL journals the exact original Paper lines and asynchronous correlated native readbacks. Distinguish original log and derivative; SHA256 all recorded files.
- Bounded 1200-second host watchdog. This is only an operational timeout; Paper tick or early death determines the research result.

## Execution authority: important limitation

R3 is deliberately an *observation pilot*. It does not call the historical D4/D8 Action runner and does not implement original S49 MOVE/ATTACK/PICKUP/EAT in a recurrent life loop. The Mineflayer player is physically in the World, can be attacked, hunger can change, and can die, but this code issues zero physical Actions and makes zero Gemma calls. A completed 10,000-tick World horizon is not proof of autonomous survival or Skill learning. An event-driven original S49 owner is the next separately gated development stage.

## Source and test entrypoints

- tools/bug0_d14_natural_world.py: fresh normal World startup, tick-source reader, native passive readbacks, early-death handling, safe cleanup and source hashes
- tools/bug0_d14_natural_post.py: independent paper timeline and original-versus-derivative journal audit, natural-config and no-action guards
- tests/test_d14_natural_world.py: original source/timing and negative controls, including forged World LIMIT, early death, forced Hunger/NoAI, wrong 600-tick respawn, omitted samples, fake learning
- .github/workflows/unified-v05-d14-r3-natural-world-offline.yml: exact checkout, focused tests, repository contract, Ruff and Paper plugin build

Preflight:

    python -m pytest -q tests/test_d14_natural_world.py tests/test_d14_tick_horizon.py tests/test_d12_experience_bridge.py tests/test_d12_third_intent_rearm.py
    python -m ruff check tools/bug0_d14_natural_world.py tools/bug0_d14_natural_post.py tests/test_d14_natural_world.py
    python tools/check_repository.py
    mvn -B -ntp -f adapters/mineflayer/zombie_respawn_dev/pom.xml -DskipTests package

Only a new, separately verified single-use real-World run should supply S49_REAL_SERVER_CI=1, D14_10000_TICK_WORLD_ONLY=1, D14_R3_NATURAL_WORLD_ONCE=1, an exact pinned Paper JAR, and D14_R3_RESPAWN_JAR / D14_R3_RESPAWN_SHA256. Do not mix these with old D8 Hunger/NoAI grants or copy R1/R2 world data.

Proposed runner invocation:

    python -B -m tools.bug0_d14_natural_world --report R3/report.json --server-log R3/paper_original.log --event-journal R3/d14_natural_events.jsonl

Independent post, only after the original final report exists:

    python -B -m tools.bug0_d14_natural_post --report R3/report.json --server-log R3/paper_original.log --event-journal R3/d14_natural_events.jsonl --out R3/independent_audit.json

Preserve all original R1/R2 SHA256 manifests unchanged, do not fabricate a missing report on cancellation, do not silently respawn the Self, and do not retry an unfavorable natural outcome. User's objective: observe natural life rather than force success or a counterexample.

Classification: DEV_ONLY / NATURAL_WORLD_SOURCE_IMPLEMENTED / REAL_R3_NOT_RUN / ORIGINAL_S49_CONTINUOUS_ACTION_NOT_CONNECTED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.
