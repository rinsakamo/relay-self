# S49 original owner repeated ATTACK / native disappearance — DEV contract

Stacked on #749 exact source HEAD `7dcc06e154650070e5b2b5aa4fecd383098ef7be`. Parent #742 and Unified v0.5 #717.

## Why
Existing single-shot #730 has two important gates: original
`NormalSessionActionExecutor.require_attack_authorizations` rejects any
subsequent attack (`_count!=0`) and `verify_attack_effect` requires the
same original zombie still in the native post-ACK registry. Neither can
handle multiple source-qualified strikes followed by a lethal disappearance.

## Scope in this change
- Strict default retains one ATTACK and same-target-after-probe behavior.
- Explicit DEV `max_sequential_attacks=1..32` permits only a pure ATTACK
  sequence by the **same original S49-owned ActionSupervisor**. Every
  ATTACK requires fresh two native complete probes, same target, reach,
  stationary body/target, matching distinct PROPOSE/ISSUE authorizations,
  unique new action_id, closed prior Action and no pending reconsideration.
  Mixing MOVE/EAT into this budget is not permitted.
- The opt-in `allow_target_disappearance` allows an ACK-applied ATTACK
  with a subsequent complete **0–2 native item-only entities** (or empty registry), solely as
  **ATTACK_COMMAND_APPLIED_TARGET_NOT_VISIBLE**. This is **NOT death,
  damage, kill attribution, a zombie drop, another attack authorization,
  or proof that the World killed this target**. Other entities, truncated,
  out of order, unknown/failed ACK and stale sessions all reject.
  Native absence does not grant a physical Action.
- A native `OUTCOME` here closes the attempted attack effect only.
  World-side independent managed zombie `EntityDeathEvent` and killer
  provenance must be verified *separately* before a zombie death is claimed.
- No change to original #745 600-tick World zombie respawn source,
  #749 D2 natural-drop witness, #741 WorldBody physical model or L2
  learning. No extra Action issuer. No World launched in this change.

## Next gate
1. Exact offline regression for original one-shot and explicit 2-attack
   authorization, ACK, target still present/vanished.
2. Then one uniquely granted and isolated Paper World: start managed
   zombie, source-qualify actual S49 ATTACK, compare original native command
   and separate Paper death/killer UUID without giving Self the Paper
   private World truth; retain outcome UNKNOWN if source can't be joined.
3. Follow only with real positive vanilla rotten_flesh → item UUID →
   Pickup → native inventory → S51 EAT and next epoch. No endless-loop
   claim until one World sustains >=2 independent cycles.

`DEV_ONLY / NO_NEW_REAL_WORLD / AUTONOMOUS_KILL_NOT_PROVEN /
QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.
