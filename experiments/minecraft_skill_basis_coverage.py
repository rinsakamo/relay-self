from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

CANDIDATE_SKILL_BASIS: tuple[str, ...] = (
    "WAIT",
    "EAT",
    "FIGHT",
    "FLEE",
    "SEEK",
    "TALK",
    "CONTEMPLATE",
)


class CandidateStatus(str, Enum):
    """Current experiment-local result of the Grand Null attack."""

    REDUCED = "reduced"
    OPEN = "open"
    SURVIVES_CURRENT_ATTACK = "survives_current_attack"


CANDIDATE_STATUS: dict[str, CandidateStatus] = {
    "WAIT": CandidateStatus.REDUCED,
    "EAT": CandidateStatus.SURVIVES_CURRENT_ATTACK,
    "FIGHT": CandidateStatus.SURVIVES_CURRENT_ATTACK,
    "FLEE": CandidateStatus.SURVIVES_CURRENT_ATTACK,
    "SEEK": CandidateStatus.OPEN,
    "TALK": CandidateStatus.REDUCED,
    "CONTEMPLATE": CandidateStatus.REDUCED,
}

# Experiment-local abstraction over target-native capabilities. This is not a
# production Action ontology or adapter contract.
TARGET_PRIMITIVES: frozenset[str] = frozenset(
    {
        "MOVE",
        "LOOK",
        "EQUIP",
        "CONSUME",
        "ATTACK",
        "BREAK",
        "TAKE",
        "PLACE",
        "USE",
        "TRANSFER",
        "CRAFT",
        "CHAT_DELIVERY",
    }
)

# Snapshot of abstract primitive families reachable through the current
# Mineflayer effect surface. The adapter remains authoritative for its protocol.
CURRENT_ADAPTER_PRIMITIVE_FIXTURE: frozenset[str] = frozenset(
    {"MOVE", "LOOK", "EQUIP", "CONSUME", "ATTACK"}
)


@dataclass(frozen=True, slots=True)
class BehaviorDecomposition:
    """One falsification record, not a declaration of required Skills."""

    behavior_id: str
    family: str
    summary: str
    proposed_skills: tuple[str, ...]
    surviving_candidates: tuple[str, ...]
    open_candidates: tuple[str, ...]
    primitives: tuple[str, ...]
    owners: tuple[str, ...] = ()
    pressure: str = ""

    def missing_current_primitives(self) -> tuple[str, ...]:
        return tuple(
            primitive
            for primitive in self.primitives
            if primitive not in CURRENT_ADAPTER_PRIMITIVE_FIXTURE
        )


def _case(
    behavior_id: str,
    family: str,
    summary: str,
    proposed: tuple[str, ...],
    *,
    surviving: tuple[str, ...] = (),
    open_: tuple[str, ...] = (),
    primitives: tuple[str, ...] = (),
    owners: tuple[str, ...] = (),
    pressure: str,
) -> BehaviorDecomposition:
    return BehaviorDecomposition(
        behavior_id=behavior_id,
        family=family,
        summary=summary,
        proposed_skills=proposed,
        surviving_candidates=surviving,
        open_candidates=open_,
        primitives=primitives,
        owners=owners,
        pressure=pressure,
    )


BEHAVIOR_CORPUS: tuple[BehaviorDecomposition, ...] = (
    _case(
        "hold_position",
        "inaction",
        "Remain in place without inventing an external intervention.",
        ("WAIT",),
        owners=("Current Intent", "Scheduler/timing when needed"),
        pressure="Healthy inactivity already requires no SkillExecution.",
    ),
    _case(
        "eat_available_food",
        "body_maintenance",
        "Consume an available edible item and ground success in later body state.",
        ("EAT",),
        surviving=("EAT",),
        primitives=("EQUIP", "CONSUME"),
        owners=("Body/resource state",),
        pressure="EAT survives the current attack; final irreducibility is not claimed.",
    ),
    _case(
        "direct_combat",
        "combat",
        "Attack a grounded adverse target and ground the local result.",
        ("FIGHT",),
        surviving=("FIGHT",),
        primitives=("LOOK", "ATTACK"),
        owners=("Current Appraisal",),
        pressure="Target discovery is distinct from antagonistic intervention.",
    ),
    _case(
        "escape_threat",
        "escape",
        "Increase separation from a grounded threat and observe progress.",
        ("FLEE",),
        surviving=("FLEE",),
        primitives=("LOOK", "MOVE"),
        owners=("Current Appraisal",),
        pressure="Locating safety is distinct from closed-loop separation.",
    ),
    _case(
        "navigate_remembered_location",
        "navigation",
        "Travel toward a location already represented by owned cognition.",
        ("SEEK",),
        primitives=("MOVE",),
        owners=("Memory", "Current Intent"),
        pressure=(
            "Known target location removes target-absence uncertainty; SEEK must not "
            "become a generic GO/GOAL operator."
        ),
    ),
    _case(
        "search_unknown_resource",
        "exploration",
        "Act to reduce uncertainty until a resource is observed or remains unresolved.",
        ("SEEK",),
        open_=("SEEK",),
        primitives=("MOVE", "LOOK"),
        owners=("Current Intent", "Observation"),
        pressure="Active time-spanning SEEK remains open after snapshot SEEK reduced.",
    ),
    _case(
        "mine_and_craft_upgrade",
        "resource_processing",
        "Locate missing material when needed, acquire it, and construct equipment.",
        ("SEEK", "CONTEMPLATE"),
        open_=("SEEK",),
        primitives=("MOVE", "LOOK", "EQUIP", "BREAK", "TAKE", "CRAFT"),
        owners=("Memory", "Capability", "ordinary cognition"),
        pressure="CONTEMPLATE reduces; BREAK/TAKE/CRAFT remain boundary gaps.",
    ),
    _case(
        "build_shelter_before_night",
        "construction",
        "Use or form a design, obtain missing material/site information, and build.",
        ("CONTEMPLATE", "SEEK"),
        open_=("SEEK",),
        primitives=("MOVE", "LOOK", "PLACE"),
        owners=("Time observation", "Inventory", "ordinary cognition"),
        pressure="Design cognition does not require CONTEMPLATE; PLACE is a boundary gap.",
    ),
    _case(
        "farm_renewable_food",
        "resource_processing",
        "Establish, monitor, and harvest a renewable food process.",
        ("SEEK", "WAIT", "EAT"),
        open_=("SEEK",),
        primitives=("MOVE", "USE", "PLACE", "BREAK", "TAKE"),
        owners=("Body/resource state", "Scheduler/timing"),
        pressure="WAIT reduces to timing/no-action; EAT is not required to operate the farm.",
    ),
    _case(
        "scout_and_report",
        "information_social",
        "Acquire missing environmental information and report it to another Self.",
        ("SEEK", "TALK"),
        open_=("SEEK",),
        primitives=("MOVE", "LOOK", "CHAT_DELIVERY"),
        owners=("Observation",),
        pressure="TALK carries language coupling; active SEEK remains open.",
    ),
    _case(
        "coordinate_two_agent_attack",
        "social_combat",
        "Exchange task-relevant language and converge on a combat intervention.",
        ("TALK", "SEEK", "FIGHT"),
        surviving=("FIGHT",),
        open_=("SEEK",),
        primitives=("CHAT_DELIVERY", "MOVE", "LOOK", "ATTACK"),
        owners=("Other/Relationship cognition",),
        pressure="No hard-coded COOPERATE or ROLE Skill is required.",
    ),
    _case(
        "share_scarce_food",
        "social_resource",
        "Transfer a scarce resource to another Self.",
        ("TALK",),
        primitives=("TRANSFER",),
        owners=("Other/Relationship cognition", "Body/resource state", "Current Intent"),
        pressure="An already-decided transfer does not semantically require TALK.",
    ),
    _case(
        "trade_resources",
        "social_resource",
        "Negotiate and exchange resources without introducing a TRADE Skill.",
        ("TALK", "SEEK"),
        open_=("SEEK",),
        primitives=("CHAT_DELIVERY", "TRANSFER"),
        owners=("Other/Relationship cognition",),
        pressure="TALK carries negotiation; SEEK applies only to missing targets/information.",
    ),
    _case(
        "ambush_player",
        "social_combat",
        "Reach a position, withhold intervention until a condition, then attack.",
        ("SEEK", "WAIT", "FIGHT"),
        surviving=("FIGHT",),
        open_=("SEEK",),
        primitives=("MOVE", "LOOK", "ATTACK"),
        owners=("Current Intent", "Scheduler/timing"),
        pressure="WAIT reduces to timing/no-action; active target search remains open.",
    ),
    _case(
        "retreat_and_regroup",
        "social_escape",
        "Escape a threat while restoring contact/proximity with a companion.",
        ("FLEE", "SEEK", "TALK"),
        surviving=("FLEE",),
        open_=("SEEK",),
        primitives=("MOVE", "LOOK", "CHAT_DELIVERY"),
        owners=("Other/Relationship cognition",),
        pressure="FLEE remains distinct; SEEK is conditional on missing target information.",
    ),
    _case(
        "escort_companion",
        "social_navigation",
        "Maintain useful proximity to a companion and respond to threats.",
        ("SEEK", "FIGHT", "FLEE", "TALK"),
        surviving=("FIGHT", "FLEE"),
        open_=("SEEK",),
        primitives=("MOVE", "LOOK", "ATTACK", "CHAT_DELIVERY"),
        owners=("Other/Relationship cognition",),
        pressure="FOLLOW/GUARD are not forced; tracking/navigation remains future pressure.",
    ),
    _case(
        "rescue_companion_under_attack",
        "social_combat",
        "Locate missing relevant entities when needed and intervene under threat.",
        ("SEEK", "FIGHT", "TALK"),
        surviving=("FIGHT",),
        open_=("SEEK",),
        primitives=("MOVE", "LOOK", "ATTACK", "CHAT_DELIVERY"),
        owners=("Other/Relationship cognition", "Current Appraisal"),
        pressure="RESCUE remains composition rather than a named basis Skill.",
    ),
    _case(
        "construct_operate_mechanism",
        "construction",
        "Use or form a design, assemble, and operate a multi-part mechanism.",
        ("CONTEMPLATE", "SEEK"),
        open_=("SEEK",),
        primitives=("MOVE", "LOOK", "PLACE", "USE"),
        owners=("Memory", "Capability", "ordinary cognition"),
        pressure="CONTEMPLATE reduces; construction primitives remain boundary concerns.",
    ),
    _case(
        "recover_after_respawn",
        "recovery",
        "After respawn, recover toward a remembered useful state.",
        ("SEEK",),
        open_=("SEEK",),
        primitives=("MOVE", "LOOK", "TAKE"),
        owners=("Persistent Cognition", "World observation", "Current Intent"),
        pressure="SEEK applies only when recovery targets must be rediscovered.",
    ),
    _case(
        "learn_from_failed_route_or_fight",
        "learning",
        "Integrate grounded consequence so later reduction can differ.",
        (),
        owners=("Experience Integration", "Memory", "Capability"),
        pressure="Not every meaningful adaptive process belongs in the Skill basis.",
    ),
    _case(
        "plan_multi_step_expedition",
        "internal_cognition",
        "Construct and compare a hypothetical multi-step expedition before acting.",
        ("CONTEMPLATE",),
        owners=("Memory", "Capability", "Current Intent", "RelayEngine cognition"),
        pressure="Existing Retrieval/BOUNDED/THINK/OPEN cover this without CONTEMPLATE.",
    ),
    _case(
        "deceive_other_through_language",
        "social_cognition",
        "Generate an intentionally misleading expression for another agent.",
        ("CONTEMPLATE", "TALK"),
        primitives=("CHAT_DELIVERY",),
        owners=("Other/Relationship cognition", "ordinary cognition"),
        pressure="Internal reasoning does not require CONTEMPLATE; TALK retains coupling.",
    ),
    _case(
        "create_novel_structure",
        "construction",
        "Generate a novel internal design and realize it through target primitives.",
        ("CONTEMPLATE", "SEEK"),
        open_=("SEEK",),
        primitives=("MOVE", "LOOK", "PLACE"),
        owners=("ordinary cognition", "Current Intent"),
        pressure="Novel cognition does not establish a CONTEMPLATE lifecycle.",
    ),
)


def corpus_by_id() -> dict[str, BehaviorDecomposition]:
    return {case.behavior_id: case for case in BEHAVIOR_CORPUS}


def proposed_basis_usage() -> dict[str, tuple[str, ...]]:
    usage: dict[str, list[str]] = {skill: [] for skill in CANDIDATE_SKILL_BASIS}
    for case in BEHAVIOR_CORPUS:
        for skill in case.proposed_skills:
            usage[skill].append(case.behavior_id)
    return {skill: tuple(ids) for skill, ids in usage.items()}


def surviving_basis_usage() -> dict[str, tuple[str, ...]]:
    usage: dict[str, list[str]] = {skill: [] for skill in CANDIDATE_SKILL_BASIS}
    for case in BEHAVIOR_CORPUS:
        for skill in case.surviving_candidates:
            usage[skill].append(case.behavior_id)
    return {skill: tuple(ids) for skill, ids in usage.items()}


def open_basis_usage() -> dict[str, tuple[str, ...]]:
    usage: dict[str, list[str]] = {skill: [] for skill in CANDIDATE_SKILL_BASIS}
    for case in BEHAVIOR_CORPUS:
        for skill in case.open_candidates:
            usage[skill].append(case.behavior_id)
    return {skill: tuple(ids) for skill, ids in usage.items()}


def validate_corpus() -> tuple[str, ...]:
    errors: list[str] = []
    known_skills = set(CANDIDATE_SKILL_BASIS)
    ids: set[str] = set()

    if set(CANDIDATE_STATUS) != known_skills:
        errors.append("candidate status must classify every candidate exactly once")

    for case in BEHAVIOR_CORPUS:
        if case.behavior_id in ids:
            errors.append(f"duplicate behavior_id: {case.behavior_id}")
        ids.add(case.behavior_id)

        for field_name, values in (
            ("proposed_skills", case.proposed_skills),
            ("surviving_candidates", case.surviving_candidates),
            ("open_candidates", case.open_candidates),
        ):
            unknown = sorted(set(values) - known_skills)
            if unknown:
                errors.append(
                    f"{case.behavior_id}: unknown {field_name}={','.join(unknown)}"
                )

        unknown_primitives = sorted(set(case.primitives) - TARGET_PRIMITIVES)
        if unknown_primitives:
            errors.append(
                f"{case.behavior_id}: unknown primitives={','.join(unknown_primitives)}"
            )

        proposed = set(case.proposed_skills)
        surviving = set(case.surviving_candidates)
        open_ = set(case.open_candidates)
        if not surviving <= proposed:
            errors.append(
                f"{case.behavior_id}: surviving candidates must come from proposal"
            )
        if not open_ <= proposed:
            errors.append(f"{case.behavior_id}: open candidates must come from proposal")
        if surviving & open_:
            errors.append(
                f"{case.behavior_id}: candidate cannot be both surviving and open"
            )

        if not case.family.strip():
            errors.append(f"{case.behavior_id}: empty family")
        if not case.summary.strip():
            errors.append(f"{case.behavior_id}: empty summary")
        if not case.pressure.strip():
            errors.append(f"{case.behavior_id}: missing falsification pressure")

    return tuple(errors)
