"""C9: World-inspection epistemic value and action redecision, offline only.

World observations are paid and source-bound. The toy is not a live Self,
Minecraft agent, LLM, GPU workload, physical joule or production authority.
"""
from __future__ import annotations

import hashlib
import json
import random
from collections import Counter
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path

MANIFEST_PATH = Path(__file__).with_name("ac_c_c9_manifest.json")
MANIFEST_SHA = "063d2c4b2fd3b232f162e6eb61f3752fc601abff1afff1cc75eeaf06ec3d96c1"
ARMS = (
    "NO_RETRY", "ALWAYS_FLIP", "ALWAYS_DETOUR", "CHEAP_HINT",
    "NO_INSPECT_BAYES", "ALWAYS_INSPECT", "VOI_BAYES",
    "INSPECT_SIMPLE", "EVALUATOR_ORACLE",
)
SECONDS = ("STOP", "NORMAL_FLIP", "DETOUR_SAME", "DETOUR_FLIP", "NORMAL_SAME")
COST = {
    "FIRST_NORMAL": (1, 1),
    "NORMAL_SAME": (1, 1), "NORMAL_FLIP": (1, 1),
    "DETOUR_SAME": (3, 4), "DETOUR_FLIP": (3, 4),
    "INSPECT": (2, 3), "STOP": (0, 0),
}


def sha(obj: object) -> str:
    return hashlib.sha256(json.dumps(
        obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode()).hexdigest()


@lru_cache(maxsize=1)
def cfg() -> dict:
    obj = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if sha(obj) != MANIFEST_SHA:
        raise ValueError("FROZEN_C9_MANIFEST_DRIFT")
    return obj


@dataclass(frozen=True)
class Case:
    session: str
    epoch: str
    group: int
    prefix: int
    hidden_z: int
    blocked: bool
    cheap_hint: bool | None
    inspect_hint: bool
    inspect_available: bool
    deadline: int
    health: int
    hunger: int
    threat: bool

    @property
    def target(self) -> int:
        return (self.prefix.bit_count() & 1) ^ self.hidden_z


@dataclass(frozen=True)
class E0:
    session: str
    revision: int
    group: int
    prefix: int
    inspect_available: bool
    deadline: int
    health: int
    hunger: int
    threat: bool


@dataclass(frozen=True)
class CalibrationReceipt:
    session: str
    group: int
    observed_z: int


@dataclass(frozen=True)
class FirstReceipt:
    session: str
    e0_hash: str
    selected_action: int
    moved: bool
    cheap_hint: bool | None
    revision: int


@dataclass(frozen=True)
class InspectReceipt:
    session: str
    first_hash: str
    hinted_obstruction: bool
    revision: int


@dataclass(frozen=True)
class SecondReceipt:
    session: str
    first_hash: str
    inspect_hash: str | None
    action: str
    moved: bool
    revision: int


class CalibrationWorld:
    """Twenty-four source-owned, paid-model calibration labels per group."""

    def __init__(self, seed: int):
        rng = random.Random(seed * 1000 + 17)
        self._issued = tuple(
            CalibrationReceipt(f"c9:cal:{seed}:{g}:{i}", g,
                               int(rng.random() < cfg()["hidden_z_p1"]["base"][g]))
            for g in (0, 1) for i in range(
                cfg()["calibration"]["shared_per_group_paid_z_labels"]
            )
        )
        self._consumed: set[int] = set()

    def issued(self) -> tuple[CalibrationReceipt, ...]:
        return self._issued

    def consume(self, receipt: CalibrationReceipt) -> None:
        ref = next((i for i, item in enumerate(self._issued) if item is receipt), None)
        if ref is None or ref in self._consumed:
            raise ValueError("UNSOURCED_OR_REPLAYED_CALIBRATION")
        self._consumed.add(ref)


def train(seed: int) -> tuple[tuple[int, int], ...]:
    source = CalibrationWorld(seed)
    counts = [[0, 0], [0, 0]]
    for r in source.issued():
        source.consume(r)
        counts[r.group][0] += r.observed_z
        counts[r.group][1] += 1
    return tuple((ones, n) for ones, n in counts)


def group_prediction(counts: tuple[tuple[int, int], ...], group: int) -> tuple[int, float]:
    ones, n = counts[group]
    p1 = (ones + 1) / (n + 2)
    zguess = int(p1 > .5)
    return zguess, p1 if zguess else 1-p1


def generate(seed: int) -> tuple[Case, ...]:
    rng = random.Random(seed)
    m = cfg()
    out = []
    for epoch in m["epochs"]:
        for index in range(m["episodes_per_epoch"]):
            group = rng.randrange(2)
            z = int(rng.random() < m["hidden_z_p1"][epoch][group])
            block = rng.random() < m["obstruction_probability"][epoch]
            cheap = None
            if rng.random() < m["world"]["cheap_obstacle_hint_present"]:
                cheap = block if rng.random() < m["world"]["cheap_obstacle_hint_accuracy"] else not block
            inspect_signal = block if rng.random() < m["world"]["inspect_hint_accuracy"] else not block
            out.append(Case(
                session=f"c9:{seed}:{epoch}:{index}", epoch=epoch, group=group,
                prefix=rng.randrange(4), hidden_z=z, blocked=block,
                cheap_hint=cheap, inspect_hint=inspect_signal,
                inspect_available=rng.random() < m["world"]["inspector_available"],
                deadline=rng.choice(m["world"]["deadline_values"]),
                health=rng.choice(m["world"]["health_values"]),
                hunger=rng.choice(m["world"]["hunger_values"]),
                threat=rng.random() < m["world"]["threat_probability"],
            ))
    return tuple(out)


def first_viable(e: E0) -> bool:
    return e.revision == 0 and e.deadline >= 1 and e.health > 2


def second_viable(e: E0, action: str, inspected: bool) -> bool:
    if action == "STOP":
        return True
    if action not in SECONDS:
        return False
    remaining_time = e.deadline - COST["FIRST_NORMAL"][0] - (
        COST["INSPECT"][0] if inspected else 0
    )
    remaining_health = e.health - cfg()["world"]["first_fail_health_damage"]
    ticks = COST[action][0]
    if remaining_time < ticks:
        return False
    if action.startswith("NORMAL"):
        return remaining_health > 2
    exposure = int(e.threat) * cfg()["world"]["detour_threat_exposure"]
    return e.hunger > 2 and remaining_health > 1 + exposure


def inspect_viable(e: E0) -> bool:
    return (
        e.inspect_available and any(
            second_viable(e, a, inspected=True) for a in SECONDS if a != "STOP"
        )
    )


class World:
    """Two Actions and one optional paid observation, all receipt-gated."""

    def __init__(self, case: Case):
        self._c = case
        self._first: FirstReceipt | None = None
        self._first_consumed = False
        self._inspect: InspectReceipt | None = None
        self._inspect_consumed = False
        self._second: SecondReceipt | None = None
        self._second_consumed = False
        self._stopped = False
        self._initial_zn: int | None = None

    def e0(self) -> E0:
        c = self._c
        return E0(c.session, 0, c.group, c.prefix, c.inspect_available,
                  c.deadline, c.health, c.hunger, c.threat)

    def issue_first(self, e: E0, initial_zn: int) -> FirstReceipt:
        if self._first is not None:
            raise ValueError("DUPLICATE_FIRST")
        if e != self.e0() or not first_viable(e):
            raise ValueError("UNAUTHORIZED_FIRST")
        if initial_zn not in (0, 1):
            raise ValueError("UNPAID_INITIAL_Z")
        self._initial_zn = initial_zn
        action = (e.prefix.bit_count() & 1) ^ initial_zn
        moved = (initial_zn == self._c.hidden_z and not self._c.blocked)
        self._first = FirstReceipt(
            e.session, sha(asdict(e)), action, moved,
            self._c.cheap_hint, 1,
        )
        return self._first

    def consume_first(self, e: E0, r: FirstReceipt) -> FirstReceipt:
        if (self._first_consumed or self._first is not r or e != self.e0()
                or r.session != e.session or r.e0_hash != sha(asdict(e))
                or r.revision != 1):
            raise ValueError("INVALID_OR_REPLAYED_FIRST")
        self._first_consumed = True
        return r

    def issue_inspect(self, e: E0, first: FirstReceipt) -> InspectReceipt:
        if not (self._first_consumed and self._first is first
                and not first.moved and not self._stopped and self._second is None
                and self._inspect is None and e == self.e0() and inspect_viable(e)):
            raise ValueError("INSPECT_NOT_ADMITTED")
        self._inspect = InspectReceipt(
            e.session, sha(asdict(first)), self._c.inspect_hint, 2,
        )
        return self._inspect

    def consume_inspect(self, e: E0, first: FirstReceipt,
                        receipt: InspectReceipt) -> InspectReceipt:
        if (self._inspect_consumed or self._inspect is not receipt
                or self._first is not first or not self._first_consumed
                or receipt.first_hash != sha(asdict(first))
                or receipt.session != e.session or receipt.revision != 2
                or e != self.e0()):
            raise ValueError("INVALID_OR_REPLAYED_INSPECTION")
        self._inspect_consumed = True
        return receipt

    def issue_second(self, e: E0, first: FirstReceipt,
                     action: str, *, inspect: InspectReceipt | None = None) -> SecondReceipt:
        if (self._second is not None or self._stopped or not self._first_consumed
                or self._first is not first or first.moved or e != self.e0()):
            raise ValueError("SECOND_NOT_AUTHORIZED")
        if self._inspect is not None:
            if inspect is not self._inspect or not self._inspect_consumed:
                raise ValueError("UNCONSUMED_OR_FOREIGN_INSPECTION")
        elif inspect is not None:
            raise ValueError("UNPAID_INSPECTION_USE")
        if not second_viable(e, action, self._inspect is not None) or action == "STOP":
            raise ValueError("UNSAFE_OR_UNKNOWN_SECOND")
        same = action.endswith("SAME")
        z = self._initial_zn if same else 1-self._initial_zn
        bypass = action.startswith("DETOUR")
        moved = (z == self._c.hidden_z and (bypass or not self._c.blocked))
        self._second = SecondReceipt(
            e.session, sha(asdict(first)),
            sha(asdict(inspect)) if inspect is not None else None,
            action, moved, 3 if inspect is None else 4,
        )
        return self._second

    def consume_second(self, e: E0, first: FirstReceipt, r: SecondReceipt) -> SecondReceipt:
        if (self._second_consumed or self._second is not r or
                self._first is not first or not self._first_consumed or
                r.session != e.session or r.first_hash != sha(asdict(first)) or
                r.inspect_hash != (sha(asdict(self._inspect)) if self._inspect else None)
                or r.revision != (4 if self._inspect else 3) or e != self.e0()):
            raise ValueError("INVALID_OR_REPLAYED_SECOND")
        self._second_consumed = True
        return r

    def stop(self, e: E0, first: FirstReceipt) -> None:
        if (self._stopped or self._second is not None or self._first is not first or
                not self._first_consumed or first.moved or e != self.e0()):
            raise ValueError("STOP_NOT_AUTHORIZED")
        self._stopped = True

    def evaluate(self) -> dict:
        """Privileged evaluator only; never an input to planning."""
        if self._first is None or not self._first_consumed:
            raise ValueError("NO_COMPLETED_FIRST")
        if not (self._first.moved or self._stopped or self._second_consumed):
            raise ValueError("NO_TERMINAL_COMPLETION")
        first_moved = self._first.moved
        second_moved = self._second.moved if self._second_consumed else False
        return {
            "success": bool(first_moved or second_moved),
            "first_moved": first_moved, "second_moved": second_moved,
            "first_wrong": self._initial_zn != self._c.hidden_z,
            "first_failed_but_correct": not first_moved and self._initial_zn == self._c.hidden_z,
            "actual_block": self._c.blocked,
        }


def posterior(q: float, cheap: bool | None,
              inspected: bool | None = None) -> dict[tuple[bool, bool], float]:
    """Conditional on first NORMAL failed; supports no hidden World reads."""
    p_block = cfg()["planning"]["assumed_obstruction_probability"]
    weights = {
        (True, True): q*p_block,
        (False, True): (1-q)*p_block,
        (False, False): (1-q)*(1-p_block),
    }
    def lh(signal: bool | None, real_block: bool, accuracy: float) -> float:
        if signal is None:
            return 1.0
        return accuracy if signal == real_block else 1-accuracy
    for (match, block), weight in list(weights.items()):
        weights[(match, block)] = (
            weight * lh(cheap, block, cfg()["planning"]["cheap_hint_accuracy"])
            * lh(inspected, block, cfg()["planning"]["inspect_hint_accuracy"])
        )
    total = sum(weights.values())
    if total <= 0:
        raise ValueError("NONNORMALIZABLE_POSTERIOR")
    return {key: val/total for key, val in weights.items()}


def expected_second(e: E0, beliefs: dict[tuple[bool, bool], float],
                    *, inspected: bool) -> tuple[str, float]:
    opts = cfg()["planning"]["second_score"]
    best_action = "STOP"
    best = float(opts["stop"])
    for action in SECONDS:
        if action == "STOP" or not second_viable(e, action, inspected):
            continue
        p = sum(
            prob for (match, blocked), prob in beliefs.items()
            if (match if action.endswith("SAME") else not match)
            and (action.startswith("DETOUR") or not blocked)
        )
        tick, work = COST[action]
        utility = (
            p * opts["success"] + (1-p)*opts["failure"]
            + opts["per_work"]*work + opts["per_tick"]*tick
        )
        if utility > best + 1e-12:
            best, best_action = utility, action
    return best_action, best


def voi_decision(e: E0, q: float, hint: bool | None) -> tuple[bool, str, float]:
    beliefs = posterior(q, hint)
    initial, value_no = expected_second(e, beliefs, inspected=False)
    if not inspect_viable(e):
        return False, initial, 0.0
    signal_prob = {}
    after_value = {}
    for signal in (False, True):
        accuracy = cfg()["planning"]["inspect_hint_accuracy"]
        signal_prob[signal] = sum(
            p * (accuracy if signal == block else 1-accuracy)
            for (_, block), p in beliefs.items()
        )
        after_value[signal] = expected_second(
            e, posterior(q, hint, signal), inspected=True
        )[1]
    it, iw = COST["INSPECT"]
    cost = -(cfg()["planning"]["second_score"]["per_work"]*iw +
             cfg()["planning"]["second_score"]["per_tick"]*it)
    evi = sum(signal_prob[s] * after_value[s] for s in (False, True)) - cost - value_no
    return evi > 1e-12, initial, evi


def cheap_heuristic(e: E0, hint: bool | None, *, inspected: bool) -> str:
    priority = ("DETOUR_SAME", "NORMAL_FLIP", "DETOUR_FLIP") if hint is True else (
        "NORMAL_FLIP", "DETOUR_SAME", "DETOUR_FLIP",
    )
    for action in priority:
        if second_viable(e, action, inspected):
            return action
    return "STOP"


def run_arm(seed: int, arm: str) -> dict:
    m = cfg()
    if seed not in m["seeds"]["calibration"] + m["seeds"]["heldout"]:
        raise ValueError("SEED_NOT_PREREGISTERED")
    if arm not in ARMS:
        raise ValueError("ARM_NOT_PREREGISTERED")
    priors = train(seed)
    trace = []
    for case in generate(seed):
        world = World(case)
        e = world.e0()
        mode = "ABSTAIN"
        first_success = False
        second_action = "NONE"
        inspected = False
        choice_changed = False
        evi = None
        first_failure = False
        final_success = False
        inspector_hint = None
        initial, q = group_prediction(priors, e.group)
        first_r = None
        insp_r = None
        if first_viable(e):
            first_r = world.consume_first(e, world.issue_first(e, initial))
            first_success = first_r.moved
            final_success = first_success
            mode = "FIRST_NORMAL"
            if not first_success:
                first_failure = True
                beliefs = posterior(q, first_r.cheap_hint)
                noinspect_best = expected_second(e, beliefs, inspected=False)[0]
                choice = "STOP"
                if arm == "EVALUATOR_ORACLE":
                    # privileged upper bound, excluded from fair comparisons
                    allowed = [
                        a for a in SECONDS if second_viable(e, a, inspected=False)
                    ]
                    valid = []
                    for action in allowed:
                        if action == "STOP":
                            success = False
                        else:
                            same = action.endswith("SAME")
                            correct = (initial if same else 1-initial) == case.hidden_z
                            success = correct and (
                                action.startswith("DETOUR") or not case.blocked
                            )
                        work = COST[action][1]
                        ticks = COST[action][0]
                        pay = (-1 if action == "STOP" else 12 if success else -6)
                        pay -= .6*work + .4*ticks
                        valid.append((pay, action))
                    choice = max(valid, key=lambda v: v[0])[1]
                elif arm == "NO_RETRY":
                    choice = "STOP"
                elif arm == "ALWAYS_FLIP":
                    choice = "NORMAL_FLIP" if second_viable(e, "NORMAL_FLIP", False) else "STOP"
                elif arm == "ALWAYS_DETOUR":
                    choice = cheap_heuristic(e, True, inspected=False)
                elif arm == "CHEAP_HINT":
                    choice = cheap_heuristic(e, first_r.cheap_hint, inspected=False)
                elif arm == "NO_INSPECT_BAYES":
                    choice = noinspect_best
                elif arm in ("ALWAYS_INSPECT", "VOI_BAYES", "INSPECT_SIMPLE"):
                    allowed = inspect_viable(e)
                    if arm == "VOI_BAYES":
                        allowed, _, evi = voi_decision(e, q, first_r.cheap_hint)
                    if allowed:
                        insp_r = world.consume_inspect(
                            e, first_r, world.issue_inspect(e, first_r)
                        )
                        inspector_hint = insp_r.hinted_obstruction
                        inspected = True
                        if arm == "INSPECT_SIMPLE":
                            choice = cheap_heuristic(e, inspector_hint, inspected=True)
                        else:
                            choice = expected_second(
                                e, posterior(q, first_r.cheap_hint, inspector_hint),
                                inspected=True,
                            )[0]
                        choice_changed = choice != noinspect_best
                    else:
                        if arm == "INSPECT_SIMPLE":
                            choice = cheap_heuristic(e, first_r.cheap_hint, inspected=False)
                        else:
                            choice = noinspect_best
                else:
                    raise ValueError("UNRECOGNIZED_ARM")
                second_action = choice
                if choice == "STOP":
                    world.stop(e, first_r)
                else:
                    second_r = world.consume_second(
                        e, first_r, world.issue_second(
                            e, first_r, choice, inspect=insp_r
                        ),
                    )
                    final_success = second_r.moved
                # Privileged ground truth read only after terminal completion.
                check = world.evaluate()
                assert check["success"] == final_success
        overhead = m["selector_overhead_per_failed_initial_attempt"][arm] if first_failure else 0
        mechanism_work = int(mode == "FIRST_NORMAL")
        ticks = mechanism_work
        if inspected:
            mechanism_work += COST["INSPECT"][1]
            ticks += COST["INSPECT"][0]
        if second_action not in ("NONE", "STOP"):
            mechanism_work += COST[second_action][1]
            ticks += COST[second_action][0]
        terminal = "SUCCESS" if final_success else (
            "INITIAL_ABSTAIN" if mode == "ABSTAIN" else
            "STOP" if second_action == "STOP" else "FAILED_SECOND"
        )
        u = m["final_episode_utility"]
        base = (u["success"] if terminal == "SUCCESS"
                else u["exhausted_failed_retry"] if terminal == "FAILED_SECOND"
                else u["initial_inadmissible_abstain"] if terminal == "INITIAL_ABSTAIN"
                else u["voluntary_stop_after_first_failure"])
        util = base + u["per_combined_work"]*(mechanism_work+overhead) + u["per_world_tick"]*ticks
        damage = int(first_failure) + int(second_action not in ("NONE", "STOP") and not final_success)
        damage += int(e.threat and second_action.startswith("DETOUR"))
        trace.append({
            "session": e.session, "epoch": case.epoch,
            "group": e.group, "initial_zn": initial, "initial_confidence": q,
            "initial_feasible": mode != "ABSTAIN",
            "first_success": first_success, "first_failure": first_failure,
            "cheap_hint": first_r.cheap_hint if first_r is not None else None,
            "inspected": inspected, "inspection_hint": inspector_hint,
            "second_action": second_action, "changed_from_noinspect": choice_changed,
            "positive_evi": evi is not None and evi > 0,
            "evi": evi, "success": final_success, "terminal": terminal,
            "work": mechanism_work, "selector_work": overhead, "ticks": ticks,
            "damage": damage, "utility_tenths": round(10*util),
        })
    metrics = (
        "success", "first_success", "first_failure", "inspected",
        "changed_from_noinspect", "positive_evi",
    )
    phases = {}
    for ep in m["epochs"]:
        rows = [row for row in trace if row["epoch"] == ep]
        if len(rows) != m["episodes_per_epoch"]:
            raise AssertionError("BAD_EPOCH_SIZE")
        phases[ep] = {
            **{metric: sum(bool(row[metric]) for row in rows) for metric in metrics},
            "initial_abstain": sum(row["terminal"] == "INITIAL_ABSTAIN" for row in rows),
            "stop": sum(row["terminal"] == "STOP" for row in rows),
            "failed_second": sum(row["terminal"] == "FAILED_SECOND" for row in rows),
            "work": sum(row["work"] for row in rows),
            "selector_work": sum(row["selector_work"] for row in rows),
            "ticks": sum(row["ticks"] for row in rows),
            "damage": sum(row["damage"] for row in rows),
            "utility_tenths": sum(row["utility_tenths"] for row in rows),
            "choices": dict(sorted(Counter(row["second_action"] for row in rows).items())),
        }
    return {"arm": arm, "seed": seed, "calibration_counts": priors,
            "phases": phases, "trace": tuple(trace)}


def report() -> dict:
    m = cfg()
    results = [
        run_arm(seed, arm)
        for seed in m["seeds"]["calibration"] + m["seeds"]["heldout"]
        for arm in ARMS
    ]
    keys = (
        "success", "first_success", "first_failure", "inspected",
        "changed_from_noinspect", "positive_evi", "initial_abstain",
        "stop", "failed_second", "work", "selector_work", "ticks",
        "damage", "utility_tenths",
    )
    aggregates = {}
    for split, seeds in m["seeds"].items():
        aggregates[split] = {}
        for arm in ARMS:
            rr = [x for x in results if x["seed"] in seeds and x["arm"] == arm]
            aggregates[split][arm] = {
                key: sum(x["phases"][ep][key] for x in rr for ep in m["epochs"])
                for key in keys
            }
    heldout_phases = {
        arm: {
            ep: {
                key: sum(
                    r["phases"][ep][key] for r in results
                    if r["arm"] == arm and r["seed"] in m["seeds"]["heldout"]
                ) for key in keys
            } for ep in m["epochs"]
        } for arm in ARMS
    }
    paired = {}
    for seed in m["seeds"]["heldout"]:
        rr = {a: next(r for r in results if r["seed"] == seed and r["arm"] == a)
              for a in ARMS}
        assert len({tuple(t["session"] for t in r["trace"]) for r in rr.values()}) == 1
        assert len({r["calibration_counts"] for r in rr.values()}) == 1
        paired[str(seed)] = {
            "voi_minus_cheap_success": sum(
                rr["VOI_BAYES"]["phases"][ep]["success"] -
                rr["CHEAP_HINT"]["phases"][ep]["success"]
                for ep in m["epochs"]
            ),
            "voi_minus_noinspect_success": sum(
                rr["VOI_BAYES"]["phases"][ep]["success"] -
                rr["NO_INSPECT_BAYES"]["phases"][ep]["success"]
                for ep in m["epochs"]
            ),
            "voi_inspections": sum(rr["VOI_BAYES"]["phases"][ep]["inspected"] for ep in m["epochs"]),
            "voi_changed_actions": sum(
                rr["VOI_BAYES"]["phases"][ep]["changed_from_noinspect"]
                for ep in m["epochs"]
            ),
        }
    answer = {"manifest_sha256": MANIFEST_SHA, "summary": aggregates,
              "heldout_phases": heldout_phases, "paired": paired}
    answer["result_sha256"] = sha(answer)
    return answer


if __name__ == "__main__":
    print(json.dumps(report(), sort_keys=True, ensure_ascii=False))
