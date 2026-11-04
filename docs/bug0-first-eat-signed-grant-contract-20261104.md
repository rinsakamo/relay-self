# Bug-0 EAT — external operator principal verification, offline stage (2026-11-04)

> **READ-ONLY DESIGN/IMPLEMENTATION.** This child is stacked on [first-EAT PR #721](https://github.com/rinsakamo/relay-self/pull/721), the S49/S51 owner join [#719](https://github.com/rinsakamo/relay-self/pull/719) and Bug-0 [#717](https://github.com/rinsakamo/relay-self/issues/717). It does not authorize an EAT World or replace S49 as the sole Action issuer.

## Why an extra boundary is needed

`NormalEatingAuthorization` in `normal_action.py` checks typed fields, scopes and grant-stage separation, but a caller can construct these fields without proving a real issuing principal. The existing `handoff_authorized_first_eat` performs structural source/owner matching on synthetic tests. It **must not** be wired to a live runner on that basis.

The new `bug0_eat_grant_contract.py` is a narrow, pure **detached Ed25519 verifier** for independently signed, time-bounded operator PROPOSE and ISSUE decisions. Canonical signed statements include stage, principal, grant/nonce, existing S49 session/Intent/Action identifiers, **both original native probe sequence numbers**, current request ID, exact bread item/slot/food value, and issue/expiry UTC milliseconds. The bytes are explicitly domain-separated. S49 signs nothing; private keys are never accepted by the verifier and no static/test key is embedded in product code.

Only operator-controlled **pinned public keys** are accepted, separately for PROPOSE and ISSUE; the two stages must have different principal IDs and nonce values. The signature and relevant source fields must verify at the supplied host UTC timestamp. A verified pair produces **diagnostic metadata only** with `physical_eat_authorized=false` and no `NormalEatingAuthorization` or `ActionLifecycle` output. A caller that supplies its own trusted-key map has not independently proven the principal: pin custody is outside this module.

## Mandatory gaps before a physical EAT

1. **S owner / operator approval:** decide the actual principal, pinned public key distribution, signing custody and revocation; never place a private key in the S49 process, repository or CI. Connect a trusted receipt channel to the same existing S49 owner. Two signatures are not by themselves an owner-authenticated independent approval.
2. **Atomic one-shot admission:** bind the two signed statements to fresh original probes at **actual ISSUE**, enforce single-use of the grant and action identity across attempted restarts / processes, and guard any direct `NormalSessionActionExecutor.execute_eat` entry. This new verifier deliberately does not cache or consume grant IDs.
3. **World/source authority:** independently qualify actual native source, source freshness and physical occupancy. A two-probe stationary delta and empty bounded entity registry do not prove a safe World or global idleness. Post-MOVE S49 settling fence remains closed; first physical EAT must use a zero-prior-MOVE session.
4. **One explicitly approved disposable DEV World:** recheck native food/health/threat immediately before issue; under original S49 sole ActionSupervisor delegate one EAT to existing S51, save immutable raw command+native and S16 terminal, distinguish consume/stock/food outcomes from mere Action issue. Cleanup and independent SHA audit, no auto retry. Real World execution requires a separately approved operator grant, not this PR or GitHub CI.

## Current evidence ceiling

The offline tests generate ephemeral **fixture** keys and show one matching two-stage pair, rejection of signatures modified after signing, mismatched original scope, stale/expired time, unknown keys, same principal/nonce, and no physical issue. A replay of the same signed pair still verifies: this is intentional evidence that **a one-shot owner ledger is missing**, not an authorization result.

No new World, native Action, model call, Memory/Learning mutation, nutrition credit, physical STOP proof, independent source attestation or qualification is provided here. GitHub Actions may execute only the offline test tools. Original PR #721 remains Draft and unchanged.

`DEV_OFFLINE_SIGNED_EAT_OPERATOR_CONTRACT / SOURCE_UNATTESTED / NO_ISSUE_AUTHORITY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.
