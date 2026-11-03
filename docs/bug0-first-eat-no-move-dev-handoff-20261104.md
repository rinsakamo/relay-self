# Bug-0 first EAT without prior MOVE — S49 owner/S51 runner DEV handoff (2026-11-04)

> **Code available; no new World or native food Action executed in this development turn.** Child of [Bug-0 EAT owner PR #719](https://github.com/rinsakamo/relay-self/pull/719), original S49 [#674](https://github.com/rinsakamo/relay-self/pull/674), S51 existing runner (same source tree). This is a **nonissuing first-EAT native source shadow**, not a qualification, external Action grant or automatic world session.

## Grand-null decision — reuse S49 + S51

The existing S51 real-survival runner **already** provisions an isolated Mojang 1.21.8 World, gives operator-staged bread to survival-mode Self, induces an actual hunger condition, observes original Mineflayer snapshots, and knows how to issue one existing eat Skill/Action followed by `equip_item`, `consume_held`, and an exact native food/inventory after-probe.

The existing S49 owner has `NormalSessionActionExecutor`, one original `IntentCommitment` + `ActionSupervisor`, `require_eating_authorizations`, and an explicit post-MOVE settling fence. Bug-0 [S50 #720](https://github.com/rinsakamo/relay-self/pull/720) established that input OFF alone cannot attest complete STOP after a MOVE.

**Therefore the first food test should start before any MOVE**, rather than waiting for general server-effective clear qualification. The next step is an original source readback using **the same S51 World staging** plus a fresh S49 *owner representation*, not a new issuer, launcher, inventory action, learned skill or second Mineflayer connection.

## New opt-in implementation

- [`bug0_first_eat_shadow.py`](../adapters/mineflayer/bug0_first_eat_shadow.py) accepts the existing S49 owner's **fresh, unissued** state and two distinct original native `probe`s. It requires a matching session, monotonically advancing native sequence (bounded difference), different request IDs, zero observed nearby entities / complete bounded registry, viable body, <=0.05m **sampled** position change, actual food/hunger eligibility from **existing** `EatCursor`, and unchanged candidate item-slot inventory counts.
- It returns only a frozen **diagnostic**: source ids, food candidate, risk statuses, sampled displacement and **explicit false** physical authorization, independently authenticated grant, complete idle World ticks, R source and EAT-issued fields. This object is **not passed to `ActionSupervisor.issue`**, has no signature/authority and cannot unlock the S49 post-MOVE fence.
- The existing [S51 runner](../adapters/mineflayer/s51_eat_real_ci.py) adds default-off `--bug0-first-eat-shadow`, restricted to **bread / inventory / single initial food opportunity**. If explicitly enabled for a disposable DEV World, it reuses S51's existing staging and immutable native/command capture, obtains the **second** original native observation, constructs one fresh **unissued** S49 owner, calls the diagnostic, then exits through the **original S51 shutdown and report path**. It never enters the existing S51 `ActionLifecycle.propose/authorize/issue` block for this mode, nor calls `equip_item` / `consume_held`.
- Explicit pre-World gates are both `S51_REAL_SERVER_CI=1` **and** `S51_BUG0_FIRST_EAT_SHADOW_DEV_ONLY=1`, plus `--bug0-first-eat-shadow`. Missing gates block before Java. The flags are **not** a physical EAT grant or independent principal proof.
- Operator `/give` and `/effect hunger` are Minecraft **test staging effects** in this opt-in World, **not** Self-issued EAT Actions. The pre-food loop may advance the existing experimental M0 WAIT ledger; **no food-energy credit** occurs. A DEV shadow run is not an all-readonly World.

## Offline tests and evidence

- New tests: synthetic first food source candidate and no-Action assertions; stale/foreign probes, same request, too-old seq, physical displacement, nearby threat, truncated coverage, missing/changing food, wrong hunger, expired owner, pending reconsideration, wrong observation type, invalid DEV mode, and missing DEV gate. Tests do not start Java, Node or a Minecraft server.
- Exact-head offline CI is [here](https://github.com/rinsakamo/relay-self/actions/workflows/bug0-first-eat-shadow-offline.yml), running original S49/S51/S46 regressions alongside the new tests. The final source SHA and pass/fail outcome must be read from the completed exact-head run; a previous HEAD's green build is not current qualification.
- The S51 runner's **default path is unchanged** if `--bug0-first-eat-shadow` is absent; no existing historical qualification or source is overwritten.

## Owner-operated new DEV World (not yet executed)

A future approved *single* disposable DEV shadow may use the existing S51 preflight and runtime only after S-owner resource/grant approval, pinned sources and fresh output paths. Suggested invocation template (not executed here):

```sh
PYTHONPATH=src:tests:. \
S51_REAL_SERVER_CI=1 \
S51_BUG0_FIRST_EAT_SHADOW_DEV_ONLY=1 \
python -m adapters.mineflayer.s51_eat_real_ci \
  --bug0-first-eat-shadow \
  --food-item bread --food-source inventory \
  --report /path/to/new/b0-first-eat-shadow-report.json \
  --server-log /path/to/new/b0-first-eat-shadow-paper.log
```

Preconditions: exact code and official World server pin, Java 21/Node 22/Mineflayer 1.21.8, original S51 sole owned process; reserved immutable native/command stream paths; available unused loopback port; no live other World; one bounded session and no retry. Preserve all failures. On exit, independently verify original after source, no `equip_item` / `consume_held` commands, `actual_native_actions=[]`, no native Action ISSUED, Node/Java termination and cleanup, server config/world hashes, original source receipt, and report SHA.

**No first-EAT physical Action should be issued based only on the DEV shadow.** A following separately reviewed physical DEV attempt still needs genuinely authorized EAT PROPOSE/ISSUE from the S49 single issuer at issuance time, fresh threat/food/body source, and S51 original consumption/stock evidence. If MOVE was ever issued in that owner's session, S49's settling fence remains closed until correctly qualified.

## Strict current classification

`DEV_OFFLINE_FIRST_EAT_SHADOW_CODE / SOURCE_UNATTESTED / EAT_ACTION_NOT_RUN / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.

In this transaction: **World 0 / Node 0 / Paper 0 / native Self Action 0 / food credit 0 / learning 0**. Future physical staging, WAIT basal charges, grant handling and genuine World evidence must be reported as *new evidence*, not silently inherited.
