# RelaySelf L-Zombie / Z1 Paper server tick witness — DEV runbook

2026-11-02. Parent Draft PR #692 and Issue #693. GitHub-only work: NO real Paper World, actual zombie, client observation, or real Gemma in this turn. Preserve #689 real-World A PASS_DEV / B1-U limited PASS_DEV, and all previous original/failure SHAs.

## Source rationale

Original S49 kills and respawns zombies across stages, so consecutive stage observations are different entities. Mineflayer nearby-entity registry has position, integer entity ID and client seq, but not a Paper-exact tick and independently verified UUID/spawn-generation in the same observation. Native seq and client update-time packet are not equivalent to exact server ticks. Z1 starts with Paper-only original tick source, not live cognition.

## Independent Java21/Paper1.21.8 plugin

Source: adapters/mineflayer/l_zombie_paper_dev, independent of M02, S49, L0 and all other lanes. Maven invocation:

    mvn -B -ntp -f adapters/mineflayer/l_zombie_paper_dev/pom.xml -DskipTests package

JAR: relay-l-zombie-paper-dev-0.1.0-dev.jar

Config copied to a NEW disposable Paper World plugins folder; defaults OFF. Explicitly set both dev-enabled: true and zombie-tick-readonly-dev: true, version 1.21.8. The plugin never summons, despawns, damages, teleports, moves or changes player/zombie physics.

Once one real zombie exists and only one is loaded, execute the console-only Paper command:

    relayzombietrack start z1-original-1 s1-zombie

It logs one L_ZOMBIE_ARM_V1, 31 consecutive main-thread Paper tick rows L_ZOMBIE_TICK_V1 at offsets 0...30, and L_ZOMBIE_END_V1. Offset 10 is the future prediction-reference point, offset 30 is exactly 20 server ticks later; the plugin does NOT actually issue a forecast. All rows carry UUID/World UUID/entity ID/positions and observational spawn_instance=1 (this is an observational generation token, NOT a lifetime-global spawn serial). Entity removal, invalid position, tick skips, operator stop or plugin shutdown produce non-PASS end, not silent respawn/retry. The process writes through the original Paper console logger; no custom file writes.

## Next operator-local real test — separate consent/budget and physical checks

1. Confirm grant for a NEW independent disposable Paper World, at most one and zero automatic retries, with source-only readback. Fix exact clean branch HEAD, real Java21/Paper1.21.8 server/plugin JAR SHAs, localhost-only bind, new clean unique evidence and World roots, process/cwd/PID custody and teardown checks before launch. Never modify old #689/#679/#684 results.
2. Stage the plugin and its DEV flags in the new Paper server; disable uncontrolled mob spawning. Build a safe isolated Arena first. Stage precisely one zombie under operator control and DO NOT kill or replace it between the source ticks. Choose a safe player enclosure/creative observer. NoAI disabled is necessary to measure actual pursuit behavior; if the zombie does not chase, source can still be measured but a positive AI pursuit claim is invalid. Retain existing L0 safety if a Self actor is present.
3. Invoke the Paper console-only arm once; preserve the complete unedited Paper stdout raw bytes and externally calculate the exact SHA256. If zero/multiple zombies, invalid movement, lost/removed target or any incomplete window: preserve original FAIL, no retry. Native Mineflayer observation if taken must be separately source-qualified; no client tick alignment is inferred.
4. Independently read back the original Paper log, only after the process has stopped or the raw complete-line capture is fixed:

    python -m tools.l_zombie_paper_original_audit --paper-original "$PAPER_RAW" --expected-sha256 "$PAPER_SHA" --marker z1-original-1 --session s1-zombie --report "$NEW_READBACK_JSON"

The auditor refuses stale/symlink/partial source SHA, extra/duplicate/missing tick rows, noncontiguous ticks, changed entity and incomplete END. It produces a fresh create-only report; never edits original raw log. This is PAPER-SOURCE-SHAPE_ONLY, not real process authenticity or native-client observation evidence. Independently verify actual owned Java PID/JAR/world, cleanup, deleted World and released ports.
5. Preserve negative and success originals with exact SHA index, branch/HEAD and runtime identity, report to #693 and PR #692 in Japanese. Remain DEV_ONLY, QUALIFICATION_NO_GO, SCIENCE_NOT_RUN.

## Boundaries of what Z1 can prove

Paper-only continuous UUID/tick/position observation can establish a *bounded source* when actual process provenance is independently authenticated, not lifetime, AI pursuit, causal model learning or B1.

The Z0 pure 20-tick scorer expects native-seq source and client identity; it cannot be fed solely Paper rows and then called a real Mineflayer observation. A future Z1 client join must source-qualify native probe time/entity before use. Z2 separately requires actual Gemma4 strict schema/Reasoning OFF with genuine GGUF mapping and fresh HTTP preflight, one pre-outcome frozen L2 point or abstention, and a +20-tick independent physical outcome. No model is allowed to see target data early. Separate B1-N/U/Q, B2, C, holdout and source provenance.

Current classification: Z1_PAPER_SOURCE_IMPLEMENTED_OFFLINE_ONLY / REAL_WORLD_0 / REAL_GEMMA_0 / PAPER_CLIENT_JOIN_UNATTESTED / NO_ACTION_OR_LEARNING / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.
