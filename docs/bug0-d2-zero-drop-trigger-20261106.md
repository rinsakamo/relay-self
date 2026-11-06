# One new D2 World: natural drop or zero food, always 600tick respawn

Unique docs-only trigger commit: `run-bug0-d2-zero-drop-world-once-20261106`.

The revised runner, zero-loot branch and independent negative source audit
at exact preflight HEAD `8a13a91bd4ba24251c7de999f1929ea7b2f84a22`
passed [offline CI #42189684372](https://github.com/rinsakamo/relay-self/actions/runs/42189684372).
The first physical D2 World [#42188953900](https://github.com/rinsakamo/relay-self/actions/runs/42188953900)
remains immutable **FAILED for pickup**: original natural drop count 0;
Paper death tick36, due636, World stopped before respawn; preserved artifact
#13488448680, independent read-only audit #42189178634 SUCCESS.

Authorize precisely one *different*, disposable Paper 1.21.8 World using
original pinned Paper source and original two independent World plugins.
Do not retry the earlier World. The test's operator teleports the managed
zombie to the player and kills it once. **This is not Self S49 ATTACK**.

- If real Paper death drops 1..2 rotten_flesh, require genuine ItemSpawn,
  EntityPickup UUID/source, native inventory gain and 600 source ticks to
  a fresh real zombie and new native entity ID.
- If real Paper death drops 0, verify native inventory remains 0, do not
  stage meat or claim pickup, **still require 600 source ticks and next
  fresh zombie** before marking a source-valid zero-loot World.
- If source evidence ambiguous or required event absent, fail closed.
- No extra S49 issuer, physical Action, S51 EAT, World physics mutation,
  model invocation, learning or energy debit; cleanup + SHA originals.
- No automated rerun of this new trigger even if it fails.

`DEV_ONLY / D2_ONE_NEW_WORLD / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.
