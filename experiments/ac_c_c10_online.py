"""C10: source-only online calibration of movement rule and obstruction.

An isolated deterministic symbolic World, not production RelaySelf, Minecraft,
LLM reasoning, physical energy or an authority to promote HABIT.
"""
from __future__ import annotations

import hashlib
import json
import random
from collections import Counter, deque
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path

MANIFEST_PATH = Path(__file__).with_name("ac_c_c10_manifest.json")
MANIFEST_SHA = "47bef17459ff5d4f5e0e3eb450c26b0146fd90b9cf994971e5a00f1222951767"
ARMS = (
    "FROZEN_HINT", "FROZEN_FLIP", "ADAPT_HINT", "ADAPT_FLIP",
    "ADAPT_BAYES_FIXED", "ADAPT_BAYES_BLOCK", "ADAPT_VOI_BLOCK",
    "ADAPT_INSPECT_SIMPLE", "NO_FEEDBACK_HINT", "EVALUATOR_ORACLE",
)
COST = {
    "FIRST_NORMAL": (1, 1), "NORMAL_FLIP": (1, 1),
    "NORMAL_SAME": (1, 1), "DETOUR_SAME": (3, 4),
    "DETOUR_FLIP": (3, 4), "INSPECT": (2, 3), "STOP": (0, 0),
}
ORDER = ("STOP", "NORMAL_FLIP", "DETOUR_SAME", "DETOUR_FLIP", "NORMAL_SAME")


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


@lru_cache(maxsize=1)
def manifest() -> dict:
    m = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if digest(m) != MANIFEST_SHA:
        raise ValueError("C10_FROZEN_MANIFEST_DRIFT")
    return m


@dataclass(frozen=True)
class HiddenCase:
    session: str
    epoch: str
    group: int
    prefix: int
    z: int
    blocked: bool
    cheap_hint: bool | None
    inspect_hint: bool
    inspect_available: bool
    deadline: int
    health: int
    hunger: int
    threat: bool


@dataclass(frozen=True)
class Evidence:
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
class FirstReceipt:
    session: str
    evidence_hash: str
    zguess: int
    moved: bool
    cheap_hint: bool | None
    revision: int


@dataclass(frozen=True)
class InspectReceipt:
    session: str
    first_hash: str
    hint: bool
    revision: int


@dataclass(frozen=True)
class SecondReceipt:
    session: str
    first_hash: str
    inspect_hash: str | None
    action: str
    executed_z: int
    moved: bool
    revision: int


def generate(seed: int) -> tuple[HiddenCase, ...]:
    m = manifest()
    rng = random.Random(seed)
    rows = []
    for epoch in m["epochs"]:
        for idx in range(m["n_per_epoch"]):
            g = rng.randrange(2)
            z = int(rng.random() < m["hidden_z_probability_1"][epoch][g])
            block = rng.random() < m["obstruction_probability"][epoch]
            cheap = None
            if rng.random() < m["world"]["cheap_hint_presence"]:
                cheap = block if rng.random() < m["world"]["cheap_hint_accuracy"] else not block
            inspected = block if rng.random() < m["world"]["inspect_hint_accuracy"] else not block
            rows.append(HiddenCase(
                f"c10:{seed}:{epoch}:{idx}", epoch, g, rng.randrange(4), z,
                block, cheap, inspected,
                rng.random() < m["world"]["inspect_available"],
                rng.choice(m["world"]["deadline"]),
                rng.choice(m["world"]["health"]),
                rng.choice(m["world"]["hunger"]),
                rng.random() < m["world"]["threat_probability"],
            ))
    return tuple(rows)


def first_viable(e: Evidence) -> bool:
    return e.revision == 0 and e.deadline >= 1 and e.health > 2


def viable_second(e: Evidence, action: str, has_inspected: bool) -> bool:
    if action == "STOP":
        return True
    if action not in COST or action in ("FIRST_NORMAL", "INSPECT"):
        return False
    remaining = e.deadline - COST["FIRST_NORMAL"][0] - (
        COST["INSPECT"][0] if has_inspected else 0
    )
    if remaining < COST[action][0]:
        return False
    health = e.health - manifest()["world"]["failed_first_damage"]
    if action.startswith("NORMAL"):
        return health > 2
    exposure = int(e.threat) * manifest()["world"]["detour_threat_exposure"]
    return e.hunger > 2 and health > 1 + exposure


def viable_inspect(e: Evidence) -> bool:
    return (
        e.inspect_available and any(
            viable_second(e, a, True) for a in ORDER if a != "STOP"
        )
    )


@dataclass
class Belief:
    z_evidence: dict[int, deque[int]] = field(default_factory=dict)
    block_hints: deque[int] = field(default_factory=lambda: deque(maxlen=24))
    admitted_sources: set[str] = field(default_factory=set)

    def zposterior(self, group: int) -> tuple[float, int]:
        hist = self.z_evidence.get(group, ())
        p1 = (1 + sum(hist)) / (2 + len(hist))
        return p1, int(p1 > 0.5)

    def obstacle_rate(self) -> float:
        values = self.block_hints
        if not values:
            return manifest()["learning"]["obstruction_prior_center"]
        m = manifest()["learning"]
        n0 = m["obstruction_pseudocount_strength"]
        # Calibrated pseudocount centered on the observed hint-true rate.
        prior = m["obstruction_prior_center"]
        false_positive = m["obstruction_hint_false_positive"]
        sensitivity = m["obstruction_hint_sensitivity"]
        hint_true_center = false_positive + (sensitivity - false_positive) * prior
        rate = (sum(values) + n0 * hint_true_center) / (len(values) + n0)
        estimate = (rate - false_positive) / (sensitivity - false_positive)
        low, high = m["estimated_block_clamp"]
        return max(low, min(high, estimate))

    def record(self, e: Evidence, first: FirstReceipt,
               second: SecondReceipt | None) -> tuple[bool, bool]:
        if e.session in self.admitted_sources:
            raise ValueError("LEARNING_FEEDBACK_DUPLICATED")
        self.admitted_sources.add(e.session)
        z_label = None
        if first.moved:
            z_label = first.zguess
        elif second is not None:
            if second.moved:
                z_label = second.executed_z
            elif second.action.startswith("DETOUR"):
                # Explicit bypass World law makes this one failure identifiable.
                z_label = 1 - second.executed_z
            # NORMAL failure remains ambiguous and must not label z.
        before = self.zposterior(e.group)[1]
        if z_label is not None:
            self.z_evidence.setdefault(e.group, deque(maxlen=12)).append(z_label)
        if first.cheap_hint is not None:
            self.block_hints.append(int(first.cheap_hint))
        return z_label is not None, before != self.zposterior(e.group)[1]


class World:
    """One session, sequential first/optional inspection/second/retention."""

    def __init__(self, case: HiddenCase):
        self._c = case
        self._first: FirstReceipt | None = None
        self._first_consumed = False
        self._inspect: InspectReceipt | None = None
        self._inspect_consumed = False
        self._second: SecondReceipt | None = None
        self._second_consumed = False
        self._stopped = False
        self._retained = False

    def e0(self) -> Evidence:
        c = self._c
        return Evidence(
            c.session, 0, c.group, c.prefix, c.inspect_available,
            c.deadline, c.health, c.hunger, c.threat,
        )

    def issue_first(self, e: Evidence, zguess: int) -> FirstReceipt:
        if self._first is not None:
            raise ValueError("DUPLICATE_FIRST")
        if e != self.e0() or not first_viable(e) or zguess not in (0, 1):
            raise ValueError("UNAUTHORIZED_FIRST")
        c = self._c
        self._first = FirstReceipt(
            e.session, digest(asdict(e)), zguess,
            zguess == c.z and not c.blocked,
            c.cheap_hint, 1,
        )
        return self._first

    def consume_first(self, e: Evidence, r: FirstReceipt) -> FirstReceipt:
        if (self._first_consumed or self._first is not r or e != self.e0() or
                r.session != e.session or r.evidence_hash != digest(asdict(e))
                or r.revision != 1):
            raise ValueError("INVALID_OR_REPLAYED_FIRST")
        self._first_consumed = True
        return r

    def issue_inspect(self, e: Evidence, first: FirstReceipt) -> InspectReceipt:
        if (not self._first_consumed or first is not self._first or first.moved or
                self._inspect is not None or self._second is not None or
                self._stopped or e != self.e0() or not viable_inspect(e)):
            raise ValueError("UNADMITTED_INSPECTION")
        self._inspect = InspectReceipt(
            e.session, digest(asdict(first)), self._c.inspect_hint, 2,
        )
        return self._inspect

    def consume_inspect(self, e: Evidence, first: FirstReceipt,
                        r: InspectReceipt) -> InspectReceipt:
        if (self._inspect_consumed or self._inspect is not r or not self._first_consumed
                or self._first is not first or e != self.e0() or r.session != e.session
                or r.first_hash != digest(asdict(first)) or r.revision != 2):
            raise ValueError("INVALID_OR_REPLAYED_INSPECTION")
        self._inspect_consumed = True
        return r

    def issue_second(
        self, e: Evidence, first: FirstReceipt, action: str,
        *, inspection: InspectReceipt | None = None,
    ) -> SecondReceipt:
        if (not self._first_consumed or self._first is not first or first.moved or
                self._second is not None or self._stopped or e != self.e0()):
            raise ValueError("UNAUTHORIZED_SECOND")
        if self._inspect is not None:
            if not self._inspect_consumed or inspection is not self._inspect:
                raise ValueError("UNCONSUMED_OR_FOREIGN_INSPECTION")
        elif inspection is not None:
            raise ValueError("UNPAID_INSPECTION_RECEIPT")
        if action == "STOP" or not viable_second(e, action, self._inspect is not None):
            raise ValueError("UNSAFE_SECOND")
        z = first.zguess if action.endswith("SAME") else 1 - first.zguess
        moved = z == self._c.z and (
            action.startswith("DETOUR") or not self._c.blocked
        )
        self._second = SecondReceipt(
            e.session, digest(asdict(first)),
            digest(asdict(inspection)) if inspection is not None else None,
            action, z, moved, 4 if inspection is not None else 3,
        )
        return self._second

    def consume_second(self, e: Evidence, first: FirstReceipt,
                       r: SecondReceipt) -> SecondReceipt:
        if (self._second_consumed or self._second is not r or self._first is not first
                or not self._first_consumed or e != self.e0()
                or r.session != e.session or r.first_hash != digest(asdict(first))
                or r.inspect_hash != (
                    digest(asdict(self._inspect)) if self._inspect else None
                ) or r.revision != (4 if self._inspect else 3)):
            raise ValueError("INVALID_OR_REPLAYED_SECOND")
        self._second_consumed = True
        return r

    def stop(self, e: Evidence, first: FirstReceipt) -> None:
        if (not self._first_consumed or self._first is not first
                or first.moved or self._second is not None
                or self._stopped or e != self.e0()):
            raise ValueError("STOP_NOT_ADMITTED")
        self._stopped = True

    def retain(self, e: Evidence, first: FirstReceipt,
               second: SecondReceipt | None, state: Belief, *, enabled: bool) -> tuple[bool, bool]:
        if (self._retained or not self._first_consumed or self._first is not first
                or e != self.e0() or (not first.moved and not self._stopped
                                      and not self._second_consumed)
                or second is not self._second):
            raise ValueError("FORGED_PREMATURE_OR_DUPLICATED_RETAIN")
        self._retained = True
        if not enabled:
            return False, False
        return state.record(e, first, second)

    def evaluator(self) -> dict:
        if not self._first_consumed or not (
            self._first.moved or self._stopped or self._second_consumed
        ):
            raise ValueError("UNFINISHED_EVALUATION")
        return {
            "hidden_z": self._c.z, "block": self._c.blocked,
            "success": self._first.moved or (
                self._second.moved if self._second_consumed else False
            ),
            "first_correct_but_blocked": (
                not self._first.moved and self._first.zguess == self._c.z
            ),
        }


def posterior(q: float, pblock: float, hint: bool | None,
              inspector: bool | None = None) -> dict[tuple[bool, bool], float]:
    weights = {
        (True, True): q * pblock,
        (False, True): (1-q) * pblock,
        (False, False): (1-q) * (1-pblock),
    }

    def lh(signal: bool | None, blocked: bool, acc: float) -> float:
        return 1 if signal is None else (
            acc if signal == blocked else 1-acc
        )

    for (match, block), prob in list(weights.items()):
        weights[(match, block)] = (
            prob * lh(hint, block, manifest()["planning"]["cheap_hint_accuracy"])
            * lh(inspector, block, manifest()["planning"]["inspection_hint_accuracy"])
        )
    total = sum(weights.values())
    if total <= 0:
        raise ValueError("UNNORMALIZABLE_BELIEF")
    return {key: val/total for key, val in weights.items()}


def expected(e: Evidence, beliefs: dict[tuple[bool, bool], float],
             inspected: bool) -> tuple[str, float]:
    scores = manifest()["planning"]["second_score"]
    best, best_value = "STOP", float(scores["stop"])
    for action in ORDER[1:]:
        if not viable_second(e, action, inspected):
            continue
        psuccess = sum(
            prob for (match, blocked), prob in beliefs.items()
            if (match if action.endswith("SAME") else not match)
            and (action.startswith("DETOUR") or not blocked)
        )
        t, w = COST[action]
        score = psuccess*scores["success"] + (1-psuccess)*scores["failure"]
        score += w*scores["per_work"] + t*scores["per_tick"]
        if score > best_value + 1e-12:
            best, best_value = action, score
    return best, best_value


def value_inspect(e: Evidence, q: float, pb: float,
                  cheap: bool | None) -> tuple[bool, str, float]:
    beliefs = posterior(q, pb, cheap)
    base_action, base_score = expected(e, beliefs, inspected=False)
    if not viable_inspect(e):
        return False, base_action, 0.0
    after = 0.0
    for signal in (False, True):
        p_signal = sum(
            prob * (manifest()["planning"]["inspection_hint_accuracy"] if signal == block
                    else 1-manifest()["planning"]["inspection_hint_accuracy"])
            for (_, block), prob in beliefs.items()
        )
        after += p_signal * expected(
            e, posterior(q, pb, cheap, inspector=signal), inspected=True
        )[1]
    t, w = COST["INSPECT"]
    costs = manifest()["planning"]["second_score"]
    gain = after + costs["per_work"]*w + costs["per_tick"]*t - base_score
    return gain > 1e-12, base_action, gain


def cheap_choice(e: Evidence, hint: bool | None, inspected: bool) -> str:
    priority = (
        ("DETOUR_SAME", "NORMAL_FLIP", "DETOUR_FLIP")
        if hint is True else
        ("NORMAL_FLIP", "DETOUR_SAME", "DETOUR_FLIP")
    )
    for action in priority:
        if viable_second(e, action, inspected):
            return action
    return "STOP"


def run(seed: int, arm: str) -> dict:
    m = manifest()
    if seed not in m["seeds"]["heldout"] + m["seeds"]["calibration"]:
        raise ValueError("UNFROZEN_SEED")
    if arm not in ARMS:
        raise ValueError("UNFROZEN_ARM")
    state = Belief()
    rows = []
    warmup_end_state = None
    block_phase_end = {}
    for c in generate(seed):
        warmup = c.epoch == "warmup"
        if not warmup and warmup_end_state is None:
            warmup_end_state = {
                "z": {str(g): list(state.z_evidence.get(g, ())) for g in (0, 1)},
                "hints": list(state.block_hints),
            }
        world = World(c)
        e = world.e0()
        first = None
        inspector = None
        second = None
        choice = "NONE"
        inspected = False
        changed = False
        was_positive_voi = False
        first_success = False
        success = False
        flip = False
        z_label = False
        pb_before = state.obstacle_rate()
        z0 = state.zposterior(e.group)[1]
        if first_viable(e):
            first = world.consume_first(e, world.issue_first(e, z0))
            first_success = first.moved
            success = first_success
            if not first_success:
                if warmup:
                    choice = cheap_choice(e, first.cheap_hint, inspected=False)
                elif arm == "EVALUATOR_ORACLE":
                    options = [a for a in ORDER if viable_second(e, a, False)]
                    scored = []
                    for action in options:
                        if action == "STOP":
                            val = -1.0
                        else:
                            z = z0 if action.endswith("SAME") else 1-z0
                            good = z == c.z and (
                                action.startswith("DETOUR") or not c.blocked
                            )
                            val = (12 if good else -6) - .6*COST[action][1] - .4*COST[action][0]
                        scored.append((val, action))
                    choice = max(scored, key=lambda pair: pair[0])[1]
                elif arm in ("FROZEN_HINT", "ADAPT_HINT", "NO_FEEDBACK_HINT"):
                    choice = cheap_choice(e, first.cheap_hint, False)
                elif arm in ("FROZEN_FLIP", "ADAPT_FLIP"):
                    choice = "NORMAL_FLIP" if viable_second(e, "NORMAL_FLIP", False) else "STOP"
                elif arm in ("ADAPT_BAYES_FIXED", "ADAPT_BAYES_BLOCK", "ADAPT_VOI_BLOCK"):
                    p1, _ = state.zposterior(e.group)
                    q = p1 if z0 else (1-p1)
                    pb = (m["planning"]["fixed_obstruction_prior"]
                          if arm == "ADAPT_BAYES_FIXED" else pb_before)
                    choice = expected(e, posterior(q, pb, first.cheap_hint), False)[0]
                    if arm == "ADAPT_VOI_BLOCK":
                        wants, _, _ = value_inspect(e, q, pb, first.cheap_hint)
                        if wants:
                            inspector = world.consume_inspect(
                                e, first, world.issue_inspect(e, first)
                            )
                            inspected = True
                            updated = expected(
                                e, posterior(q, pb, first.cheap_hint, inspector.hint), True
                            )[0]
                            changed = updated != choice
                            choice = updated
                            was_positive_voi = True
                elif arm == "ADAPT_INSPECT_SIMPLE":
                    choice = cheap_choice(e, first.cheap_hint, False)
                    if viable_inspect(e):
                        inspector = world.consume_inspect(
                            e, first, world.issue_inspect(e, first)
                        )
                        inspected = True
                        update = cheap_choice(e, inspector.hint, True)
                        changed = update != choice
                        choice = update
                else:
                    raise ValueError("UNKNOWN_ARM")
                if choice == "STOP":
                    world.stop(e, first)
                else:
                    second = world.consume_second(
                        e, first, world.issue_second(
                            e, first, choice, inspection=inspector,
                        ),
                    )
                    success = second.moved
            learn = warmup or arm not in (
                "FROZEN_HINT", "FROZEN_FLIP", "NO_FEEDBACK_HINT", "EVALUATOR_ORACLE",
            )
            z_label, flip = world.retain(e, first, second, state, enabled=learn)
            assert world.evaluator()["success"] == success
        t, w = (COST["FIRST_NORMAL"] if first is not None else (0, 0))
        if inspector is not None:
            t += COST["INSPECT"][0]
            w += COST["INSPECT"][1]
        if second is not None:
            t += COST[choice][0]
            w += COST[choice][1]
        selector = 0 if warmup or first is None or first_success else m["selector_work"][arm]
        terminal = ("SUCCESS" if success else "INITIAL_ABSTAIN" if first is None
                    else "STOP" if choice == "STOP" else "FAILED_SECOND")
        u = m["episode_utility"]
        nominal = (u["success"] if success else
                   u["initial_abstain"] if first is None else
                   u["stop"] if choice == "STOP" else u["exhausted_failure"])
        util = nominal + u["per_all_work"]*(w+selector) + u["per_world_tick"]*t
        damage = int(first is not None and not first_success)
        damage += int(second is not None and not second.moved)
        damage += int(e.threat and choice.startswith("DETOUR"))
        block_phase_end[c.epoch] = state.obstacle_rate()
        rows.append({
            "session": e.session, "epoch": c.epoch, "group": e.group,
            "first": first is not None, "first_success": first_success,
            "first_failed": first is not None and not first_success,
            "success": success, "terminal": terminal, "choice": choice,
            "inspected": inspected, "changed_action": changed,
            "positive_voi": was_positive_voi, "z_labeled": z_label,
            "map_changed": flip, "cheap_hint_admitted": (
                first is not None and first.cheap_hint is not None and learn
            ) if first is not None else False,
            "block_p_estimate": pb_before,
            "work": w, "selector": selector, "ticks": t,
            "utility_tenths": round(util*10), "damage": damage,
            "correct_first_but_blocked": (
                first is not None and world.evaluator()["first_correct_but_blocked"]
            ) if first is not None else False,
        })
    if warmup_end_state is None:
        raise AssertionError("WARMUP_ABSENT")
    phases = {}
    for epoch in m["epochs"]:
        subset = [r for r in rows if r["epoch"] == epoch]
        if len(subset) != m["n_per_epoch"]:
            raise AssertionError("EPOCH_LENGTH")
        metrics = ("first_success", "first_failed", "success", "inspected",
                   "changed_action", "positive_voi", "z_labeled", "map_changed",
                   "cheap_hint_admitted", "correct_first_but_blocked")
        phases[epoch] = {
            **{key: sum(bool(x[key]) for x in subset) for key in metrics},
            **{key: sum(x[key] for x in subset) for key in (
                "work", "selector", "ticks", "utility_tenths", "damage"
            )},
            "initial_abstain": sum(x["terminal"] == "INITIAL_ABSTAIN" for x in subset),
            "stopped": sum(x["terminal"] == "STOP" for x in subset),
            "failed_second": sum(x["terminal"] == "FAILED_SECOND" for x in subset),
            "last_block_p_estimate": round(block_phase_end[epoch], 4),
            "choices": dict(sorted(Counter(x["choice"] for x in subset).items())),
        }
    return {
        "seed": seed, "arm": arm, "warmup_state": warmup_end_state,
        "phases": phases, "trace": tuple(rows),
    }


def report() -> dict:
    m = manifest()
    results = [
        run(seed, arm)
        for seed in m["seeds"]["calibration"] + m["seeds"]["heldout"]
        for arm in ARMS
    ]
    keys = (
        "first_success", "first_failed", "success", "inspected", "changed_action",
        "positive_voi", "z_labeled", "map_changed", "cheap_hint_admitted",
        "correct_first_but_blocked", "work", "selector", "ticks",
        "utility_tenths", "damage", "initial_abstain", "stopped", "failed_second",
    )
    summary = {}
    for split, seeds in m["seeds"].items():
        summary[split] = {}
        for arm in ARMS:
            active = [r for r in results if r["seed"] in seeds and r["arm"] == arm]
            summary[split][arm] = {
                key: sum(r["phases"][epoch][key] for r in active
                         for epoch in m["epochs"][1:])
                for key in keys
            }
            summary[split][arm]["phase_success"] = {
                epoch: sum(r["phases"][epoch]["success"] for r in active)
                for epoch in m["epochs"]
            }
            summary[split][arm]["warmup_sources_identical"] = True
    paired = {}
    for seed in m["seeds"]["heldout"]:
        entries = {a: next(r for r in results if r["seed"] == seed and r["arm"] == a)
                   for a in ARMS}
        assert len({tuple(row["session"] for row in r["trace"]) for r in entries.values()}) == 1
        assert all(r["warmup_state"] == entries[ARMS[0]]["warmup_state"]
                   for r in entries.values())
        base = entries["ADAPT_HINT"]
        frozen = entries["FROZEN_HINT"]
        bayes = entries["ADAPT_BAYES_BLOCK"]
        voi = entries["ADAPT_VOI_BLOCK"]
        paired[str(seed)] = {
            "adapt_hint_minus_frozen": sum(
                base["phases"][ep]["success"] - frozen["phases"][ep]["success"]
                for ep in m["epochs"][1:]
            ),
            "bayes_block_minus_adapt_hint": sum(
                bayes["phases"][ep]["success"] - base["phases"][ep]["success"]
                for ep in m["epochs"][1:]
            ),
            "voi_minus_block": sum(
                voi["phases"][ep]["success"] - bayes["phases"][ep]["success"]
                for ep in m["epochs"][1:]
            ),
            "voi_actual_changed": sum(
                voi["phases"][ep]["changed_action"] for ep in m["epochs"][1:]
            ),
        }
    result = {"manifest_sha256": MANIFEST_SHA, "summary": summary, "paired": paired}
    result["result_sha256"] = digest(result)
    return result


if __name__ == "__main__":
    print(json.dumps(report(), sort_keys=True, ensure_ascii=False))
