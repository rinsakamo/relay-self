# RelaySelf S30 — actual Node bridge process qualification with test-only Mineflayer substitution

## Frozen authorities
- S29 Draft PR #365, exact base `5424669a09a69eb364da559e38b9999fee7b6680`.
- Frozen S18–S29 artifacts, RelayTheory R6, Paper2 MAIN40 must remain unchanged.
- S29 correlated observe request ID wire implementation is reused **without editing production bridge or protocol**.

## Qualification target
`CORRELATED_REAL_NODE_BRIDGE_PROCESS_TEST_SHIM_QUALIFIED` means:
- actual Node 22 child process executing frozen `adapters/mineflayer/bridge.mjs`
- actual Python `MineflayerProcessSession.launch/send_observe/receive/shutdown` with OS pipes and strict native JSONL decoder
- controlled test-only `mineflayer` module substitution installed via Node `--require` preload in the **test child process** only.

This explicitly does **not** mean actual Minecraft server, real Mineflayer implementation, genuine bot/world state, hardware attestation, or independent physical source authenticity.

## Test-only isolation
`adapters/mineflayer/s30_test_only_preload.cjs` hooks Node's CommonJS module loader to replace only exact imports `mineflayer` and `mineflayer/package.json`. This fake bot supplies deterministic:
- bot position (0,64,0), zombie entity ID 42 0.20m or 1.80m away
- health/food/oxygen/time/inventory needed by **real bridge snapshot serializer**
- `inject_allowed` + `spawn` + health event to exercise existing health-synchronized bootstrap
- deterministic `quit -> end`, no Minecraft socket.

The test fixture explicitly sets `NODE_OPTIONS=--require=<absolute fixture path>` via monkeypatch for child launch. Node's actual `bridge.mjs` remains unchanged. No production injection option is added. The mock is active only in test processes and its replacement of real Mineflayer is prominently recorded.

## Acceptance: actual-process assertions
- `adapter_started` seq0 and `spawn` observation seq1 via actual child stdout
- request1 `s30-probe:one.1` produces correlated probe seq2 with exactly matching request ID and entity #42
- request2 `s30-probe:two.2` yields independent correlated probe seq3, no cross-ID attribution
- legacy `send_observe()` emits untagged probe seq4 (S29 legacy compatibility)
- duplicate request1 in same session yields `command_error=duplicate_probe_request_id` and **no extra probe**
- 1.80m alternate mock output yields matching 3D position and distance
- deliberately malformed JSON, invalid or null ID are rejected by actual Node command parser; a later valid request still works
- before simulated `spawn`, probe returns `observe_before_spawn` rather than invented World data
- clean shutdown produces ack and connection_end, followed by EOF; force termination refuses subsequent reads/sends without implicit relaunch
- fresh Node process creates separate UUID and fresh in-memory request ID set.

## Fail-closed / strict distinctions
The Node bridge process and operating system pipes are real. The Mineflayer import, bot and entity registry are **mocked**, not physically derived. A package-version stub is supplied and no real Mineflayer API or Minecraft TCP server is exercised. The real bridge protocol is thus tested for transport, serialization, session/seq, correlation, duplicate ID, termination and error handling, not live World correctness.

S29 already provided protocol-level request ID matching. S30 adds OS process, pipe, event-loop, bridge handling and shutdown evidence under an explicit test double. It does not establish:
- globally unique IDs across process restarts
- request-response cryptographic signatures or real-world causality
- authentic Minecraft state; source-native content may be fabricated by test shim/compromised bridge
- independent authenticated physical clock; live latency or connectivity
- automatic scheduler/reentry, new Action issuance, Skill completion or learning.

## Files
`adapters/mineflayer/s30_test_only_preload.cjs`
`tests/test_postmain_real_node_bridge.py`
`docs/postmain-s30-receipt.json`
`docs/postmain-s30-process-trace.json`
`docs/postmain-s30-qualification-ja.md`
`.github/workflows/postmain-capability-s30.yml`

## Gate
Accept only if exact final HEAD has successful repo contracts, Ruff, all pytest and Mineflayer adapter Node checks. Dedicated pytest job sets up Node 22 for actual child-process tests. Keep PR Draft/unmerged.

S31 candidate: run the **unmodified Mineflayer implementation** against an explicitly provisioned temporary local Minecraft test server, preserving separation from sensor truth or autonomous Self qualification. Alternative: process-bound request ledger restart/replay transaction with independently frozen test identity.
