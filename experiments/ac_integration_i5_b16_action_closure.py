"""I5: B16 quorum S11 choice -> actual B11 simulator Action -> terminal receipt.

This is an OFFLINE, same-process test-world behavioral closure. Existing native S10
owner commits and B16 separate forgeable TEST Habit grants are reused unchanged.
A B11 simulator receipt is NOT an S15/S16 Mineflayer WorldConsequence, S17
feedback, durable Habit acquisition, authenticated native source or production GO.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from experiments.ac_b_b11_governed_habit import (
    CONTEXTS,
    CurrentWorld,
    ObservedOutcome,
    cue_for,
    empty_repertoire,
)
from experiments.ac_b_b16_quorum import (
    MIN_VOTES,
    N_TRIALS,
    BatchLedger,
    PairedTrial,
    commit_test_quorum_habit,
    initial_state,
    issue_observed_trial,
    issue_test_authority,
    native_s10_commit,
    propose_quorum_habit,
)
from relay_self.habit import (
    HabitRepertoire,
    HabitSelectionStatus,
    select_habit,
)
from relay_self.learning import LearningUpdateAuthority
from relay_self.provenance import Provenance

MANIFEST = Path(__file__).with_name("ac_integration_i5_manifest.json")
FROZEN_SHA256 = "5a239655a11b242504a28b951be861181d70f1eaa4018cc7a84cc713e5ed327c"
ARMS = ("ONE_SHOT", "S11_QUORUM", "CHEAP_COUNT")
EARLY, LATE = "EARLY", "LATE"


class I5Rejected(ValueError):
    """Unqualified offline World source, model decision or evaluation permission."""


@dataclass(frozen=True, slots=True)
class LocalTrialPermit:
    """Explicit bounded caller-local permission: no production issuer/security."""
    trial_id: str
    arm: str
    checkpoint: str
    session: str
    source_revision: int
    source_world_id: int
    a: int
    b: int
    owner_id: str
    owner_revision: int
    selected_action: int | None
    granted: bool


@dataclass(frozen=True, slots=True)
class TrialClosure:
    trial_id: str
    arm: str
    checkpoint: str
    a: int
    b: int
    owner_revision: int
    selected_action: int | None
    source_event: ObservedOutcome | None
    terminal: str
    success: bool
    release_to_learning: bool = False
    s15_action_issued: bool = False
    native_world_attested: bool = False
    production_go: bool = False


def _unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise I5Rejected("duplicate frozen manifest key")
        result[key] = value
    return result


def frozen_manifest() -> dict[str, object]:
    try:
        obj = json.loads(
            MANIFEST.read_text(encoding="utf-8"), object_pairs_hook=_unique,
            parse_constant=lambda _: (_ for _ in ()).throw(
                I5Rejected("nonfinite frozen JSON")
            ),
        )
        packed = json.dumps(
            obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (OSError, TypeError, ValueError) as exc:
        raise I5Rejected("frozen manifest not readable") from exc
    if hashlib.sha256(packed).hexdigest() != FROZEN_SHA256:
        raise I5Rejected("prospective I5 manifest digest mismatch")
    return obj


def _policy_choice(
    world: CurrentWorld, ledger: BatchLedger, owner: HabitRepertoire,
    arm: str, checkpoint: str,
) -> int | None:
    if (
        not isinstance(world, CurrentWorld)
        or not isinstance(ledger, BatchLedger)
        or ledger.world is not world
        or not isinstance(owner, HabitRepertoire)
        or (ledger.a, ledger.b) not in CONTEXTS
    ):
        raise I5Rejected("genuine source-owned B16 ledger and S11 owner required")
    ledger.assert_current()
    if checkpoint == EARLY and arm == "ONE_SHOT":
        if len(ledger.trials) != 1:
            raise I5Rejected("ONE_SHOT requires exactly one actually observed pair")
        return ledger.first_shot()
    if checkpoint != LATE or arm not in ("S11_QUORUM", "CHEAP_COUNT"):
        raise I5Rejected("trial/arm not admitted at frozen checkpoint")
    if len(ledger.trials) != N_TRIALS:
        raise I5Rejected("quorum lacks five genuinely issued two-action trials")
    if arm == "CHEAP_COUNT":
        return ledger.counted_quorum()
    picked = select_habit(
        owner, cue_for(ledger.a, ledger.b, trial="i5-actual-evaluation"),
    )
    if picked.status is HabitSelectionStatus.NO_MATCH:
        return None
    if picked.status is not HabitSelectionStatus.SELECTED:
        raise I5Rejected("ambiguous S11 selection cannot cause Action")
    if picked.selected_candidate_ref not in ("action:0", "action:1"):
        raise I5Rejected("S11 selected a nonbinary or unauthorized Action")
    return int(picked.selected_candidate_ref[-1])


def mint_test_permit(
    world: CurrentWorld, ledger: BatchLedger, owner: HabitRepertoire,
    *, arm: str, checkpoint: str,
) -> LocalTrialPermit:
    selected = _policy_choice(world, ledger, owner, arm, checkpoint)
    trial_id = f"i5:{world.session}:{checkpoint}:{arm}:{ledger.a}:{ledger.b}"
    return LocalTrialPermit(
        trial_id=trial_id, arm=arm, checkpoint=checkpoint,
        session=world.session, source_revision=world.revision,
        source_world_id=id(world), a=ledger.a, b=ledger.b,
        owner_id=owner.repertoire_id, owner_revision=owner.revision,
        selected_action=selected, granted=True,
    )


def execute_scoped_test_action(
    world: CurrentWorld, ledger: BatchLedger, owner: HabitRepertoire,
    permit: LocalTrialPermit | None, consumed: set[str],
) -> TrialClosure:
    """Issue exactly one source-registered test World act; no ActionSupervisor."""
    if (
        not isinstance(world, CurrentWorld)
        or not isinstance(ledger, BatchLedger)
        or not isinstance(owner, HabitRepertoire)
        or not isinstance(permit, LocalTrialPermit)
        or type(consumed) is not set
        or any(type(x) is not str for x in consumed)
        or permit.granted is not True
        or type(permit.trial_id) is not str
        or permit.trial_id in consumed
        or permit.arm not in ARMS
        or permit.checkpoint not in (EARLY, LATE)
        or any(type(v) is not int for v in (
            permit.source_revision, permit.source_world_id, permit.a, permit.b,
            permit.owner_revision,
        ))
        or ledger.world is not world
        or permit.source_world_id != id(world)
        or permit.session != world.session
        or permit.source_revision != world.revision
        or (permit.a, permit.b) != (ledger.a, ledger.b)
        or permit.owner_id != owner.repertoire_id
        or permit.owner_revision != owner.revision
        or permit.trial_id
        != f"i5:{world.session}:{permit.checkpoint}:{permit.arm}:{ledger.a}:{ledger.b}"
    ):
        raise I5Rejected("unqualified or replayed test-only source/owner permission")
    exact = _policy_choice(world, ledger, owner, permit.arm, permit.checkpoint)
    if type(permit.selected_action) is not type(exact) or permit.selected_action != exact:
        raise I5Rejected("test permit not aligned with actual S11/cheap current choice")
    consumed.add(permit.trial_id)
    if exact is None:
        return TrialClosure(
            trial_id=permit.trial_id, arm=permit.arm, checkpoint=permit.checkpoint,
            a=ledger.a, b=ledger.b, owner_revision=owner.revision,
            selected_action=None, source_event=None,
            terminal="ABSTAIN_NO_SOURCE_ACTION", success=False,
        )
    before = world.actions_executed
    observed = world.act(ledger.a, ledger.b, exact)
    if (
        not isinstance(observed, ObservedOutcome)
        or not world.observed(observed)
        or observed.session != permit.session
        or observed.revision != permit.source_revision
        or (observed.a, observed.b, observed.action) != (ledger.a, ledger.b, exact)
        or observed.kind != "OBSERVED_ACTION"
        or type(observed.success) is not bool
        or world.actions_executed != before + 1
    ):
        raise I5Rejected("unobserved or forged source-issued terminal Action")
    return TrialClosure(
        trial_id=permit.trial_id, arm=permit.arm, checkpoint=permit.checkpoint,
        a=ledger.a, b=ledger.b, owner_revision=owner.revision,
        selected_action=exact, source_event=observed,
        terminal="SIMULATOR_SOURCE_ACTION_TERMINAL", success=observed.success,
    )


def run_i5_episode(*, noisy: bool) -> dict[str, object]:
    world = CurrentWorld(session="b16-offline-noisy" if noisy else "b16-offline-clean")
    owner = empty_repertoire(label=f"i5-owner-{'noisy' if noisy else 'clean'}")
    original_owner = owner
    batches: dict[tuple[int, int], list[PairedTrial]] = {
        key: [] for key in CONTEXTS
    }
    closures: list[TrialClosure] = []
    spent: set[str] = set()
    native_s10_count = 0
    s11_grants = 0
    training_count = 0

    for trial_idx in range(N_TRIALS):
        for a, b in CONTEXTS:
            pair = issue_observed_trial(world, a, b, trial_idx, noisy=noisy)
            batches[a, b].append(pair)
            training_count += 2
        if trial_idx == 0:
            if training_count != 8:
                raise I5Rejected("wrong early training checkpoint")
            for a, b in CONTEXTS:
                ledger = BatchLedger(world, a, b, tuple(batches[a, b]))
                permit = mint_test_permit(
                    world, ledger, owner, arm="ONE_SHOT", checkpoint=EARLY,
                )
                closures.append(
                    execute_scoped_test_action(world, ledger, owner, permit, spent)
                )
            # Source-owned evaluation receipts exist in world._issued, but NEVER
            # in the explicitly enumerated B16 source training tuples.
            if any(len(v) != 1 for v in batches.values()):
                raise I5Rejected("evaluation Action entered training samples")
    if training_count != 40:
        raise I5Rejected("insufficient fixed B16 executed training Actions")
    cheap: dict[tuple[int, int], int] = {}
    ledgers = {
        (a, b): BatchLedger(world, a, b, tuple(batches[a, b]))
        for a, b in CONTEXTS
    }
    for a, b in CONTEXTS:
        ledger = ledgers[a, b]
        if ledger.counted_quorum() is None:
            continue
        cheap[a, b] = ledger.counted_quorum()
        state = initial_state(ledger)
        auth = LearningUpdateAuthority(
            authority_id=f"i5-B16-native-S10:{a}:{b}",
            target_id=state.target_id,
            granted=True,
            provenance=Provenance("i5-explicit-s10-test-grant", ledger.digest),
        )
        actual = native_s10_commit(ledger, auth)
        native_s10_count += 1
        draft = propose_quorum_habit(ledger, owner, actual)
        owner = commit_test_quorum_habit(
            ledger, owner, actual, draft, issue_test_authority(draft),
        )
        s11_grants += 1

    for a, b in CONTEXTS:
        ledger = ledgers[a, b]
        for arm in ("S11_QUORUM", "CHEAP_COUNT"):
            permit = mint_test_permit(world, ledger, owner, arm=arm, checkpoint=LATE)
            closures.append(
                execute_scoped_test_action(world, ledger, owner, permit, spent)
            )
    # Never let postselection evaluation receipts enter source-limited training.
    source_training_ids = {
        item.event_id for trials in batches.values()
        for pair in trials for item in (pair.action0, pair.action1)
    }
    eval_ids = {
        result.source_event.event_id for result in closures
        if result.source_event is not None
    }
    if (
        len(source_training_ids) != 40
        or len(eval_ids) != len([
            result for result in closures if result.source_event is not None
        ])
        or source_training_ids & eval_ids
        or any(not world.observed(result.source_event) for result in closures
               if result.source_event is not None)
        or any(ledger.counted_quorum() != cheap.get(key)
               for key, ledger in ledgers.items())
        or original_owner.rules
        or world.actions_executed != training_count + len(eval_ids)
    ):
        raise I5Rejected("source leakage, edited B16 samples or owner mutation")
    counts = {
        arm: (
            sum(x.arm == arm and x.source_event is not None for x in closures),
            sum(x.arm == arm and x.success for x in closures),
        )
        for arm in ARMS
    }
    for x, y in zip(closures[4::2], closures[5::2]):
        if x.selected_action != y.selected_action or x.success != y.success:
            raise I5Rejected("S11 and cheap count differ on same source/action")
    return {
        "episode": "adversarial" if noisy else "clean",
        "training_actions": training_count,
        "followup_actions": len(eval_ids),
        "total_world_actions": world.actions_executed,
        "counts": counts,
        "native_s10_commits": native_s10_count,
        "separate_s11_test_grants": s11_grants,
        "actual_s11_rules": len(owner.rules),
        "cheap_quorum_rules": len(cheap),
        "original_owner_revision": original_owner.revision,
        "new_owner_revision": owner.revision,
        "closures": tuple(closures),
        "no_native_s16_s17_join": True,
    }


def run_i5_closure() -> dict[str, object]:
    m = frozen_manifest()
    if (
        m["exact_b16_base"] != "f4e31933c464f9b39f854dd2408134544d3f9f76"
        or m["owner_issue"] != 515
        or m["evaluation_receipts_are_training"] is not False
        or m["production_go"] is not False
        or m["native_s16_s17_world_join"] is not False
        or MIN_VOTES != 4
        or N_TRIALS != 5
    ):
        raise I5Rejected("I5 frozen B16 experiment authority mismatch")
    clean, noisy = run_i5_episode(noisy=False), run_i5_episode(noisy=True)
    reports = (clean, noisy)
    training = sum(x["training_actions"] for x in reports)
    followup = sum(x["followup_actions"] for x in reports)
    counts = {
        arm: tuple(sum(x["counts"][arm][j] for x in reports) for j in (0, 1))
        for arm in ARMS
    }
    if (
        training != 80
        or followup != 21
        or sum(x["total_world_actions"] for x in reports) != 101
        or tuple(x["followup_actions"] for x in reports) != (12, 9)
        or counts != {
            "ONE_SHOT": (7, 4),
            "S11_QUORUM": (7, 6),
            "CHEAP_COUNT": (7, 6),
        }
        or any(
            x["counts"]["S11_QUORUM"] != x["counts"]["CHEAP_COUNT"]
            for x in reports
        )
    ):
        raise I5Rejected("predeclared B16 simulator behavior/cheap Grand Null differs")
    return {
        "classification": "I5_B16_QUORUM_SIMULATOR_ACTION_CLOSURE_CHEAP_COUNT_PARITY",
        "episodes": reports,
        "training_actions": training,
        "followup_actions": followup,
        "all_simulator_actions": training + followup,
        "arm_results": counts,
        "quorum_benefit_is_not_s10_specific": True,
        "cheap_count_matches_s11": True,
        "native_minecraft": False,
        "native_s16_s17_world_join": False,
        "production_habit_owner": False,
        "measured_resource_advantage": False,
        "actual_l2": False,
        "production_go": False,
    }
