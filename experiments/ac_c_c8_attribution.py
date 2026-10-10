"""AC-C C8: movement-only World outcomes with hidden independent obstruction.

An independent deterministic simulator.  No Minecraft, LLM, GPU, real energy,
physical World authentication or production owner is instantiated.
"""
from __future__ import annotations

import hashlib
import json
import random
from collections import Counter, deque
from dataclasses import asdict, dataclass, field
from pathlib import Path

MANIFEST_PATH = Path(__file__).with_name("ac_c_c8_manifest.json")
MANIFEST_SHA = "be4cb30a19bc2bf5ae773ec2d3bbedad03b9ff981246e772bfcf57b4e9a6fa15"
ARMS = (
    "FROZEN_MAP", "NAIVE_BLAME", "SUCCESS_ONLY", "SENSOR_HEURISTIC",
    "CAUSAL_BAYES", "CAUSAL_NO_SENSOR", "PROBE_FIRST", "EVALUATOR_ORACLE",
)
COST = {"CHEAP": (1, 1), "PROBE": (3, 5)}


def canonical_hash(x: object) -> str:
    return hashlib.sha256(
        json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def config() -> dict:
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if canonical_hash(data) != MANIFEST_SHA:
        raise ValueError("C8_MANIFEST_DRIFT")
    return data


@dataclass(frozen=True)
class Case:
    session: str
    epoch: str
    group: int
    prefix: int
    hidden_z: int
    obstructed: bool
    obstacle_hint: bool | None
    deadline: int
    health: int
    hunger: int
    threat: bool
    probe_available: bool

    @property
    def target(self) -> int:
        return (self.prefix.bit_count() & 1) ^ self.hidden_z


@dataclass(frozen=True)
class Evidence:
    session: str
    revision: int
    group: int
    prefix: int
    deadline: int
    health: int
    hunger: int
    threat: bool
    probe_available: bool


@dataclass(frozen=True)
class Receipt:
    session: str
    e0_digest: str
    mode: str
    selected_action: int
    moved: bool
    obstacle_hint: bool | None
    probe_z: int | None
    terminal_revision: int


def generate(seed: int) -> tuple[Case, ...]:
    m = config()
    rng = random.Random(seed)
    cases = []
    for ep in m["epochs"]:
        for i in range(m["episode_counts"][ep]):
            group = rng.randrange(2)
            z = int(rng.random() < m["hidden_z_probability_1"][ep][group])
            obstructed = rng.random() < m["independent_obstruction_probability"][ep]
            hint = None
            if rng.random() < m["world"]["obstacle_hint_presence"]:
                hint = (obstructed if rng.random() < m["world"]["obstacle_hint_accuracy"]
                        else not obstructed)
            cases.append(Case(
                f"c8:{seed}:{ep}:{i}", ep, group, rng.randrange(4), z, obstructed,
                hint, rng.choice(m["world"]["deadline_values"]),
                rng.choice(m["world"]["health_values"]),
                rng.choice(m["world"]["hunger_values"]),
                rng.random() < m["world"]["threat_probability"],
                rng.random() < m["world"]["probe_available"],
            ))
    return tuple(cases)


def viable(e: Evidence, mode: str) -> bool:
    if e.revision != 0 or mode not in COST or COST[mode][0] > e.deadline:
        return False
    if mode == "PROBE" and (not e.probe_available or e.hunger <= 2):
        return False
    max_exposure = int(e.threat and COST[mode][0] >= 3)
    max_wrong_damage = 2 if mode == "CHEAP" else 0
    return e.health > max_wrong_damage + max_exposure


class World:
    def __init__(self, case: Case):
        self._case = case
        self._issued: Receipt | None = None
        self._consumed = False
        self._retained = False
        self._valid_decision: bool | None = None

    def e0(self) -> Evidence:
        c = self._case
        return Evidence(c.session, 0, c.group, c.prefix, c.deadline, c.health,
                        c.hunger, c.threat, c.probe_available)

    def issue(self, e: Evidence, mode: str, *, predicted_z: int = 0) -> Receipt:
        if self._issued is not None:
            raise ValueError("DUPLICATE_WORLD_TERMINAL")
        if e != self.e0():
            raise ValueError("FOREIGN_OR_STALE_E0")
        if not viable(e, mode):
            raise ValueError("UNADMITTED_ACTION")
        if predicted_z not in (0, 1) or (mode != "CHEAP" and predicted_z != 0):
            raise ValueError("UNPAID_EVALUATOR_TRUTH")
        z = predicted_z if mode == "CHEAP" else self._case.hidden_z
        action = (e.prefix.bit_count() & 1) ^ z
        self._valid_decision = action == self._case.target
        moved = bool(self._valid_decision and not self._case.obstructed)
        self._issued = Receipt(
            e.session, canonical_hash(asdict(e)), mode, action, moved,
            self._case.obstacle_hint, self._case.hidden_z if mode == "PROBE" else None,
            1 if mode == "CHEAP" else 2,
        )
        return self._issued

    def consume(self, e: Evidence, r: Receipt, mode: str) -> Receipt:
        if (self._consumed or self._issued is not r or e != self.e0()
                or r.session != e.session or r.e0_digest != canonical_hash(asdict(e))
                or r.mode != mode
                or r.terminal_revision != (1 if mode == "CHEAP" else 2)):
            raise ValueError("INVALID_OR_REPLAYED_WORLD_RECEIPT")
        self._consumed = True
        return r

    def retain(self, e: Evidence, r: Receipt, state: PolicyState,
               arm: str, *, warmup: bool) -> bool:
        if (self._retained or not self._consumed or self._issued is not r
                or e != self.e0() or arm not in ARMS):
            raise ValueError("UNATTESTED_OR_DUPLICATED_LEARNING")
        self._retained = True
        if not warmup and arm in ("FROZEN_MAP", "EVALUATOR_ORACLE"):
            return False
        return state.update(e, r, arm=arm, warmup=warmup)

    def evaluate(self) -> tuple[bool, bool, int, int, bool]:
        """Evaluator-only; never an input to any normal selector or retention."""
        if not self._consumed or self._valid_decision is None:
            raise ValueError("NO_CONSUMED_ACTION")
        c = self._case
        exposure = int(c.threat and COST[self._issued.mode][0] >= 3)
        damage = int(not self._valid_decision) * 2 + exposure
        return self._valid_decision, self._issued.moved, damage, exposure, c.obstructed


@dataclass
class PolicyState:
    z_probability: dict[int, deque[float]] = field(default_factory=dict)

    def posterior(self, group: int) -> tuple[float, int]:
        hist = self.z_probability.get(group, ())
        p1 = (1 + sum(hist)) / (2 + len(hist))
        return p1, int(p1 > .5)

    def add(self, group: int, probability_z1: float) -> None:
        if not 0 <= probability_z1 <= 1:
            raise ValueError("UNBOUNDED_BELIEF_UPDATE")
        self.z_probability.setdefault(group, deque(maxlen=12)).append(probability_z1)

    def update(self, e: Evidence, receipt: Receipt, *, arm: str,
               warmup: bool) -> bool:
        before = self.posterior(e.group)[1]
        executed_z = receipt.selected_action ^ (e.prefix.bit_count() & 1)
        if receipt.mode == "PROBE":
            if receipt.probe_z not in (0, 1):
                raise ValueError("UNSOURCED_PAID_OBSERVATION")
            self.add(e.group, float(receipt.probe_z))
        elif receipt.moved:
            # The action cannot have moved when z does not match it.
            self.add(e.group, float(executed_z))
        elif not warmup and arm == "NAIVE_BLAME":
            # Explicit fallacious scientific control: no movement != wrong.
            self.add(e.group, float(1 - executed_z))
        elif not warmup and arm == "SENSOR_HEURISTIC":
            if receipt.obstacle_hint is not True:
                self.add(e.group, float(1 - executed_z))
        elif not warmup and arm in ("CAUSAL_BAYES", "CAUSAL_NO_SENSOR"):
            # A failed action has two explanations: incorrect intended action
            # or a correct action blocked by an independent obstacle.
            prior_p1, _ = self.posterior(e.group)
            q_correct = prior_p1 if executed_z else 1 - prior_p1
            pb = config()["learners"]["assumed_obstruction_prior"]
            hint = receipt.obstacle_hint if arm == "CAUSAL_BAYES" else None
            acc = config()["learners"]["hint_accuracy_assumed"]

            def hint_likelihood(blocked: bool) -> float:
                if hint is None:
                    return 1.0
                return acc if hint == blocked else 1.0 - acc

            l_match = pb * hint_likelihood(True)
            l_mismatch = pb * hint_likelihood(True) + (1 - pb) * hint_likelihood(False)
            denom = q_correct * l_match + (1 - q_correct) * l_mismatch
            posterior_match = (q_correct * l_match / denom) if denom else 0.5
            p1 = posterior_match if executed_z == 1 else (1 - posterior_match)
            self.add(e.group, p1)
        # SUCCESS_ONLY, PROBE_FIRST, shared WARMUP, etc ignore failures.
        return before != self.posterior(e.group)[1]


def select(e: Evidence, arm: str, state: PolicyState,
           *, warmup: bool) -> tuple[str, int]:
    if arm not in ARMS:
        raise ValueError("UNKNOWN_POLICY_ARM")
    if not warmup and arm == "EVALUATOR_ORACLE":
        raise ValueError("EVALUATOR_PRIVILEGE_NOT_SOURCE_ADMITTED")
    if (warmup or arm == "PROBE_FIRST") and viable(e, "PROBE"):
        return "PROBE", 0
    if viable(e, "CHEAP"):
        return "CHEAP", state.posterior(e.group)[1]
    return "ABSTAIN", 0


def trajectory(seed: int, arm: str) -> dict:
    m = config()
    if seed not in m["seeds"]["calibration"] + m["seeds"]["heldout"]:
        raise ValueError("UNFROZEN_SEED")
    if arm not in ARMS:
        raise ValueError("UNFROZEN_ARM")
    state = PolicyState()
    records = []
    for c in generate(seed):
        world = World(c)
        e = world.e0()
        warmup = c.epoch == "warmup"
        if not warmup and arm == "EVALUATOR_ORACLE":
            if viable(e, "CHEAP"):
                mode, bit, free_oracle = "CHEAP", c.hidden_z, True
            else:
                # No ordinary selector receives hidden facts, including oracle.
                mode, bit, free_oracle = ("PROBE", 0, False) if viable(e, "PROBE") else (
                    "ABSTAIN", 0, False
                )
        else:
            mode, bit = select(e, arm, state, warmup=warmup)
            free_oracle = False
        flipped = False
        if mode == "ABSTAIN":
            correct, moved, damage, exposure, blocked = None, False, 0, 0, None
            revision = None
        elif free_oracle:
            # Evaluator-only free z upper bound, NOT World authority or receipt.
            correct, moved, damage, exposure, blocked = (
                True, not c.obstructed, 0, 0, c.obstructed
            )
            revision = 1
        else:
            r = world.consume(e, world.issue(e, mode, predicted_z=bit), mode)
            flipped = world.retain(e, r, state, arm, warmup=warmup)
            correct, moved, damage, exposure, blocked = world.evaluate()
            revision = r.terminal_revision
        ticks, work = COST.get(mode, (0, 0))
        overhead = 0 if warmup else m["selector_overhead"][arm]
        weights = m["objective"]
        utility = (weights["correct_decision"] if correct is True else
                   weights["wrong_decision"] if correct is False else
                   weights["abstain"])
        utility += weights["per_mechanism_and_selector_work"] * (work + overhead)
        utility += weights["per_world_tick"] * ticks
        records.append({
            "session": e.session, "epoch": c.epoch, "group": e.group,
            "mode": mode, "correct_decision": correct,
            "moved": moved, "decision_correct_but_blocked": correct is True and not moved,
            "observed_hint": c.obstacle_hint if mode != "ABSTAIN" else None,
            "hint_reported": mode != "ABSTAIN" and c.obstacle_hint is not None,
            "blocked_for_evaluator_only": blocked,
            "damage": damage, "exposure": exposure, "ticks": ticks,
            "mechanism_work": work, "selector_work": overhead,
            "utility_tenths": round(utility * 10),
            "changed_map": flipped, "receipt_revision": revision,
        })
    phases = {}
    for ep in m["epochs"]:
        rows = [x for x in records if x["epoch"] == ep]
        if len(rows) != m["episode_counts"][ep]:
            raise AssertionError("EPOCH_LENGTH_MISMATCH")
        phases[ep] = {
            "correct": sum(x["correct_decision"] is True for x in rows),
            "wrong": sum(x["correct_decision"] is False for x in rows),
            "abstain": sum(x["correct_decision"] is None for x in rows),
            "moved": sum(x["moved"] for x in rows),
            "correct_but_blocked": sum(x["decision_correct_but_blocked"] for x in rows),
            "hints": sum(x["hint_reported"] for x in rows),
            "map_flips": sum(x["changed_map"] for x in rows),
            "mechanism_work": sum(x["mechanism_work"] for x in rows),
            "selector_work": sum(x["selector_work"] for x in rows),
            "ticks": sum(x["ticks"] for x in rows),
            "damage": sum(x["damage"] for x in rows),
            "utility_tenths": sum(x["utility_tenths"] for x in rows),
            "mode_counts": dict(sorted(Counter(x["mode"] for x in rows).items())),
        }
    return {"seed": seed, "arm": arm, "phases": phases, "trace": tuple(records)}


def report() -> dict:
    m = config()
    records = [
        trajectory(seed, arm)
        for seed in m["seeds"]["calibration"] + m["seeds"]["heldout"]
        for arm in ARMS
    ]
    summary = {}
    measure_keys = (
        "correct", "wrong", "abstain", "moved", "correct_but_blocked",
        "hints", "map_flips", "mechanism_work", "selector_work",
        "ticks", "damage", "utility_tenths",
    )
    for split, seeds in m["seeds"].items():
        summary[split] = {}
        for arm in ARMS:
            rr = [x for x in records if x["seed"] in seeds and x["arm"] == arm]
            summary[split][arm] = {
                k: sum(row["phases"][ep][k] for row in rr for ep in m["epochs"][1:])
                for k in measure_keys
            }
    phases = {
        arm: {
            ep: {
                k: sum(row["phases"][ep][k] for row in records
                       if row["seed"] in m["seeds"]["heldout"] and row["arm"] == arm)
                for k in measure_keys
            } for ep in m["epochs"]
        } for arm in ARMS
    }
    pairs = {}
    for seed in m["seeds"]["heldout"]:
        rr = {arm: next(x for x in records if x["seed"] == seed and x["arm"] == arm)
              for arm in ARMS}
        assert len({tuple(row["session"] for row in x["trace"]) for x in rr.values()}) == 1
        pairs[str(seed)] = {
            "causal_minus_success_only_correct": sum(
                rr["CAUSAL_BAYES"]["phases"][ep]["correct"] -
                rr["SUCCESS_ONLY"]["phases"][ep]["correct"]
                for ep in m["epochs"][1:]
            ),
            "causal_minus_sensor_heuristic_correct": sum(
                rr["CAUSAL_BAYES"]["phases"][ep]["correct"] -
                rr["SENSOR_HEURISTIC"]["phases"][ep]["correct"]
                for ep in m["epochs"][1:]
            ),
            "block_only_naive_flips": rr["NAIVE_BLAME"]["phases"]["block_only"]["map_flips"],
            "block_only_causal_flips": rr["CAUSAL_BAYES"]["phases"]["block_only"]["map_flips"],
        }
    result = {"manifest_sha256": MANIFEST_SHA,
              "summaries": summary, "heldout_phases": phases, "paired": pairs}
    result["result_sha256"] = canonical_hash(result)
    return result


if __name__ == "__main__":
    print(json.dumps(report(), sort_keys=True, ensure_ascii=False))
