# M0.2 V7 S50 tick-chord BASE_ON — independent engineering qualification

Date: 2026-10-16 (JST). Authority R #575, S #537 and user-approved one-time
new-JAR QUALIFICATION. **Qualified scope: BASE_ON with the exact new plugin
and tick-chord config only.** This is not V SCIENCE, not production, and not
a reclassification of any historical DEV attempt or earlier consumed grant.

## Terminal R verdict

`R_M02_V7_NEW_BASE_ON_TICK_CHORD_ENGINEERING_QUALIFIED_ONLY`

Independent **read-only** R rereview run:
[GitHub Actions #38908742143](https://github.com/rinsakamo/relay-self/actions/runs/38908742143)
**SUCCESS**. The original bytes and R verdict are saved as a fresh 90-day
[artifact #12049670505](https://github.com/rinsakamo/relay-self/actions/runs/38908742143/artifacts/12049670505).
Artifact archive digest:
`sha256:64be2a990e65e3ebd9beff5db688606158dc6afd8570f6c4529b8ef739302994`.
This rereview **did not launch Java, Node or a new World**.

### The one consumed physical run

[One real Paper qualification #38907469772](https://github.com/rinsakamo/relay-self/actions/runs/38907469772),
workflow attempt 1, source S workflow HEAD
`6931d57c1037c47ebd89295bdc3cd4f237f64d09`. Its source checkout was
**separately** pinned to S source HEAD
`d34c1cc613920a2485a581c25a8010f2a47e1bd6`,
and its original independent R source checkout to R HEAD
`53193a5da376e2832555231df4ada15f063f3b67`.
The initial physical run had a failed *R verdict job*, so GitHub correctly
records overall workflow FAILURE despite the S physical producer exit **0**.
Do not rewrite that overall run conclusion as SUCCESS.

One-shot grant:
`USER_M02_V7_TICK_CHORD_BASE_ON_20261016_ONCE`;
**consumed=True**, Java starts 1, native Node sessions 1,
retry_count=0, fresh producer run ID
`81a372a825004ff93797b230df2a5c08`,
native session ID
`dd437825-0ef2-4b29-9065-8de1085f1919`.
All host cleanup was independently witnessed by the original
same-host GitHub step: Java PID 2737 absent, Node PID 2830 absent,
loopback 127.0.0.1:25565 free, Java and Node exit0, native STOP ACK and
connection_end, owned isolated World cleaned. The S producer receipt remained
`qual_engineering=false` (only R decides).

Immutable original physical archive:
[artifact #12048564191](https://github.com/rinsakamo/relay-self/actions/runs/38907469772/artifacts/12048564191),
`sha256:6dd93e90dea3dfa40a5d7c02ddac82ad5a3485a8476f7ef912db164fb66ea847`.

### Exact qualified assets

| Source | SHA256 |
|---|---|
| Official Paper 1.21.8 build60 | `8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e` |
| New Paper M0.2 tick-chord plugin JAR | `a43afa4d0a1fdaf01c633efd2543ed24b6b53b12ee38ed62a33594057e701e8f` |
| BASE_ON with `s50-tick-meter-dev: true` | `939c2da60ed4ce2f5afb5609c1f784886e3b021104c28a83658c17b744159b16` |
| Input `server.properties` | `11aaf903bae3d92f3b667f464f301a513bee559f04acc33d722c7a2e966d03ae` |

S50 governed MOVE issued/outcome, S51 native steak EAT issued/outcome,
3 native S50 look/forward/clear ACKs and 2 S51 equip/consume ACKs
are checked against the original Action journal, commands and native
sequence. Target World NBT seed is 61021. Requested BASAL direct write for
first 200 player callbacks=0.2 exhaustion; tick-chord observed horizontal
sum=1.9389928412050272 blocks; direct native WALK setter input
=0.019389928412050277 exhaustion. The source review inspected 500 tick
writer records and separate per-event MOVE observations remained
zero-billed, not double billed. No continuous sub-tick motion inference.

The independent R original manifest pin includes e.g.:
`paper_server.log` SHA
`2aa9d9a74637dbbd8c3ef171048fd1dbbdbfe55059c5d4312e0052fe488d5bfe`;
`original_native.jsonl` SHA
`f1d1c81b78a6167b5661456b4cfde2cb067cdf7fc531853dbb88f94755ac9186`;
`owner_commands.jsonl` SHA
`0e7eddb5b924fcc7c6675004a617ee638c7a3014a634e55d8781b6fab7159337`;
`qualification_producer.json` SHA
`2509cc27ad625ac32b3b703dc3c311166432d16e2644667eb45971f54aa1e1cf`.
All indexed sources were rehashed before and after R review. The genuine
S original ZIP archive was independently downloaded and its GitHub artifact
ID/provider SHA pinned.

## No physical retry: three distinct audit outcomes

1. Source physical run #38907469772: S producer completed and the
   independent R reviewer originally failed because an overly generic
   20 MiB source cap rejected the **52,811,717-byte legitimate Paper JAR**.
   Original physical evidence retained; physical grant consumed.
2. First offline rereview #38908344582: after correcting the Paper JAR
   cap, R reviewer rejected the five true motor+EAT native effects because
   it had incorrectly applied the **three-effect S50-only** constraint.
3. Offline diagnostic #38908548732 independently inspected the frozen
   `owner_commands.jsonl`: exactly **3 S50** effects
   (look, set_control, clear_controls) plus **2 S51 EAT** effects
   (equip_item, consume_held).
4. Final offline rereview #38908742143: R reviewer now validates **all five**
   effects and their native ACKs, all source bytes, native World,
   single consumed grant and process witnesses; terminal independent
   **ENGINEERING QUALIFICATION PASS**.

All secondary steps were *read-only R original rereviews*. Neither a new
physical session nor a second qualification authorization was performed.
Preserve the failed R verdicts in audit history rather than deleting or
calling those failures PASS.

## Scope boundaries

- **Qualified:** only the specific M0.2 new JAR + `BASE_ON` tick-chord
  config, S50 native write-side WALK accounting and first200 BASAL
  direct source-write accounting, genuine S50 MOVE + S51 EAT, native
  STOP and independently witnessed host cleanup.
- **Not qualified:** SHAM_ON, BASAL_ZERO, WALK_ZERO, BOTH_ZERO profiles;
  alternative JAR/config HEADs; continuous movement within one World tick;
  fully isolated downstream food/saturation debits; survival/endurance
  benefit; learning/cognitive adaptation; V8 ecological comparisons.
- **No authorization:** no more physical use of this grant, no promotion of
  old DEV science evidence, no V7 prereg alteration, no V SCIENCE launch.
  Frozen V7 science=0/20 and V6 science=0/48; G3/production remains NO_GO.

R owner source auditor:
`experiments/standard_env/m02_v7_tick_qualification_audit.py`.
R replay workflow:
`.github/workflows/rsee-m02-v7-new-base-qualification-original-replay.yml`.
S owner producer:
`adapters/mineflayer/m02_paper_dev/s51_paper_v7_new_qualification.py`.
