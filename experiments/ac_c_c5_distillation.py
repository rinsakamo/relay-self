"""C5 independent offline causal resource selection and bounded compilation.

Model/GPU/Minecraft never called. The paid modes purchase World information;
none represents actual LLM cognitive depth or electrical power consumption.
"""
from __future__ import annotations

import hashlib
import json
import random
from collections import Counter, deque
from dataclasses import asdict, dataclass, field
from pathlib import Path

MANIFEST = Path(__file__).with_name("ac_c_c5_manifest.json")
MANIFEST_SHA = "dbedfa52a30411a7443daa97a077553f079a58481e477193800a638fc9af3452"
MODES = ("CHEAP", "MEDIUM", "SCAN", "DEEP")
ARMS = (
    "STATIC_ZERO", "CHEAP_HISTORY", "STATIC_DIAGNOSTIC", "SIMPLE_GATE",
    "RESOURCE_BAYES", "RESOURCE_NO_FEEDBACK", "CACHE_COMPILED", "EVALUATOR_ORACLE",
)
COST = {"CHEAP": (1, 1), "MEDIUM": (2, 2), "SCAN": (3, 5), "DEEP": (5, 8)}


def canonical_hash(obj: object) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def config() -> dict:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if canonical_hash(manifest) != MANIFEST_SHA:
        raise ValueError("C5_FROZEN_MANIFEST_MISMATCH")
    return manifest


@dataclass(frozen=True)
class Case:
    session: str
    phase: str
    group: int
    prefix: int
    latent_z: int
    medium_hint: int
    deadline: int
    health: int
    hunger: int
    threat: bool
    scan_available: bool

    @property
    def target(self) -> int:
        return (self.prefix.bit_count() & 1) ^ self.latent_z


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
    scan_available: bool


@dataclass(frozen=True)
class Receipt:
    session: str
    source_digest: str
    mode: str
    action: int
    observed_target: int
    success: bool
    damage: int
    exposure: int
    terminal_revision: int


def cases(seed: int) -> tuple[Case, ...]:
    m = config()
    rng = random.Random(seed)
    out = []
    for phase in m["phases"]:
        for i in range(m["episodes_per_phase"]):
            group = rng.randrange(2)
            latent = int(rng.random() < m["latent_probability_z1"][phase][group])
            hint = latent if rng.random() < m["world"]["medium_hint_accuracy"] else 1 - latent
            out.append(Case(
                session=f"c5:{seed}:{phase}:{i}", phase=phase,
                group=group, prefix=rng.randrange(4), latent_z=latent,
                medium_hint=hint, deadline=rng.choice(m["world"]["deadlines"]),
                health=rng.choice(m["world"]["health"]),
                hunger=rng.choice(m["world"]["hunger"]),
                threat=rng.random() < m["world"]["threat_probability"],
                scan_available=rng.random() < m["world"]["scan_available_probability"],
            ))
    return tuple(out)


def viable(e: Evidence, mode: str) -> bool:
    if mode not in MODES:
        return False
    ticks = COST[mode][0]
    if ticks > e.deadline or (mode == "SCAN" and not e.scan_available):
        return False
    if mode == "DEEP" and e.hunger <= 2:
        return False
    exposure = int(e.threat and ticks >= 3)
    damage = 0 if mode in ("SCAN", "DEEP") else 2
    return e.health > exposure + damage


class World:
    """One World decision; only consumed issued receipt permits retained update."""

    def __init__(self, case: Case):
        self._case = case
        self._receipt: Receipt | None = None
        self._consumed = False
        self._learned = False

    def evidence(self) -> Evidence:
        c = self._case
        return Evidence(
            c.session, 0, c.group, c.prefix, c.deadline,
            c.health, c.hunger, c.threat, c.scan_available,
        )

    def issue(self, e: Evidence, mode: str, z_guess: int = 0) -> Receipt:
        if self._receipt is not None:
            raise ValueError("DUPLICATE_ISSUE")
        if e != self.evidence() or e.revision != 0:
            raise ValueError("FOREIGN_OR_STALE_EVIDENCE")
        if not viable(e, mode):
            raise ValueError("UNAUTHORIZED_MODE")
        if z_guess not in (0, 1) or (z_guess and mode != "CHEAP"):
            raise ValueError("UNPAID_LATENT_INFORMATION")
        observed_z = (
            z_guess if mode == "CHEAP"
            else self._case.medium_hint if mode == "MEDIUM"
            else self._case.latent_z
        )
        action = (e.prefix.bit_count() & 1) ^ observed_z
        correct = action == self._case.target
        exposure = int(e.threat and COST[mode][0] >= 3)
        damage = 2 * int(not correct) + exposure
        self._receipt = Receipt(
            e.session, canonical_hash(asdict(e)), mode, action,
            self._case.target, correct, damage, exposure,
            1 if mode == "CHEAP" else 2,
        )
        return self._receipt

    def consume(self, e: Evidence, receipt: Receipt, mode: str) -> Receipt:
        if (
            self._consumed or self._receipt is not receipt or
            e != self.evidence() or receipt.session != e.session or
            receipt.source_digest != canonical_hash(asdict(e)) or
            receipt.mode != mode or receipt.terminal_revision != (
                1 if mode == "CHEAP" else 2
            )
        ):
            raise ValueError("INVALID_OR_REPLAYED_OUTCOME")
        self._consumed = True
        return receipt

    def retain(self, e: Evidence, receipt: Receipt, state: State, arm: str) -> None:
        if (
            not self._consumed or self._learned or self._receipt is not receipt
            or e != self.evidence()
        ):
            raise ValueError("UNCONSUMED_OR_DUPLICATED_FEEDBACK")
        self._learned = True
        if arm in ("RESOURCE_NO_FEEDBACK", "STATIC_ZERO", "STATIC_DIAGNOSTIC"):
            return
        if arm not in ("CHEAP_HISTORY", "SIMPLE_GATE", "RESOURCE_BAYES", "CACHE_COMPILED"):
            raise ValueError("UNAUTHORIZED_LEARNING_ARM")
        z = receipt.observed_target ^ (e.prefix.bit_count() & 1)
        state.history.setdefault(e.group, deque(maxlen=12)).append(z)


@dataclass
class State:
    history: dict[int, deque[int]] = field(default_factory=dict)
    cache: dict[tuple, tuple[str, int]] = field(default_factory=dict)

    def counts(self, group: int) -> tuple[int, int]:
        recent = self.history.get(group, ())
        return sum(recent), len(recent)

    def posterior(self, group: int) -> tuple[float, int]:
        ones, n = self.counts(group)
        p_z1 = (ones + 1) / (n + 2)
        return max(p_z1, 1 - p_z1), int(p_z1 > 0.5)


def cheapest(e: Evidence, priority: tuple[str, ...]) -> tuple[str, int]:
    for mode in priority:
        if viable(e, mode):
            return mode, 0
    return "ABSTAIN", 0


def bayes_decision(e: Evidence, state: State) -> tuple[str, int]:
    m = config()
    qcheap, z = state.posterior(e.group)
    quality = {"CHEAP": qcheap, "MEDIUM": m["world"]["medium_hint_accuracy"],
               "SCAN": 1.0, "DEEP": 1.0}
    weights = m["objective"]
    options = [("ABSTAIN", 0, weights["abstain"])]
    for mode in MODES:
        if not viable(e, mode):
            continue
        ticks, work = COST[mode]
        q = quality[mode]
        payoff = (
            weights["correct"] * q + weights["wrong"] * (1 - q)
            + weights["per_work"] * work + weights["per_world_tick"] * ticks
        )
        options.append((mode, z if mode == "CHEAP" else 0, payoff))
    # Frozen stable tie rule: earlier candidate in declared order.
    mode, bit, _ = max(options, key=lambda item: item[2])
    return mode, bit


def decide(e: Evidence, arm: str, state: State) -> tuple[str, int, bool]:
    if arm == "EVALUATOR_ORACLE":
        raise ValueError("EVALUATOR_ONLY_NOT_AN_ORDINARY_POLICY")
    if arm not in ARMS:
        raise ValueError("UNKNOWN_ARM")
    if arm == "STATIC_ZERO":
        return (*cheapest(e, ("CHEAP",)), False)
    if arm == "STATIC_DIAGNOSTIC":
        return (*cheapest(e, ("SCAN", "DEEP", "MEDIUM", "CHEAP")), False)
    if arm == "CHEAP_HISTORY":
        mode, _ = cheapest(e, ("CHEAP",))
        return mode, state.posterior(e.group)[1] if mode == "CHEAP" else 0, False
    if arm == "SIMPLE_GATE":
        p, z = state.posterior(e.group)
        if p >= config()["policy"]["gate_threshold"] and viable(e, "CHEAP"):
            return "CHEAP", z, False
        mode, _ = cheapest(e, ("SCAN", "DEEP", "MEDIUM", "CHEAP"))
        return mode, z if mode == "CHEAP" else 0, False
    if arm == "CACHE_COMPILED":
        n1, n = state.counts(e.group)
        key = (e.group, n1, n, tuple(viable(e, mode) for mode in MODES))
        if key in state.cache:
            return (*state.cache[key], True)
        answer = bayes_decision(e, state)
        state.cache[key] = answer
        return (*answer, False)
    mode, bit = bayes_decision(e, state)
    return mode, bit, False


def run_arm(seed: int, arm: str) -> dict:
    m = config()
    if seed not in m["seeds"]["calibration"] + m["seeds"]["heldout"]:
        raise ValueError("SEED_NOT_FROZEN")
    if arm not in ARMS:
        raise ValueError("ARM_NOT_FROZEN")
    state = State()
    rows = []
    for case in cases(seed):
        world = World(case)
        e = world.evidence()
        if arm == "EVALUATOR_ORACLE":
            # Privileged diagnostic bound: World latent made available for an
            # unrealistically free CHEAP action. Not admitted to ordinary arms.
            mode, hit = ("CHEAP", False) if viable(e, "CHEAP") else ("ABSTAIN", False)
            if mode == "ABSTAIN":
                mode, _ = cheapest(e, ("SCAN", "DEEP", "MEDIUM"))
            z = case.latent_z if mode == "CHEAP" else 0
            if mode == "CHEAP":
                # Never call ordinary World.issue with free hidden z.
                success = True
                damage = exposure = 0
                revision = 1
            elif mode == "ABSTAIN":
                success, damage, exposure, revision = None, 0, 0, None
            else:
                receipt = world.consume(e, world.issue(e, mode), mode)
                success, damage, exposure, revision = (
                    receipt.success, receipt.damage, receipt.exposure,
                    receipt.terminal_revision,
                )
        else:
            mode, z, hit = decide(e, arm, state)
            if mode == "ABSTAIN":
                success, damage, exposure, revision = None, 0, 0, None
            else:
                receipt = world.consume(e, world.issue(e, mode, z_guess=z), mode)
                world.retain(e, receipt, state, arm)
                success, damage, exposure, revision = (
                    receipt.success, receipt.damage, receipt.exposure,
                    receipt.terminal_revision,
                )
        selector = (
            m["policy"]["cache_hit_overhead"] if hit else
            m["policy"]["cache_miss_overhead"] if arm == "CACHE_COMPILED" else
            m["policy"]["resource_overhead"] if arm in (
                "RESOURCE_BAYES", "RESOURCE_NO_FEEDBACK"
            ) else m["policy"]["simple_overhead"] if arm in (
                "SIMPLE_GATE", "CHEAP_HISTORY"
            ) else 0
        )
        ticks, work = COST.get(mode, (0, 0))
        objective = m["objective"]
        utility = (
            objective["correct"] if success is True else
            objective["wrong"] if success is False else objective["abstain"]
        )
        utility += objective["per_work"] * (work + selector)
        utility += objective["per_world_tick"] * ticks
        rows.append({
            "phase": case.phase, "session": e.session, "group": e.group,
            "mode": mode, "selected_z": z, "success": success,
            "ticks": ticks, "work": work, "selector_work": selector,
            "utility_tenths": round(utility * 10), "damage": damage,
            "exposure": exposure, "terminal_revision": revision,
            "cache_hit": hit,
        })
    phases = {}
    for phase in m["phases"]:
        r = [x for x in rows if x["phase"] == phase]
        phases[phase] = {
            "correct": sum(x["success"] is True for x in r),
            "wrong": sum(x["success"] is False for x in r),
            "abstain": sum(x["success"] is None for x in r),
            "mechanism_work": sum(x["work"] for x in r),
            "selector_work": sum(x["selector_work"] for x in r),
            "world_ticks": sum(x["ticks"] for x in r),
            "utility_tenths": sum(x["utility_tenths"] for x in r),
            "cache_hits": sum(x["cache_hit"] for x in r),
            "counts": dict(sorted(Counter(x["mode"] for x in r).items())),
        }
    return {"seed": seed, "arm": arm, "phases": phases, "trace": tuple(rows)}


def run() -> dict:
    m = config()
    records = [
        run_arm(seed, arm) for seed in (
            m["seeds"]["calibration"] + m["seeds"]["heldout"]
        ) for arm in ARMS
    ]
    sums = {}
    for group, seeds in m["seeds"].items():
        sums[group] = {}
        for arm in ARMS:
            rr = [r for r in records if r["seed"] in seeds and r["arm"] == arm]
            sums[group][arm] = {
                key: sum(r["phases"][phase][key] for r in rr for phase in m["phases"])
                for key in ("correct", "wrong", "abstain", "mechanism_work",
                            "selector_work", "world_ticks", "utility_tenths", "cache_hits")
            }
    matched = {}
    for seed in m["seeds"]["heldout"]:
        a, b, c = (next(r for r in records if r["seed"] == seed and r["arm"] == arm)
                   for arm in ("RESOURCE_BAYES", "RESOURCE_NO_FEEDBACK", "CACHE_COMPILED"))
        t1, t2, t3 = a["trace"], b["trace"], c["trace"]
        assert tuple(t["session"] for t in t1) == tuple(t["session"] for t in t2)
        assert tuple((t["mode"], t["selected_z"], t["success"], t["terminal_revision"])
                     for t in t1) == tuple((t["mode"], t["selected_z"], t["success"],
                                              t["terminal_revision"]) for t in t3), (
            "COMPILED_BEHAVIOR_DRIFT"
        )
        matched[str(seed)] = {
            "feedback_changed_choice": sum(
                (x["mode"], x["selected_z"]) != (y["mode"], y["selected_z"])
                for x, y in zip(t1, t2, strict=True)
            ),
            "feedback_correct_delta": (
                sum(x["success"] is True for x in t1) -
                sum(y["success"] is True for y in t2)
            ),
            "cache_hits": sum(x["cache_hit"] for x in t3),
        }
    data = {"manifest_sha256": MANIFEST_SHA, "summaries": sums, "paired": matched}
    data["result_sha256"] = canonical_hash(data)
    return data


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True, separators=(",", ":"), ensure_ascii=False))
