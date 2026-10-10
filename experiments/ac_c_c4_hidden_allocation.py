"""AC-C C4: independent source-limited cognition allocation fixture.

No production authority, LLM/GPU/Minecraft, or sibling Draft imports.
A costed diagnostic obtains additional World information: not computation alone.
"""
from __future__ import annotations

import hashlib
import json
import random
from collections import Counter, deque
from dataclasses import asdict, dataclass, field
from pathlib import Path

MANIFEST_PATH = Path(__file__).with_name("ac_c_c4_manifest.json")
MANIFEST_SHA256 = "d8782e8d814bd0bd1624d4b31224aec1384ba5673a023f0d862e13d58598dc5d"
MODES = ("FAST", "MEDIUM", "OBSERVE", "SLOW")
COST = {"FAST": (1, 1), "MEDIUM": (3, 3), "OBSERVE": (4, 4), "SLOW": (5, 8)}
ARMS = (
    "FAST_ONLY", "SLOW_ONLY", "FIXED", "LEARNED_ALLOC",
    "LEARNED_NO_FEEDBACK", "CHEAP_HISTORY", "SIMPLE_SWITCH", "EVALUATOR_ORACLE",
)


def digest(obj: object) -> str:
    return hashlib.sha256(
        json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def frozen_manifest() -> dict:
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if digest(data) != MANIFEST_SHA256:
        raise ValueError("C4_MANIFEST_DRIFT")
    return data


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
class OutcomeReceipt:
    session: str
    e0_hash: str
    mechanism: str
    selected_action: int
    observed_target: int
    success: bool
    damage: int
    exposure: int
    initial_revision: int
    terminal_revision: int


def generate(seed: int) -> tuple[Case, ...]:
    m = frozen_manifest()
    rng = random.Random(seed)
    records = []
    for phase in m["phases"]:
        for i in range(m["episodes_per_phase"]):
            group = rng.randrange(2)
            prefix = rng.randrange(4)
            latent = int(
                rng.random() < m["hidden_suffix_one_probability_by_group"][phase][group]
            )
            hint = latent if rng.random() < 0.75 else 1 - latent
            records.append(Case(
                session=f"c4:{seed}:{phase}:{i}",
                phase=phase, group=group, prefix=prefix,
                latent_z=latent, medium_hint=hint,
                deadline=rng.choice(m["world"]["deadline_ticks"]),
                health=rng.choice(m["world"]["health"]),
                hunger=rng.choice(m["world"]["hunger"]),
                threat=rng.random() < m["world"]["threat_probability"],
                scan_available=rng.random() < m["world"]["scan_available_probability"],
            ))
    return tuple(records)


def admissible(e: Evidence, mode: str) -> bool:
    if mode not in COST:
        return False
    ticks = COST[mode][0]
    if ticks > e.deadline or (mode == "OBSERVE" and not e.scan_available):
        return False
    if mode == "SLOW" and e.hunger <= 2:
        return False
    exposure = int(e.threat and ticks >= 4)
    worst_error = 2 if mode in ("FAST", "MEDIUM") else 0
    return e.health > worst_error + exposure


class SourceWorld:
    def __init__(self, case: Case):
        self._case = case
        self._issued: OutcomeReceipt | None = None
        self._consumed = False
        self._feedback_used = False

    def e0(self) -> Evidence:
        c = self._case
        return Evidence(
            c.session, 0, c.group, c.prefix, c.deadline,
            c.health, c.hunger, c.threat, c.scan_available,
        )

    def issue(self, e: Evidence, mode: str, *, cheap_z: int = 0) -> OutcomeReceipt:
        if self._issued is not None:
            raise ValueError("DUPLICATE_WORLD_TERMINAL")
        if e != self.e0() or e.revision != 0:
            raise ValueError("STALE_OR_FOREIGN_EVIDENCE")
        if cheap_z not in (0, 1) or (cheap_z != 0 and mode != "FAST"):
            raise ValueError("UNPAID_INFORMATION_CLAIM")
        if not admissible(e, mode):
            raise ValueError("UNADMITTED_MECHANISM")
        # A paid mechanism gets the hidden suffix only *after* selection.
        # The output receipt is World-owned, not predictor-owned.
        if mode == "FAST":
            z = cheap_z
        elif mode == "MEDIUM":
            z = self._case.medium_hint
        else:
            z = self._case.latent_z
        chosen = (e.prefix.bit_count() & 1) ^ z
        succeeded = chosen == self._case.target
        exposure = int(e.threat and COST[mode][0] >= 4)
        damage = int(not succeeded) * 2 + exposure
        terminal_revision = 2 if mode in ("MEDIUM", "OBSERVE", "SLOW") else 1
        self._issued = OutcomeReceipt(
            e.session, digest(asdict(e)), mode, chosen, self._case.target,
            succeeded, damage, exposure, e.revision, terminal_revision,
        )
        return self._issued

    def consume(self, e: Evidence, receipt: OutcomeReceipt, mode: str) -> OutcomeReceipt:
        if (
            self._issued is not receipt
            or self._consumed
            or e != self.e0()
            or receipt.session != e.session
            or receipt.e0_hash != digest(asdict(e))
            or receipt.mechanism != mode
            or receipt.initial_revision != 0
            or receipt.terminal_revision != (1 if mode == "FAST" else 2)
        ):
            raise ValueError("INVALID_OR_REPLAYED_WORLD_FEEDBACK")
        self._consumed = True
        return receipt

    def apply_feedback(
        self, e: Evidence, receipt: OutcomeReceipt, arm: str, state: State
    ) -> None:
        """Only this World may authorize one retained toy update per outcome."""
        if (self._issued is not receipt or not self._consumed
                or self._feedback_used or e != self.e0()):
            raise ValueError("UNATTESTED_OR_DUPLICATE_LEARNING_FEEDBACK")
        self._feedback_used = True
        state._learn_verified(e, receipt, arm)


@dataclass
class State:
    opportunity: int = 0
    fast_result: dict[int, deque[bool]] = field(default_factory=dict)
    z_history: dict[int, deque[int]] = field(default_factory=dict)

    def p_fast(self, group: int) -> float:
        xs = self.fast_result.get(group, ())
        return (1 + sum(xs)) / (2 + len(xs))

    def learned_z(self, group: int) -> int:
        zs = self.z_history.get(group, ())
        return int(sum(zs) > len(zs) / 2)  # tie -> 0

    def _learn_verified(self, e: Evidence, receipt: OutcomeReceipt, arm: str) -> None:
        if arm == "LEARNED_NO_FEEDBACK":
            return
        if arm in ("LEARNED_ALLOC", "SIMPLE_SWITCH") and receipt.mechanism == "FAST":
            self.fast_result.setdefault(e.group, deque(maxlen=8)).append(receipt.success)
        if arm == "CHEAP_HISTORY":
            # Source-qualified *past* terminal target reveals the binary
            # latent difference for this completed case; no future target.
            z = receipt.observed_target ^ (e.prefix.bit_count() & 1)
            self.z_history.setdefault(e.group, deque(maxlen=8)).append(z)


def prefer(e: Evidence, choices: tuple[str, ...]) -> str:
    return next((mode for mode in choices if admissible(e, mode)), "ABSTAIN")


def decide(e: Evidence, arm: str, state: State) -> tuple[str, int]:
    if arm in ("EVALUATOR_ORACLE",):
        raise ValueError("ORACLE_EXCLUDED_FROM_ORDINARY_DECISION")
    if arm not in ARMS:
        raise ValueError("UNKNOWN_ARM")
    if arm in ("FAST_ONLY", "CHEAP_HISTORY"):
        if admissible(e, "FAST"):
            return ("FAST", state.learned_z(e.group) if arm == "CHEAP_HISTORY" else 0)
        return "ABSTAIN", 0
    if arm == "SLOW_ONLY":
        return prefer(e, ("SLOW",)), 0
    if arm == "FIXED":
        if e.health >= 6 and admissible(e, "FAST"):
            return "FAST", 0
        return prefer(e, ("OBSERVE", "SLOW", "MEDIUM", "FAST")), 0
    if arm in ("LEARNED_ALLOC", "LEARNED_NO_FEEDBACK"):
        if state.opportunity % 5 == 4 and admissible(e, "FAST"):
            return "FAST", 0
        if state.p_fast(e.group) >= 0.75 and admissible(e, "FAST"):
            return "FAST", 0
        return prefer(e, ("OBSERVE", "SLOW", "MEDIUM", "FAST")), 0
    # SIMPLE_SWITCH: low-overhead empirical moving reliability without
    # Bayesian smoothing; same exploration clock and admissibility as LEARNED.
    if state.opportunity % 5 == 4 and admissible(e, "FAST"):
        return "FAST", 0
    recent = state.fast_result.get(e.group, ())
    if (not recent or sum(recent) / len(recent) >= 0.75) and admissible(e, "FAST"):
        return "FAST", 0
    return prefer(e, ("OBSERVE", "SLOW", "MEDIUM", "FAST")), 0


def trajectory(seed: int, arm: str) -> dict:
    config = frozen_manifest()
    if seed not in config["seeds"]["calibration"] + config["seeds"]["heldout"]:
        raise ValueError("SEED_NOT_FROZEN")
    if arm not in ARMS:
        raise ValueError("ARM_NOT_FROZEN")
    state = State()
    ledger = []
    for case in generate(seed):
        world = SourceWorld(case)
        e = world.e0()
        if arm == "EVALUATOR_ORACLE":
            # Hidden truth is evaluator privilege, never an ordinary policy input.
            mode, cheap_z = ("FAST", case.latent_z) if admissible(e, "FAST") else (
                prefer(e, ("OBSERVE", "SLOW", "MEDIUM")), 0
            )
            # Evaluator-only instant correct answer is separately calculated;
            # NEVER call SourceWorld FAST cheap_z=latent (unpaid information).
            if mode == "FAST":
                receipt = OutcomeReceipt(
                    e.session, digest(asdict(e)), "ORACLE_VIRTUAL", case.target,
                    case.target, True, 0, 0, 0, 1,
                )
                success = True
            elif mode == "ABSTAIN":
                receipt = None
                success = None
            else:
                receipt = world.consume(e, world.issue(e, mode), mode)
                success = receipt.success
        else:
            mode, cheap_z = decide(e, arm, state)
            if mode == "ABSTAIN":
                receipt = None
                success = None
            else:
                receipt = world.consume(e, world.issue(e, mode, cheap_z=cheap_z), mode)
                world.apply_feedback(e, receipt, arm, state)
                success = receipt.success
        ledger.append({
            "phase": case.phase, "group": e.group, "session": e.session,
            "mechanism": mode, "success": success,
            "ticks": 0 if mode == "ABSTAIN" else COST[mode][0],
            "work": 0 if mode == "ABSTAIN" else COST[mode][1],
            "overhead": config["cost"]["selector_work"][arm],
            "damage": 0 if receipt is None else receipt.damage,
            "exposure": 0 if receipt is None else receipt.exposure,
            "world_revision": None if receipt is None else receipt.terminal_revision,
        })
        state.opportunity += 1
    summary = {}
    for phase in config["phases"]:
        rows = [x for x in ledger if x["phase"] == phase]
        summary[phase] = {
            "success": sum(x["success"] is True for x in rows),
            "wrong": sum(x["success"] is False for x in rows),
            "abstain": sum(x["success"] is None for x in rows),
            "counts": dict(sorted(Counter(x["mechanism"] for x in rows).items())),
            "ticks": sum(x["ticks"] for x in rows),
            "work": sum(x["work"] for x in rows),
            "selector_work": sum(x["overhead"] for x in rows),
            "damage": sum(x["damage"] for x in rows),
            "exposure": sum(x["exposure"] for x in rows),
        }
    # Temporal witness, not causal inference.
    shift = [x for x in ledger if x["phase"] == "shift"]
    witnesses = {}
    for group in (0, 1):
        failures = [i for i, row in enumerate(shift)
                    if row["group"] == group and row["mechanism"] == "FAST"
                    and row["success"] is False]
        if not failures:
            witnesses[str(group)] = {"fast_failure": False, "lag": None, "censored": True}
            continue
        t = failures[0]
        later = [i for i in range(t + 1, len(shift))
                 if shift[i]["group"] == group
                 and shift[i]["mechanism"] in ("MEDIUM", "SLOW", "OBSERVE")]
        witnesses[str(group)] = {
            "fast_failure": True, "lag": later[0] - t if later else None,
            "censored": not bool(later),
        }
    return {"seed": seed, "arm": arm, "phases": summary, "witnesses": witnesses,
            "trace": tuple(ledger)}


def report() -> dict:
    cfg = frozen_manifest()
    records = [trajectory(seed, arm) for seed in (
        cfg["seeds"]["calibration"] + cfg["seeds"]["heldout"]
    ) for arm in cfg["arms"]]
    summary = {}
    for group, seeds in cfg["seeds"].items():
        summary[group] = {}
        for arm in cfg["arms"]:
            runs = [r for r in records if r["seed"] in seeds and r["arm"] == arm]
            summary[group][arm] = {
                k: sum(r["phases"][phase][k] for r in runs for phase in cfg["phases"])
                for k in ("success", "wrong", "abstain", "ticks", "work", "selector_work", "damage")
            }
            summary[group][arm]["witnessed_shift"] = sum(
                w["fast_failure"] and not w["censored"]
                for r in runs for w in r["witnesses"].values()
            )
    pairs = {}
    for seed in cfg["seeds"]["heldout"]:
        a = next(r for r in records if r["seed"] == seed and r["arm"] == "LEARNED_ALLOC")
        b = next(r for r in records if r["seed"] == seed and r["arm"] == "LEARNED_NO_FEEDBACK")
        aa, bb = a["trace"], b["trace"]
        assert tuple(x["session"] for x in aa) == tuple(x["session"] for x in bb)
        pairs[str(seed)] = {
            "selection_divergences": sum(
                x["mechanism"] != y["mechanism"] for x, y in zip(aa, bb, strict=True)
            ),
            "success_difference": (
                sum(x["success"] is True for x in aa) -
                sum(y["success"] is True for y in bb)
            ),
        }
    return {
        "manifest_sha256": MANIFEST_SHA256, "records_sha256": digest(records),
        "summaries": summary, "feedback_pairs": pairs,
        "phase_counts_heldout": {
            arm: {
                phase: {
                    k: sum(r["phases"][phase][k] for r in records
                           if r["arm"] == arm and
                           r["seed"] in cfg["seeds"]["heldout"])
                    for k in ("success", "wrong", "abstain")
                } for phase in cfg["phases"]
            } for arm in cfg["arms"]
        },
    }


if __name__ == "__main__":
    print(json.dumps(report(), sort_keys=True, ensure_ascii=False))
