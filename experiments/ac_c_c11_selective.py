"""C11: source-learned predictive confidence and selective internal decoding.

All detailed cues are PUBLIC at E0. L2_ANALYTIC is charged mathematical
computation over E0, NOT a new World observation, LLM or physical inference.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import math
import random
from collections import Counter, deque
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path

MANIFEST = Path(__file__).with_name("ac_c_c11_manifest.json")
MANIFEST_SHA = "8245f1458ae17fe3db5633726e6d9e6c6114ac8e3b7ab43e3ea1f962537605c9"
ARMS = (
    "FROZEN_GROUP", "ADAPT_GROUP", "L1_FIRST_CUE", "L1_MAJORITY",
    "ALWAYS_L2", "CONFIDENCE_GATE", "VALUE_GATE", "CONFLICT_GATE",
    "NO_FEEDBACK_GROUP", "EVALUATOR_ORACLE",
)
COST = {
    "L1_GROUP": (1, 1),
    "L1_FIRST": (1, 1),
    "L1_MAJORITY": (1, 2),
    "L2_BAYES": (3, 6),
    "ABSTAIN": (0, 0),
}


def hash_obj(value: object) -> str:
    return hashlib.sha256(json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()).hexdigest()


@lru_cache(maxsize=1)
def config() -> dict:
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if hash_obj(m) != MANIFEST_SHA:
        raise ValueError("FROZEN_MANIFEST_DRIFT")
    return m


@dataclass(frozen=True)
class HiddenCase:
    session: str
    epoch: str
    group: int
    prefix: int
    public_cues: tuple[int, int, int]
    hidden_z: int
    obstructed: bool
    exact_available: bool
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
    public_cues: tuple[int, int, int]
    deadline: int
    health: int
    hunger: int
    threat: bool


@dataclass(frozen=True)
class TerminalReceipt:
    session: str
    evidence_digest: str
    mode: str
    selected_action: int
    moved: bool
    label_kind: str
    label_z: int | None
    revision: int


def generate(seed: int) -> tuple[HiddenCase, ...]:
    m = config()
    rng = random.Random(seed)
    rows = []
    for epoch in m["epochs"]:
        for i in range(m["episodes_per_epoch"]):
            group = rng.randrange(2)
            z = int(rng.random() < m["hidden_z_p1"][epoch][group])
            reliability = m["public_cue_reliability"][epoch]
            bits = tuple(
                z if rng.random() < reliability else 1-z
                for _ in range(m["world"]["public_bits"])
            )
            rows.append(HiddenCase(
                f"c11:{seed}:{epoch}:{i}", epoch, group, rng.randrange(4),
                bits, z, rng.random() < m["world"]["independent_obstruction_p"],
                rng.random() < m["world"]["terminal_exact_z_probability"],
                rng.choice(m["world"]["deadline_values"]),
                rng.choice(m["world"]["health_values"]),
                rng.choice(m["world"]["hunger_values"]),
                rng.random() < m["world"]["threat_p"],
            ))
    return tuple(rows)


def viable(e: Evidence, mode: str) -> bool:
    if mode not in COST or mode == "ABSTAIN" or e.revision != 0:
        return False
    if e.deadline < COST[mode][0] or e.health <= 2:
        return False
    if mode == "L2_BAYES" and (
        e.hunger <= 2 or e.health <= (3 if e.threat else 2)
    ):
        return False
    return True


@dataclass
class Learned:
    history: dict[int, deque[int]] = field(default_factory=dict)
    source_sessions: set[str] = field(default_factory=set)

    def posterior(self, group: int) -> tuple[float, int]:
        hist = self.history.get(group, ())
        p1 = (1 + sum(hist)) / (2 + len(hist))
        return p1, int(p1 > 0.5)

    def accept(self, e: Evidence, receipt: TerminalReceipt) -> bool:
        if e.session in self.source_sessions:
            raise ValueError("DUPLICATE_SOURCE_TRAINING")
        self.source_sessions.add(e.session)
        if receipt.label_kind == "MISSING":
            if receipt.label_z is not None:
                raise ValueError("MISSING_LABEL_SPOOF")
            return False
        if receipt.label_kind != "EXACT" or receipt.label_z not in (0, 1):
            raise ValueError("FAKE_TYPED_FEEDBACK")
        self.history.setdefault(e.group, deque(
            maxlen=config()["learning"]["window_per_group"]
        )).append(receipt.label_z)
        return True


class World:
    """Mints one final receipt. Source trust is local Python object identity."""

    def __init__(self, case: HiddenCase):
        self._case = case
        self._issued: TerminalReceipt | None = None
        self._consumed = False
        self._retained = False
        self._chosen_z: int | None = None

    def e0(self) -> Evidence:
        c = self._case
        return Evidence(
            c.session, 0, c.group, c.prefix, c.public_cues,
            c.deadline, c.health, c.hunger, c.threat,
        )

    def issue(self, e: Evidence, mode: str, zguess: int) -> TerminalReceipt:
        if self._issued is not None:
            raise ValueError("DUPLICATE_ISSUED_ACTION")
        if e != self.e0() or not viable(e, mode) or zguess not in (0, 1):
            raise ValueError("ACTION_NOT_ADMITTED")
        self._chosen_z = zguess
        correct = zguess == self._case.hidden_z
        action = (e.prefix.bit_count() & 1) ^ zguess
        self._issued = TerminalReceipt(
            e.session, hash_obj(asdict(e)), mode, action,
            correct and not self._case.obstructed,
            "EXACT" if self._case.exact_available else "MISSING",
            self._case.hidden_z if self._case.exact_available else None, 1,
        )
        return self._issued

    def consume(self, e: Evidence, mode: str,
                r: TerminalReceipt) -> TerminalReceipt:
        if (self._consumed or r is not self._issued or e != self.e0()
                or r.session != e.session or r.evidence_digest != hash_obj(asdict(e))
                or r.mode != mode or r.revision != 1):
            raise ValueError("FORGED_STALE_OR_REPLAYED_TERMINAL")
        self._consumed = True
        return r

    def retain(self, e: Evidence, r: TerminalReceipt,
               state: Learned, enabled: bool) -> bool:
        if (self._retained or not self._consumed or r is not self._issued
                or e != self.e0()):
            raise ValueError("UNCONSUMED_OR_DUPLICATE_RETENTION")
        self._retained = True
        if not enabled:
            return False
        return state.accept(e, r)

    def evaluate(self) -> dict:
        """Evaluator-only, never used inside an ordinary arm's policy."""
        if not self._consumed or self._chosen_z is None:
            raise ValueError("NO_TERMINAL_WORLD_RESULT")
        return {
            "correct": self._chosen_z == self._case.hidden_z,
            "moved": self._issued.moved,
            "blocked": self._case.obstructed,
        }


def deep_bit(p1: float, bits: tuple[int, int, int]) -> int:
    reliability = config()["compute"]["nominal_public_cue_reliability"]
    log_odds = math.log(p1 / (1-p1))
    log_ratio = math.log(reliability / (1-reliability))
    log_odds += sum((1 if bit == 1 else -1)*log_ratio for bit in bits)
    return int(log_odds > 0)


def expected_deep_accuracy(p1: float) -> float:
    reliability = config()["compute"]["nominal_public_cue_reliability"]
    total = 0.0
    for bits in itertools.product((0, 1), repeat=3):
        for z, prior in ((0, 1-p1), (1, p1)):
            likelihood = math.prod(
                reliability if bit == z else 1-reliability for bit in bits
            )
            if deep_bit(p1, bits) == z:
                total += prior*likelihood
    return total


def value_of_compute(p1: float) -> float:
    scores = config()["objective"]
    learn_gain = expected_deep_accuracy(p1)-max(p1, 1-p1)
    deep_t, deep_w = COST["L2_BAYES"]
    cheap_t, cheap_w = COST["L1_GROUP"]
    return (scores["correct"]-scores["wrong"])*learn_gain + (
        scores["per_combined_work"]*(deep_w-cheap_w)
        + scores["per_tick"]*(deep_t-cheap_t)
    )


def select(e: Evidence, state: Learned, arm: str,
           *, warmup: bool) -> tuple[str, int]:
    if arm not in ARMS:
        raise ValueError("UNFROZEN_POLICY")
    if not viable(e, "L1_GROUP"):
        return "ABSTAIN", 0
    p1, learned_bit = state.posterior(e.group)
    if warmup or arm in ("FROZEN_GROUP", "ADAPT_GROUP", "NO_FEEDBACK_GROUP"):
        return "L1_GROUP", learned_bit
    if arm == "L1_FIRST_CUE":
        return "L1_FIRST", e.public_cues[0]
    if arm == "L1_MAJORITY":
        return "L1_MAJORITY", int(sum(e.public_cues) >= 2)
    if arm == "EVALUATOR_ORACLE":
        raise ValueError("EVALUATOR_CANNOT_ENTER_SOURCE_SELECTOR")
    use_deep = viable(e, "L2_BAYES") and (
        arm == "ALWAYS_L2"
        or (arm == "CONFIDENCE_GATE" and max(p1, 1-p1) < config()["policies"]["threshold_confidence"])
        or (arm == "VALUE_GATE" and value_of_compute(p1) > 1e-12)
        or (arm == "CONFLICT_GATE" and (
            e.public_cues[0] != learned_bit
            or max(p1, 1-p1) < config()["policies"]["threshold_confidence"]
        ))
    )
    if use_deep:
        return "L2_BAYES", deep_bit(p1, e.public_cues)
    return "L1_GROUP", learned_bit


def trajectory(seed: int, arm: str) -> dict:
    c = config()
    if seed not in c["seeds"]["calibration"] + c["seeds"]["heldout"]:
        raise ValueError("UNFROZEN_SEED")
    if arm not in ARMS:
        raise ValueError("UNFROZEN_ARM")
    state = Learned()
    rows = []
    warmup_snapshot = None
    for case in generate(seed):
        warmup = case.epoch == "warmup"
        if not warmup and warmup_snapshot is None:
            warmup_snapshot = {
                str(g): tuple(state.history.get(g, ())) for g in (0, 1)
            }
        world = World(case)
        e = world.e0()
        oracle = arm == "EVALUATOR_ORACLE" and not warmup and viable(e, "L1_GROUP")
        if oracle:
            mode, zguess = "L1_GROUP", case.hidden_z
        else:
            mode, zguess = select(e, state, arm, warmup=warmup)
        p1_before, _ = state.posterior(e.group)
        old_map = state.posterior(e.group)[1]
        admitted_label = False
        decision_correct = None
        moved = False
        if mode != "ABSTAIN":
            terminal = world.consume(e, mode, world.issue(e, mode, zguess))
            admitted_label = world.retain(
                e, terminal, state,
                enabled=(warmup or arm not in (
                    "FROZEN_GROUP", "NO_FEEDBACK_GROUP", "EVALUATOR_ORACLE"
                )),
            )
            # Privileged evaluator called AFTER World retention, never to adapt
            # or to choose a source-normal policy.
            eval_row = world.evaluate()
            decision_correct = eval_row["correct"]
            moved = eval_row["moved"]
        t, w = COST[mode]
        selector_work = 0 if warmup or mode == "ABSTAIN" else c["policies"]["selector_work"][arm]
        utility = (
            c["objective"]["correct"] if decision_correct is True
            else c["objective"]["wrong"] if decision_correct is False
            else c["objective"]["abstain"]
        )
        utility += c["objective"]["per_combined_work"]*(w+selector_work)
        utility += c["objective"]["per_tick"]*t
        rows.append({
            "session": e.session, "epoch": case.epoch, "mode": mode,
            "public_bits": e.public_cues, "group": e.group,
            "prediction": zguess if mode != "ABSTAIN" else None,
            "correct": decision_correct, "moved": moved,
            "retained_exact": admitted_label,
            "confidence_prior": round(max(p1_before, 1-p1_before), 6),
            "map_changed": old_map != state.posterior(e.group)[1],
            "work": w, "selector_work": selector_work, "ticks": t,
            "utility_tenths": round(10*utility),
        })
    if warmup_snapshot is None:
        raise AssertionError("MISSING_WARMUP")
    phases = {}
    for ep in c["epochs"]:
        part = [x for x in rows if x["epoch"] == ep]
        assert len(part) == c["episodes_per_epoch"]
        phases[ep] = {
            "correct": sum(x["correct"] is True for x in part),
            "wrong": sum(x["correct"] is False for x in part),
            "abstain": sum(x["correct"] is None for x in part),
            "moved": sum(x["moved"] for x in part),
            "exact_admissions": sum(x["retained_exact"] for x in part),
            "map_changes": sum(x["map_changed"] for x in part),
            "deep_count": sum(x["mode"] == "L2_BAYES" for x in part),
            "work": sum(x["work"] for x in part),
            "selector_work": sum(x["selector_work"] for x in part),
            "ticks": sum(x["ticks"] for x in part),
            "utility_tenths": sum(x["utility_tenths"] for x in part),
            "mode_counts": dict(sorted(Counter(x["mode"] for x in part).items())),
        }
    return {"seed": seed, "arm": arm, "warmup_state": warmup_snapshot,
            "phases": phases, "trace": tuple(rows)}


def report() -> dict:
    m = config()
    results = [
        trajectory(seed, arm)
        for seed in m["seeds"]["calibration"] + m["seeds"]["heldout"]
        for arm in ARMS
    ]
    summary = {}
    keys = (
        "correct", "wrong", "abstain", "moved", "exact_admissions",
        "map_changes", "deep_count", "work", "selector_work",
        "ticks", "utility_tenths",
    )
    for split, seeds in m["seeds"].items():
        summary[split] = {}
        for arm in ARMS:
            chosen = [r for r in results if r["seed"] in seeds and r["arm"] == arm]
            summary[split][arm] = {
                k: sum(r["phases"][ep][k] for r in chosen for ep in m["epochs"][1:])
                for k in keys
            }
            summary[split][arm]["phase_correct"] = {
                ep: sum(r["phases"][ep]["correct"] for r in chosen) for ep in m["epochs"]
            }
            summary[split][arm]["warmup_identical"] = True
    pairs = {}
    for seed in m["seeds"]["heldout"]:
        r = {a: next(v for v in results if v["arm"] == a and v["seed"] == seed)
             for a in ARMS}
        assert len({tuple(x["session"] for x in v["trace"]) for v in r.values()}) == 1
        assert all(v["warmup_state"] == r[ARMS[0]]["warmup_state"]
                   for v in r.values())
        after = m["epochs"][1:]
        pairs[str(seed)] = {
            "adapt_minus_frozen": sum(r["ADAPT_GROUP"]["phases"][ep]["correct"] -
                                      r["FROZEN_GROUP"]["phases"][ep]["correct"]
                                      for ep in after),
            "value_minus_majority": sum(r["VALUE_GATE"]["phases"][ep]["correct"] -
                                        r["L1_MAJORITY"]["phases"][ep]["correct"]
                                        for ep in after),
            "value_minus_adapt": sum(r["VALUE_GATE"]["phases"][ep]["correct"] -
                                     r["ADAPT_GROUP"]["phases"][ep]["correct"]
                                     for ep in after),
            "value_deep": sum(r["VALUE_GATE"]["phases"][ep]["deep_count"] for ep in after),
        }
    result = {"manifest_sha256": MANIFEST_SHA, "summaries": summary, "paired": pairs}
    result["result_sha256"] = hash_obj(result)
    return result


if __name__ == "__main__":
    print(json.dumps(report(), sort_keys=True, ensure_ascii=False))
