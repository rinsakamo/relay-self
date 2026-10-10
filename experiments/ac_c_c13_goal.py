"""C13: positive goal-witness cognition without gifted hidden-z World labels.

An offline deterministic toy. A physical move is not a goal completion.
Neither failed NORMAL nor failed DETOUR determines a hidden cause.
World retains source-minted Action/goals; ordinary selectors NEVER see hidden z.
"""
from __future__ import annotations

import hashlib
import json
import random
from collections import Counter, deque
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path

MANIFEST = Path(__file__).with_name("ac_c_c13_manifest.json")
MANIFEST_SHA = "731fbb5ee781f55f6715942665cedd1169cc5c7117853b6db0b0b45071e86550"
ARMS = (
    "FROZEN_GROUP", "NO_FEEDBACK_GROUP", "ADAPT_GROUP",
    "FROZEN_MAJORITY", "ADAPT_MAJORITY", "STATIC_GATE",
    "LEARNED_GATE", "SIMPLE_R_GATE", "CERTIFY_ALWAYS",
    "CERTIFY_SELECTIVE", "CERTIFY_ACTION_ONLY", "EVALUATOR_ORACLE",
)
FROZEN = {"FROZEN_GROUP", "NO_FEEDBACK_GROUP", "FROZEN_MAJORITY"}
DET_COST = (3, 4)
NORMAL_COST = (1, 1)


def checksum(obj: object) -> str:
    return hashlib.sha256(json.dumps(
        obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")).hexdigest()


@lru_cache(maxsize=1)
def manifest() -> dict:
    x = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if checksum(x) != MANIFEST_SHA:
        raise ValueError("C13_FROZEN_MANIFEST_DRIFT")
    return x


@dataclass(frozen=True)
class Hidden:
    session: str
    epoch: str
    group: int
    prefix: int
    cues: tuple[int, int, int]
    hidden_z: int
    blocked_normal: bool
    blocked_detour: bool
    health: int
    deadline: int
    hunger: int
    threat: bool


@dataclass(frozen=True)
class E0:
    session: str
    revision: int
    group: int
    prefix: int
    cues: tuple[int, int, int]
    health: int
    deadline: int
    hunger: int
    threat: bool


@dataclass(frozen=True)
class WorldReceipt:
    session: str
    e0_hash: str
    parent_hash: str | None
    action_type: str
    action_bit: int
    moved: bool
    goal_reached: bool
    revision: int


def generate(seed: int) -> tuple[Hidden, ...]:
    m = manifest()
    rng = random.Random(seed)
    rows = []
    for ep in m["epochs"]:
        for idx in range(m["episodes_per_epoch"]):
            g = rng.randrange(2)
            z = int(rng.random() < m["hidden_z_p1"][ep][g])
            r = m["public_cue_reliability"][ep]
            public = tuple(z if rng.random() < r else 1-z for _ in range(3))
            sid = hashlib.sha256(f"c13:{seed}:{len(rows)}".encode()).hexdigest()[:24]
            rows.append(Hidden(
                sid, ep, g, rng.randrange(4), public, z,
                rng.random() < m["world"]["normal_block_probability"],
                rng.random() < m["world"]["detour_unexpected_block_probability"],
                rng.choice(m["world"]["health"]),
                rng.choice(m["world"]["deadline"]),
                rng.choice(m["world"]["hunger"]),
                rng.random() < m["world"]["threat_p"],
            ))
    return tuple(rows)


def admissible_first(e: E0) -> bool:
    return e.revision == 0 and e.health > 2 and e.deadline >= 1


def admissible_detour(e: E0) -> bool:
    c = manifest()["world"]
    health_remain = e.health - c["damage_on_each_failed_goal"]
    exposure = int(e.threat) * c["detour_threat_exposure"]
    return (admissible_first(e) and e.deadline-NORMAL_COST[0] >= DET_COST[0]
            and health_remain > 1+exposure and e.hunger > 2)


@dataclass
class Retention:
    group_z: dict[int, deque[int]] = field(default_factory=dict)
    cue_matches: deque[int] = field(default_factory=lambda: deque(maxlen=24))
    admitted_sessions: set[str] = field(default_factory=set)

    def p1(self, group: int) -> float:
        h = self.group_z.get(group, ())
        return (1+sum(h))/(2+len(h))

    def group_bit(self, group: int) -> int:
        return int(self.p1(group) > .5)

    def sensor_r(self) -> float:
        c = manifest()["retention"]
        n = len(self.cue_matches)
        k = c["cue_r_pseudocount"]
        raw = (sum(self.cue_matches) + k*c["cue_r_prior"])/(3*n+k)
        lower, upper = c["cue_r_clamp"]
        return max(lower, min(upper, raw))

    def accept(self, e: E0, used: WorldReceipt) -> bool:
        if e.session in self.admitted_sessions:
            raise ValueError("C13_DUPLICATE_RETAINED_SOURCE")
        if used.session != e.session or not used.goal_reached:
            raise ValueError("C13_UNQUALIFIED_GOAL_PROOF")
        # Recover committed z from executed physical Action and visible prefix.
        # This is NOT an exact hidden-z label from the environment.
        z = (e.prefix.bit_count() & 1) ^ used.action_bit
        if z not in (0, 1):
            raise ValueError("C13_UNKNOWN_ACTION")
        self.admitted_sessions.add(e.session)
        self.group_z.setdefault(
            e.group, deque(maxlen=manifest()["retention"]["group_window"])
        ).append(z)
        self.cue_matches.append(sum(b == z for b in e.cues))
        return True

    def fingerprint(self) -> tuple:
        return (
            tuple(tuple(self.group_z.get(g, ())) for g in (0, 1)),
            tuple(self.cue_matches),
        )


class World:
    def __init__(self, case: Hidden):
        self._case = case
        self._first: WorldReceipt | None = None
        self._first_consumed = False
        self._second: WorldReceipt | None = None
        self._second_consumed = False
        self._stopped = False
        self._retained = False

    def e0(self) -> E0:
        c = self._case
        return E0(c.session, 0, c.group, c.prefix, c.cues,
                  c.health, c.deadline, c.hunger, c.threat)

    def issue_first(self, e: E0, guess_z: int) -> WorldReceipt:
        if self._first is not None:
            raise ValueError("C13_DUPLICATE_FIRST")
        if e != self.e0() or not admissible_first(e) or guess_z not in (0, 1):
            raise ValueError("C13_UNAUTHORIZED_FIRST")
        act = (e.prefix.bit_count() & 1) ^ guess_z
        moved = not self._case.blocked_normal
        self._first = WorldReceipt(
            e.session, checksum(asdict(e)), None, "NORMAL", act, moved,
            moved and guess_z == self._case.hidden_z, 1,
        )
        return self._first

    def consume_first(self, e: E0, r: WorldReceipt) -> WorldReceipt:
        if (self._first_consumed or r is not self._first or e != self.e0()
                or r.session != e.session or r.e0_hash != checksum(asdict(e))
                or r.revision != 1 or r.action_type != "NORMAL"):
            raise ValueError("C13_FORGED_STALE_OR_REPLAYED_FIRST")
        self._first_consumed = True
        return r

    def issue_second(self, e: E0, first: WorldReceipt, action: str) -> WorldReceipt:
        if (not self._first_consumed or self._first is not first
                or first.goal_reached or self._second is not None or self._stopped
                or e != self.e0()):
            raise ValueError("C13_SECOND_NOT_AUTHORIZED")
        if not admissible_detour(e) or action not in ("DETOUR_SAME", "DETOUR_FLIP"):
            raise ValueError("C13_UNSAFE_DETOUR")
        z_first = (e.prefix.bit_count() & 1) ^ first.action_bit
        z = z_first if action == "DETOUR_SAME" else 1-z_first
        moved = not self._case.blocked_detour
        self._second = WorldReceipt(
            e.session, checksum(asdict(e)), checksum(asdict(first)),
            action, (e.prefix.bit_count() & 1) ^ z,
            moved, moved and z == self._case.hidden_z, 2,
        )
        return self._second

    def consume_second(
        self, e: E0, first: WorldReceipt, second: WorldReceipt,
    ) -> WorldReceipt:
        if (self._second_consumed or second is not self._second
                or self._first is not first or not self._first_consumed
                or second.parent_hash != checksum(asdict(first))
                or second.e0_hash != checksum(asdict(e)) or e != self.e0()
                or second.session != e.session or second.revision != 2):
            raise ValueError("C13_FORGED_STALE_OR_REPLAYED_SECOND")
        self._second_consumed = True
        return second

    def stop(self, e: E0, first: WorldReceipt) -> None:
        if (not self._first_consumed or self._first is not first
                or first.goal_reached or self._second is not None or self._stopped
                or e != self.e0()):
            raise ValueError("C13_STOP_NOT_AUTHORIZED")
        self._stopped = True

    def retain(
        self, e: E0, first: WorldReceipt, second: WorldReceipt | None,
        state: Retention, *, enabled: bool, second_enabled: bool = True,
    ) -> tuple[bool, str]:
        if (self._retained or not self._first_consumed
                or self._first is not first or second is not self._second
                or e != self.e0()
                or not (first.goal_reached or self._stopped or self._second_consumed)):
            raise ValueError("C13_PREMATURE_FOREIGN_OR_REPLAYED_RETENTION")
        self._retained = True
        if not enabled:
            return False, "DISABLED"
        witness = first if first.goal_reached else (
            second if second_enabled and second is not None and second.goal_reached else None
        )
        if witness is None:
            return False, "UNIDENTIFIED"
        return state.accept(e, witness), (
            "FIRST_GOAL" if witness is first else "SECOND_GOAL"
        )

    def evaluate(self) -> dict:
        """Explicit hidden evaluator channel, never a learner/selector input."""
        if not self._retained or not self._first_consumed:
            raise ValueError("C13_WORLD_TRANSACTION_NOT_COMPLETE")
        c = self._case
        f = self._first
        second = self._second if self._second_consumed else None
        guess_first = (c.prefix.bit_count() & 1)^f.action_bit
        return {
            "first_decision_correct": guess_first == c.hidden_z,
            "first_goal": f.goal_reached,
            "final_goal": f.goal_reached or (
                second.goal_reached if second is not None else False
            ),
            "hidden_z": c.hidden_z,
            "blocked_normal": c.blocked_normal,
            "blocked_detour": c.blocked_detour,
        }


def majority(e: E0) -> int:
    return int(sum(e.cues) >= 2)


def choose(e: E0, state: Retention, arm: str, *, warmup: bool) -> tuple[str, int]:
    if arm not in ARMS:
        raise ValueError("C13_UNKNOWN_ARM")
    if not admissible_first(e):
        return "ABSTAIN", 0
    group = state.group_bit(e.group)
    mbit = majority(e)
    if warmup or arm in (
        "FROZEN_GROUP", "NO_FEEDBACK_GROUP", "ADAPT_GROUP",
    ):
        return "GROUP", group
    if arm in ("FROZEN_MAJORITY", "ADAPT_MAJORITY"):
        return "MAJORITY", mbit
    if arm == "EVALUATOR_ORACLE":
        raise ValueError("C13_NO_ORACLE_IN_SOURCE_SELECTOR")
    if arm == "SIMPLE_R_GATE":
        return (("GROUP", group) if state.sensor_r() <
                manifest()["selection"]["simple_gate_r"] else ("MAJORITY", mbit))
    r = (manifest()["selection"]["static_r"]
         if arm == "STATIC_GATE" else state.sensor_r())
    pg = state.p1(e.group)
    ma = 3*r*r-2*r*r*r
    advantage = (manifest()["score"]["goal_reached"] -
                 manifest()["score"]["attempted_no_goal"])*(ma - max(pg, 1-pg))
    # Prospective decision calibration gain uses the frozen binary +/-10
    # contrast (20) rather than full-episode success utility (+12/-6).
    advantage = 20*(ma - max(pg, 1-pg))
    if advantage > 0.5:
        return "MAJORITY", mbit
    return "GROUP", group


def trajectory(seed: int, arm: str) -> dict:
    m = manifest()
    if seed not in m["seeds"]["calibration"] + m["seeds"]["heldout"]:
        raise ValueError("C13_UNREGISTERED_SEED")
    if arm not in ARMS:
        raise ValueError("C13_UNREGISTERED_ARM")
    state = Retention()
    rows = []
    warmup_signature = None
    for case in generate(seed):
        warmup = case.epoch == "warmup"
        if not warmup and warmup_signature is None:
            warmup_signature = state.fingerprint()
        world = World(case)
        e = world.e0()
        prior_group = state.group_bit(e.group)
        prior_r = state.sensor_r()
        first = None
        second = None
        detour = "NONE"
        z_mode = "ABSTAIN"
        selected_z = None
        certificate = False
        cert_kind = "NONE"
        first_goal = False
        final_goal = False
        physical_moved_without_goal = False
        first_correct = None
        if admissible_first(e):
            if arm == "EVALUATOR_ORACLE" and not warmup:
                z_mode, selected_z = "ORACLE", case.hidden_z
            else:
                z_mode, selected_z = choose(e, state, arm, warmup=warmup)
            first = world.consume_first(e, world.issue_first(e, selected_z))
            first_goal = first.goal_reached
            final_goal = first_goal
            physical_moved_without_goal = first.moved and not first.goal_reached
            if not first_goal:
                attempted_cert = (not warmup and arm in (
                    "CERTIFY_ALWAYS", "CERTIFY_SELECTIVE", "CERTIFY_ACTION_ONLY"
                ))
                wants_detour = (
                    attempted_cert and (
                        arm != "CERTIFY_SELECTIVE"
                        or majority(e) != selected_z
                        or prior_r < m["selection"]["selective_certify_r"]
                    )
                )
                if wants_detour and admissible_detour(e):
                    detour = (
                        "DETOUR_SAME" if majority(e) == selected_z else "DETOUR_FLIP"
                    )
                    second = world.consume_second(
                        e, first, world.issue_second(e, first, detour)
                    )
                    final_goal = second.goal_reached
                else:
                    world.stop(e, first)
            enabled = warmup or arm not in FROZEN|{"EVALUATOR_ORACLE"}
            certificate, cert_kind = world.retain(
                e, first, second, state,
                enabled=enabled,
                second_enabled=arm != "CERTIFY_ACTION_ONLY",
            )
            evaluated = world.evaluate()  # evaluator ONLY after model updated
            first_correct = evaluated["first_decision_correct"]
            assert evaluated["first_goal"] == first_goal
            assert evaluated["final_goal"] == final_goal
            if certificate:
                assert final_goal
                proof = first if cert_kind == "FIRST_GOAL" else second
                # Audit-only exactness check; the learner never sees this.
                extracted = (e.prefix.bit_count() & 1)^proof.action_bit
                assert extracted == evaluated["hidden_z"]
        decoder_work = int(z_mode == "MAJORITY")
        first_work = NORMAL_COST[1] if first is not None else 0
        first_ticks = NORMAL_COST[0] if first is not None else 0
        selector_work = (
            0 if warmup or first is None
            else m["selector_overhead_on_first_admitted"][arm]
        )
        work = first_work + decoder_work + selector_work + (
            DET_COST[1] if second is not None else 0
        ) + int(certificate)*m["retention"]["learning_work_per_certificate"]
        ticks = first_ticks + (DET_COST[0] if second is not None else 0)
        score = (
            m["score"]["initial_abstain"] if first is None else
            m["score"]["goal_reached"] if final_goal else
            m["score"]["attempted_no_goal"]
        )
        score += m["score"]["per_work"]*work + m["score"]["per_tick"]*ticks
        rows.append({
            "session": e.session, "epoch": case.epoch,
            "first_mode": z_mode, "first_z": selected_z,
            "first_correct": first_correct, "first_goal": first_goal,
            "first_moved_not_goal": physical_moved_without_goal,
            "final_goal": final_goal,
            "detour": detour, "certificate": certificate,
            "certificate_kind": cert_kind,
            "r_before": prior_r, "group_before": prior_group,
            "r_after": state.sensor_r(),
            "work": work, "ticks": ticks, "utility_tenths": round(score*10),
        })
    if warmup_signature is None:
        raise AssertionError("C13_WARMUP_MISSING")
    phases = {}
    for epoch in m["epochs"]:
        sub = [r for r in rows if r["epoch"] == epoch]
        assert len(sub) == m["episodes_per_epoch"]
        phases[epoch] = {
            "first_correct": sum(x["first_correct"] is True for x in sub),
            "first_wrong": sum(x["first_correct"] is False for x in sub),
            "initial_abstain": sum(x["first_correct"] is None for x in sub),
            "first_goal": sum(x["first_goal"] for x in sub),
            "final_goal": sum(x["final_goal"] for x in sub),
            "moved_without_goal": sum(x["first_moved_not_goal"] for x in sub),
            "certificates": sum(x["certificate"] for x in sub),
            "first_certificates": sum(x["certificate_kind"] == "FIRST_GOAL" for x in sub),
            "second_certificates": sum(x["certificate_kind"] == "SECOND_GOAL" for x in sub),
            "detour_count": sum(x["detour"] != "NONE" for x in sub),
            "group_choices": sum(x["first_mode"] == "GROUP" for x in sub),
            "majority_choices": sum(x["first_mode"] == "MAJORITY" for x in sub),
            "work": sum(x["work"] for x in sub),
            "ticks": sum(x["ticks"] for x in sub),
            "utility_tenths": sum(x["utility_tenths"] for x in sub),
            "phase_r_end": round(sub[-1]["r_after"], 6),
            "modes": dict(sorted(Counter(x["first_mode"] for x in sub).items())),
        }
    return {"seed": seed, "arm": arm, "warmup_signature": warmup_signature,
            "phases": phases, "trace": tuple(rows)}


def report() -> dict:
    m = manifest()
    runs = [
        trajectory(seed, arm)
        for seed in m["seeds"]["calibration"]+m["seeds"]["heldout"]
        for arm in ARMS
    ]
    keys = (
        "first_correct", "first_wrong", "initial_abstain", "first_goal",
        "final_goal", "moved_without_goal", "certificates", "first_certificates",
        "second_certificates", "detour_count", "group_choices",
        "majority_choices", "work", "ticks", "utility_tenths",
    )
    split_summary = {}
    for split, seeds in m["seeds"].items():
        split_summary[split] = {}
        for arm in ARMS:
            rr = [x for x in runs if x["seed"] in seeds and x["arm"] == arm]
            r = {
                k: sum(x["phases"][ep][k] for x in rr for ep in m["epochs"][1:])
                for k in keys
            }
            r["phase_final_goal"] = {
                ep: sum(x["phases"][ep]["final_goal"] for x in rr)
                for ep in m["epochs"]
            }
            r["phase_first_correct"] = {
                ep: sum(x["phases"][ep]["first_correct"] for x in rr)
                for ep in m["epochs"]
            }
            r["phase_r_end_mean"] = {
                ep: round(
                    sum(x["phases"][ep]["phase_r_end"] for x in rr)/len(rr), 4
                ) for ep in m["epochs"]
            }
            r["phase_r_generator_mean_abs_error"] = {
                ep: round(
                    sum(abs(x["phases"][ep]["phase_r_end"] -
                            m["public_cue_reliability"][ep]) for x in rr)/len(rr),
                    4
                ) for ep in m["epochs"]
            }
            split_summary[split][arm] = r
    paired = {}
    for seed in m["seeds"]["heldout"]:
        rr = {
            a: next(x for x in runs if x["seed"] == seed and x["arm"] == a)
            for a in ARMS
        }
        assert len({r["warmup_signature"] for r in rr.values()}) == 1
        assert len({tuple(t["session"] for t in r["trace"]) for r in rr.values()}) == 1
        paired[str(seed)] = {
            "gate_minus_majority": sum(
                rr["LEARNED_GATE"]["phases"][ep]["final_goal"] -
                rr["FROZEN_MAJORITY"]["phases"][ep]["final_goal"]
                for ep in m["epochs"][1:]
            ),
            "gate_minus_group": sum(
                rr["LEARNED_GATE"]["phases"][ep]["final_goal"] -
                rr["ADAPT_GROUP"]["phases"][ep]["final_goal"]
                for ep in m["epochs"][1:]
            ),
            "selective_minus_gate": sum(
                rr["CERTIFY_SELECTIVE"]["phases"][ep]["final_goal"] -
                rr["LEARNED_GATE"]["phases"][ep]["final_goal"]
                for ep in m["epochs"][1:]
            ),
            "selective_extra_certificates": sum(
                rr["CERTIFY_SELECTIVE"]["phases"][ep]["second_certificates"]
                for ep in m["epochs"][1:]
            ),
        }
    answer = {"manifest_sha256": MANIFEST_SHA, "summary": split_summary,
              "paired": paired}
    answer["result_sha256"] = checksum(answer)
    return answer


if __name__ == "__main__":
    print(json.dumps(report(), sort_keys=True, ensure_ascii=False))
