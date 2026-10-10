"""B19: OFFLINE B18 source-value versus C-style resource-constrained computation.

Reuses B18 native S10 training and frozen S11 read-only policy as the
observational basis. Never imports another unmerged Lane C experiment.
THINK is deliberately SAME-INPUT ANALYTIC recomputation of cheap Q, NOT
an actual L2, LLM, autonomous cognition or independent World evidence.
All health/hunger/tick/work cost amounts are synthetic, not physical.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from experiments.ac_b_b11_governed_habit import CONTEXTS, empty_repertoire
from experiments.ac_b_b17_source_value import execute_trial
from experiments.ac_b_b18_empirical_voi import (
    ABSTAIN_REWARD,
    CORRECT_REWARD,
    RISKS,
    EmpiricalTable,
    TrainingReceipt,
    grant_experiment_only,
    learn_empirical_table,
    retain_test_policy,
    selected_s11_option,
    source_action,
    sources_for,
    train_actual_s10_feedback,
    training_case,
)
from relay_self.habit import HabitRepertoire

PROFILES = {
    "OPEN": (6, 6, 7),
    "TIGHT": (6, 6, 1),
    "HUNGRY": (3, 1, 7),
}
ARMS = ("L1_STOP", "B18_CHEAP_Q", "ALWAYS_THINK", "VALUE_GATE")
WORK_PRICE = Fraction(1, 2)
TICK_PRICE = Fraction(1, 4)
PREFIX_SOURCE_COST = 2
SECONDARY_SOURCE_COST = 2
STOP_WORK = STOP_TICKS = 1
QUERY_WORK = 2
QUERY_TICKS = 3
THINK_EXTRA_WORK = 4
THINK_EXTRA_TICKS = 3
GATE_SELECTOR_WORK = 1


class InvalidB19Allocation(ValueError):
    """Fail closed on incompatible mode or unsupported World evidence."""


@dataclass(frozen=True, slots=True)
class Resource:
    health: int
    hunger: int
    deadline: int

    def __post_init__(self) -> None:
        if any(
            type(v) is not int or v < 0
            for v in (self.health, self.hunger, self.deadline)
        ):
            raise InvalidB19Allocation("nonnegative integer resources required")

    def stop_allowed(self) -> bool:
        return self.health >= 3 and self.deadline >= 1

    def query_allowed(self) -> bool:
        return (
            self.health >= 3
            and self.hunger >= 3
            and self.deadline >= 3
        )

    def think_allowed(self) -> bool:
        return (
            self.health >= 4
            and self.hunger >= 4
            and self.deadline >= 4
        )

    def think_query_allowed(self) -> bool:
        return self.think_allowed() and self.query_allowed() and self.deadline >= 6


@dataclass(frozen=True, slots=True)
class Allocation:
    mode: str
    chosen_candidate: str
    work: int
    ticks: int
    selector_work: int
    omitted_due_to_constraints: bool

    @property
    def source_query(self) -> bool:
        return self.chosen_candidate == "QUERY_S"


def recompute_same_public_Q(table: EmpiricalTable, vote: int) -> str:
    """Positive-cost L2-like analytic comparator, with ZERO new information."""
    if vote not in (0, 1) or not isinstance(table, EmpiricalTable):
        raise InvalidB19Allocation("exact already public vote/table required")
    scores = table.mean_scores[vote]
    decision = max(scores, key=lambda row: row[1])[0]
    if decision != table.choices[vote]:
        raise InvalidB19Allocation("frozen learned table inconsistent")
    return decision


def _mode(mode: str, option: str, *, gated: bool, blocked: bool) -> Allocation:
    if option not in ("STOP", "QUERY_S"):
        raise InvalidB19Allocation("only B19 admitted STOP/QUERY_S")
    if mode not in ("STOP", "QUERY_S", "THINK_STOP", "THINK_QUERY_S"):
        raise InvalidB19Allocation("unsupported allocation")
    if mode.startswith("THINK"):
        work = (QUERY_WORK if option == "QUERY_S" else STOP_WORK) + THINK_EXTRA_WORK
        ticks = (QUERY_TICKS if option == "QUERY_S" else STOP_TICKS) + THINK_EXTRA_TICKS
    else:
        work = QUERY_WORK if option == "QUERY_S" else STOP_WORK
        ticks = QUERY_TICKS if option == "QUERY_S" else STOP_TICKS
    return Allocation(
        mode=mode, chosen_candidate=option, work=work, ticks=ticks,
        selector_work=GATE_SELECTOR_WORK if gated else 0,
        omitted_due_to_constraints=blocked,
    )


def candidate_expected_net_Q(
    table: EmpiricalTable, vote: int, mode: str, resource: Resource,
) -> Fraction | None:
    """Empirical Q already charges extra source price; work/tick charged here."""
    if not resource.stop_allowed():
        return None
    if mode == "STOP":
        option = "STOP"
    elif mode == "QUERY_S" and resource.query_allowed():
        option = "QUERY_S"
    elif mode == "THINK_STOP" and resource.think_allowed():
        option = "STOP"
    elif mode == "THINK_QUERY_S" and resource.think_query_allowed():
        option = "QUERY_S"
    else:
        return None
    scored = dict(table.mean_scores[vote])
    proposed = _mode(mode, option, gated=False, blocked=False)
    return (
        scored[option]
        - proposed.work * WORK_PRICE
        - proposed.ticks * TICK_PRICE
    )


def choose(
    table: EmpiricalTable,
    vote: int,
    resource: Resource,
    arm: str,
) -> Allocation | None:
    """No hidden World or secondary outcome available at selection."""
    if arm not in ARMS or vote not in (0, 1) or not isinstance(
        resource, Resource
    ) or not isinstance(table, EmpiricalTable):
        raise InvalidB19Allocation("frozen arm, typed resource and public vote required")
    if not resource.stop_allowed():
        return None
    learned = table.choices[vote]
    if learned not in ("STOP", "QUERY_S"):
        raise InvalidB19Allocation("unsupported learned B18 action")
    if arm == "L1_STOP":
        return _mode("STOP", "STOP", gated=False, blocked=False)
    if arm == "B18_CHEAP_Q":
        blocked = learned == "QUERY_S" and not resource.query_allowed()
        mode = "STOP" if blocked else learned
        return _mode(mode, mode, gated=False, blocked=blocked)
    if arm == "ALWAYS_THINK":
        if not resource.think_allowed():
            return _mode(
                "STOP", "STOP", gated=False, blocked=True,
            )
        recomputed = recompute_same_public_Q(table, vote)
        query = recomputed == "QUERY_S" and resource.think_query_allowed()
        option = "QUERY_S" if query else "STOP"
        return _mode(
            "THINK_QUERY_S" if query else "THINK_STOP",
            option, gated=False,
            blocked=recomputed == "QUERY_S" and not query,
        )
    feasible = (
        (mode, candidate_expected_net_Q(table, vote, mode, resource))
        for mode in ("STOP", "QUERY_S", "THINK_STOP", "THINK_QUERY_S")
    )
    options = [(name, val) for name, val in feasible if val is not None]
    if not options:
        return None
    # Stable tie order defined above; selector overhead applies equally
    # to each option, thus cancels when finding the best candidate.
    mode = max(options, key=lambda row: row[1])[0]
    option = "QUERY_S" if mode.endswith("QUERY_S") else "STOP"
    return _mode(
        mode, option, gated=True,
        blocked=learned == "QUERY_S" and option != "QUERY_S",
    )


def qualify_reported_pair(
    trial: object, sources: dict[str, object], cue: tuple[int, int],
    channel: str, index: int,
) -> int | None:
    """B11 same-process source receipt identity, NOT sensor-truth attestation."""
    if (
        channel not in ("P", "S")
        or trial.channel != channel
        or trial.source is not sources[channel]
        or trial.trial_index != index
        or trial.pair.trial != index
    ):
        raise InvalidB19Allocation("source channel/trial identity mismatch")
    observed = sources[channel]
    for a, event in enumerate((trial.pair.action0, trial.pair.action1)):
        if (
            not observed.observed(event)
            or (event.a, event.b, event.action) != (*cue, a)
            or event.session != observed.session
            or event.revision != observed.revision
            or type(event.success) is not bool
            or event.kind != "OBSERVED_ACTION"
        ):
            raise InvalidB19Allocation("unissued/cloned/foreign source report")
    if trial.pair.action0.event_id == trial.pair.action1.event_id:
        raise InvalidB19Allocation("replayed duplicate source Action")
    return trial.pair.vote()


def _retained_owners(
    receipt: TrainingReceipt,
) -> dict[str, tuple[EmpiricalTable, HabitRepertoire]]:
    owners = {}
    for risk in ("HIGH", "LOW"):
        table = learn_empirical_table(receipt, risk=risk)
        owner = empty_repertoire(label=f"b19-exp-retained-{risk}")
        original = owner
        for vote in (0, 1):
            grant = grant_experiment_only(owner, table, vote)
            owner = retain_test_policy(owner, receipt, table, vote, grant)
        assert original.rules == () and original.revision == 0
        assert owner.revision == 2
        owners[risk] = (table, owner)
    return owners


def score_arm(
    table: EmpiricalTable,
    owner: HabitRepertoire,
    profile: str,
    arm: str,
) -> dict[str, object]:
    if profile not in PROFILES or arm not in ARMS:
        raise InvalidB19Allocation("exact preregistered risk/resource/arm required")
    resource = Resource(*PROFILES[profile])
    actual_actions = correct = wrong = abstained = queried = 0
    blocked = work = ticks = selector = 0
    source_cost = 0
    cases = []
    for correlated in (False, True):
        for cue in CONTEXTS:
            name = (
                f"b19-{table.risk}-{profile}-{arm}-"
                f"{'corr' if correlated else 'clean'}-{cue[0]}{cue[1]}"
            )
            sources = sources_for(name)
            first = execute_trial(
                sources, cue, 0, "P", correlated=correlated,
            )
            second = execute_trial(
                sources, cue, 1, "P", correlated=correlated,
            )
            p0 = qualify_reported_pair(first, sources, cue, "P", 0)
            p1 = qualify_reported_pair(second, sources, cue, "P", 1)
            if p0 is None or p1 != p0:
                raise InvalidB19Allocation("ambiguous P prefix cannot authorize action")
            # Native frozen S11 read-only decision is checked against exact
            # same-source cheap Q for EACH world session, BEFORE allocation.
            habit = selected_s11_option(
                owner, p0, trial=f"{name}-new-nuisance",
            )
            if habit != table.choices[p0]:
                raise InvalidB19Allocation("actual S11 vs cheap Q source-policy mismatch")
            decision = choose(table, p0, resource, arm)
            if decision is None:
                choice = None
                option = "ABSTAIN"
                decision_work = decision_ticks = selector_work = 0
                blocked += 1
            else:
                option = decision.chosen_candidate
                decision_work, decision_ticks = decision.work, decision.ticks
                selector_work = decision.selector_work
                blocked += int(decision.omitted_due_to_constraints)
                if decision.ticks > resource.deadline:
                    raise InvalidB19Allocation("deadline budget violated")
                third = None
                if decision.source_query:
                    extra = execute_trial(
                        sources, cue, 2, "S", correlated=correlated,
                    )
                    third = qualify_reported_pair(
                        extra, sources, cue, "S", 2,
                    )
                    queried += 1
                choice = source_action(p0, option, third)
            # NO helper scores source truth or success before the action
            # decision was fixed. The query is an actual World source pair.
            right = (
                sources["P"].heldout_score(*cue, choice)
                if choice is not None else None
            )
            correct += int(right is True)
            wrong += int(right is False)
            abstained += int(right is None)
            observed_actions = sum(w.actions_executed for w in sources.values())
            source_cost += PREFIX_SOURCE_COST + (
                SECONDARY_SOURCE_COST if queried and option == "QUERY_S" else 0
            )
            actual_actions += observed_actions
            work += decision_work
            ticks += decision_ticks
            selector += selector_work
            cases.append({
                "source": name, "vote": p0,
                "native_s11_choice": habit,
                "cheap_q_choice": table.choices[p0],
                "admitted_mode": decision.mode if decision else "ABSTAIN",
                "chosen": choice,
                "source_query": option == "QUERY_S",
                "source_actions": observed_actions,
                "correct": right,
            })
    result_reward = (
        correct * CORRECT_REWARD
        + wrong * RISKS[table.risk]
        + abstained * ABSTAIN_REWARD
    )
    net = (
        Fraction(result_reward - source_cost)
        - (work + selector) * WORK_PRICE
        - ticks * TICK_PRICE
    )
    return {
        "risk": table.risk,
        "profile": profile,
        "arm": arm,
        "actual_world_actions": actual_actions,
        "source_pairs_cost": source_cost,
        "correct": correct, "wrong": wrong, "abstained": abstained,
        "secondary_queries": queried,
        "denied_optional_modes": blocked,
        "decision_work_units": work,
        "selector_work_units": selector,
        "decision_tick_units": ticks,
        "deadline_violations": 0,
        "net_symbolic_utility": str(net),
        "actual_s11_equals_cheap_Q_all_cases": all(
            row["native_s11_choice"] == row["cheap_q_choice"]
            for row in cases
        ),
        "cases": tuple(cases),
    }


def run_b19_comparison() -> dict[str, object]:
    cases = tuple(
        training_case(cue=cue, correlated=correlated)
        for correlated in (False, True) for cue in CONTEXTS
    )
    training_actions = sum(
        sum(w.actions_executed for w in case.sources.values())
        for case in cases
    )
    if training_actions != 64:
        raise InvalidB19Allocation("B18 exact eight-source training missing")
    receipt = train_actual_s10_feedback(cases)
    receipt.verify()
    owners = _retained_owners(receipt)
    runs = [
        score_arm(owners[risk][0], owners[risk][1], profile, arm)
        for risk in ("HIGH", "LOW")
        for profile in PROFILES
        for arm in ARMS
    ]
    return {
        "classification": "B19_BOUNDED_RESOURCE_ALLOCATION_SAME_INFORMATION_NULL",
        "actual_offline_training_world_actions": training_actions,
        "existing_native_s10_history_commits": receipt.native_s10_commits,
        "existing_test_only_s11_rules_per_risk": 2,
        "heldout_runs": runs,
        "physical_L2_inference": False,
        "physical_source_independence": False,
        "physical_body_or_energy_measurement": False,
        "native_s10_calculates_Q": False,
        "native_s11_production_retention": False,
    }
