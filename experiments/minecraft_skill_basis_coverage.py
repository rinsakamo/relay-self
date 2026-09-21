from __future__ import annotations

from dataclasses import dataclass

CANDIDATE_SKILL_BASIS: tuple[str, ...] = (
    "WAIT",
    "EAT",
    "FIGHT",
    "FLEE",
    "SEEK",
    "TALK",
    "CONTEMPLATE",
)

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

# Snapshot of the abstract primitive families reachable through the current
# Mineflayer effect surface at Issue #304 creation time. It is evidence for
# coverage bookkeeping only; the adapter remains authoritative for its actual
# protocol.
CURRENT_ADAPTER_PRIMITIVE_FIXTURE: frozenset[str] = frozenset(
    {
        "MOVE",
        "LOOK",
        "EQUIP",
        "CONSUME",
        "ATTACK",
    }
)


@dataclass(frozen=True, slots=True)
class BehaviorDecomposition:
    behavior_id: str
    family: str
    summary: str
    skills: tuple[str, ...]
    primitives: tuple[str, ...]
    owners: tuple[str, ...] = ()
    pressure: str = ""

    def missing_current_primitives(self) -> tuple[str, ...]:
        return tuple(
            primitive
            for primitive in self.primitives
            if primitive not in CURRENT_ADAPTER_PRIMITIVE_FIXTURE
        )


BEHAVIOR_CORPUS: tuple[BehaviorDecomposition, ...] = (
    BehaviorDecomposition(
        "hold_position",
        "inaction",
        "Remain in place without inventing an external intervention.",
        ("WAIT",),
        (),
        pressure="Does healthy inactivity need Skill semantics at all?",
    ),
    BehaviorDecomposition(
        "eat_available_food",
        "body_maintenance",
        "Consume an already available edible item.",
        ("EAT",),
        ("EQUIP", "CONSUME"),
        owners=("Body/resource state",),
        pressure="Can EAT reduce to SEEK(body improvement) + CONSUME?",
    ),
    BehaviorDecomposition(
        "direct_combat",
        "combat",
        "Attack a grounded hostile/adverse target.",
        ("FIGHT",),
        ("LOOK", "ATTACK"),
        owners=("Current Appraisal",),
        pressure="Can FIGHT reduce to SEEK(neutralized threat) + ATTACK?",
    ),
    BehaviorDecomposition(
        "escape_threat",
        "escape",
        "Increase separation from a grounded threat.",
        ("FLEE",),
        ("LOOK", "MOVE"),
        owners=("Current Appraisal",),
        pressure="Can FLEE reduce to SEEK(safety) + MOVE?",
    ),
    BehaviorDecomposition(
        "navigate_remembered_location",
        "navigation",
        "Travel toward a location already represented by owned cognition.",
        ("SEEK",),
        ("MOVE",),
        owners=("Memory",),
        pressure="Does navigation require a distinct reusable control Skill?",
    ),
    BehaviorDecomposition(
        "search_unknown_resource",
        "exploration",
        "Reduce uncertainty until a desired resource is observed or remains unresolved.",
        ("SEEK",),
        ("MOVE", "LOOK"),
        pressure="Can SEEK stay narrower than a generic GOAL/DO operator?",
    ),
    BehaviorDecomposition(
        "mine_and_craft_upgrade",
        "resource_processing",
        "Locate material, acquire it, and construct upgraded equipment.",
        ("SEEK", "CONTEMPLATE"),
        ("MOVE", "LOOK", "EQUIP", "BREAK", "TAKE", "CRAFT"),
        owners=("Memory", "Capability"),
        pressure="Missing BREAK/TAKE/CRAFT must not be misclassified as missing Skills.",
    ),
    BehaviorDecomposition(
        "build_shelter_before_night",
        "construction",
        "Form a design, obtain material/site access, and create a shelter.",
        ("CONTEMPLATE", "SEEK"),
        ("MOVE", "LOOK", "PLACE"),
        owners=("Time observation", "Inventory"),
        pressure="World-state construction is a hard counterexample to SEEK-only semantics.",
    ),
    BehaviorDecomposition(
        "farm_renewable_food",
        "resource_processing",
        "Establish, wait for, and harvest a renewable food process.",
        ("SEEK", "WAIT", "EAT"),
        ("MOVE", "USE", "PLACE", "BREAK", "TAKE", "EQUIP", "CONSUME"),
        owners=("Body/resource state",),
        pressure="Tests long-horizon composition without inventing FARM.",
    ),
    BehaviorDecomposition(
        "scout_and_report",
        "information_social",
        "Explore for relevant information and report it to another Self.",
        ("SEEK", "TALK"),
        ("MOVE", "LOOK", "CHAT_DELIVERY"),
        pressure="Tests SEEK -> TALK boundary crossing.",
    ),
    BehaviorDecomposition(
        "coordinate_two_agent_attack",
        "social_combat",
        "Exchange task-relevant language and converge on a shared combat target.",
        ("TALK", "SEEK", "FIGHT"),
        ("CHAT_DELIVERY", "MOVE", "LOOK", "ATTACK"),
        owners=("Other/Relationship cognition",),
        pressure="Must not require a hard-coded COOPERATE or ROLE Skill by name alone.",
    ),
    BehaviorDecomposition(
        "share_scarce_food",
        "social_resource",
        "Transfer a scarce body-maintenance resource to another Self.",
        ("TALK",),
        ("CHAT_DELIVERY", "TRANSFER"),
        owners=("Other/Relationship cognition", "Body/resource state"),
        pressure="Tests whether GIVE is primitive transfer rather than a peer Skill.",
    ),
    BehaviorDecomposition(
        "trade_resources",
        "social_resource",
        "Negotiate/exchange resources without introducing a TRADE Skill by name.",
        ("TALK", "SEEK"),
        ("CHAT_DELIVERY", "TRANSFER"),
        owners=("Other/Relationship cognition",),
        pressure="Tests whether TALK + transfer/acquisition is sufficient.",
    ),
    BehaviorDecomposition(
        "ambush_player",
        "social_combat",
        "Reach a useful position, wait, then attack another player.",
        ("SEEK", "WAIT", "FIGHT"),
        ("MOVE", "LOOK", "ATTACK"),
        pressure="Tests composition of timing, seeking, and antagonistic intervention.",
    ),
    BehaviorDecomposition(
        "retreat_and_regroup",
        "social_escape",
        "Escape a threat while re-establishing proximity/contact with a companion.",
        ("FLEE", "SEEK", "TALK"),
        ("MOVE", "LOOK", "CHAT_DELIVERY"),
        owners=("Other/Relationship cognition",),
        pressure="Tests simultaneous escape and social target constraints.",
    ),
    BehaviorDecomposition(
        "escort_companion",
        "social_navigation",
        "Maintain useful proximity to a companion and respond to threats.",
        ("SEEK", "FIGHT", "FLEE", "TALK"),
        ("MOVE", "LOOK", "ATTACK", "CHAT_DELIVERY"),
        owners=("Other/Relationship cognition",),
        pressure="Tests FOLLOW/GUARD as compositions rather than initial Skills.",
    ),
    BehaviorDecomposition(
        "rescue_companion_under_attack",
        "social_combat",
        "Locate a companion/threat and intervene under viability pressure.",
        ("SEEK", "FIGHT", "TALK"),
        ("MOVE", "LOOK", "ATTACK", "CHAT_DELIVERY"),
        owners=("Other/Relationship cognition", "Current Appraisal"),
        pressure="Tests RESCUE as composition rather than a named Skill.",
    ),
    BehaviorDecomposition(
        "construct_operate_mechanism",
        "construction",
        "Design, assemble, and operate a multi-part mechanism.",
        ("CONTEMPLATE", "SEEK"),
        ("MOVE", "LOOK", "PLACE", "USE"),
        owners=("Memory", "Capability"),
        pressure="Pressures CREATE/BUILD and target interaction boundaries.",
    ),
    BehaviorDecomposition(
        "recover_after_respawn",
        "recovery",
        "After environment-driven respawn, recover toward a remembered useful state.",
        ("SEEK",),
        ("MOVE", "LOOK", "TAKE"),
        owners=("Persistent Cognition", "World observation"),
        pressure="Respawn is a World event; recovery must not become a special Skill by default.",
    ),
    BehaviorDecomposition(
        "learn_from_failed_route_or_fight",
        "learning",
        "Integrate grounded consequence so later reduction can differ.",
        (),
        (),
        owners=("Experience Integration", "Memory", "Capability"),
        pressure="Not every meaningful adaptive process should be forced into the Skill basis.",
    ),
    BehaviorDecomposition(
        "plan_multi_step_expedition",
        "internal_cognition",
        "Construct and compare a hypothetical multi-step expedition before acting.",
        ("CONTEMPLATE",),
        (),
        owners=("Memory", "Capability", "Current Intent"),
        pressure="Can existing OPEN/THINK/ Retrieval make CONTEMPLATE redundant?",
    ),
    BehaviorDecomposition(
        "deceive_other_through_language",
        "social_cognition",
        "Generate an intentionally misleading expression for another agent.",
        ("CONTEMPLATE", "TALK"),
        ("CHAT_DELIVERY",),
        owners=("Other/Relationship cognition",),
        pressure="Tests human-like composition without introducing DECEIVE.",
    ),
    BehaviorDecomposition(
        "create_novel_structure",
        "construction",
        "Generate a novel internal design and realize it through target primitives.",
        ("CONTEMPLATE", "SEEK"),
        ("MOVE", "LOOK", "PLACE"),
        pressure="Strong pressure on whether CONTEMPLATE is distinct from ordinary cognition.",
    ),
)


CANDIDATE_ABLATION_WITNESSES: dict[str, str] = {
    "WAIT": "hold_position",
    "EAT": "eat_available_food",
    "FIGHT": "direct_combat",
    "FLEE": "escape_threat",
    "SEEK": "search_unknown_resource",
    "TALK": "coordinate_two_agent_attack",
    "CONTEMPLATE": "create_novel_structure",
}


def corpus_by_id() -> dict[str, BehaviorDecomposition]:
    return {case.behavior_id: case for case in BEHAVIOR_CORPUS}


def basis_usage() -> dict[str, tuple[str, ...]]:
    usage: dict[str, list[str]] = {skill: [] for skill in CANDIDATE_SKILL_BASIS}
    for case in BEHAVIOR_CORPUS:
        for skill in case.skills:
            usage[skill].append(case.behavior_id)
    return {skill: tuple(ids) for skill, ids in usage.items()}


def validate_corpus() -> tuple[str, ...]:
    errors: list[str] = []
    known_skills = set(CANDIDATE_SKILL_BASIS)
    ids: set[str] = set()

    for case in BEHAVIOR_CORPUS:
        if case.behavior_id in ids:
            errors.append(f"duplicate behavior_id: {case.behavior_id}")
        ids.add(case.behavior_id)

        unknown_skills = sorted(set(case.skills) - known_skills)
        if unknown_skills:
            errors.append(
                f"{case.behavior_id}: unknown basis Skills={','.join(unknown_skills)}"
            )

        unknown_primitives = sorted(set(case.primitives) - TARGET_PRIMITIVES)
        if unknown_primitives:
            errors.append(
                f"{case.behavior_id}: unknown primitives={','.join(unknown_primitives)}"
            )

        if not case.family.strip():
            errors.append(f"{case.behavior_id}: empty family")
        if not case.summary.strip():
            errors.append(f"{case.behavior_id}: empty summary")
        if not case.pressure.strip():
            errors.append(f"{case.behavior_id}: missing falsification pressure")

    for skill, witness_id in CANDIDATE_ABLATION_WITNESSES.items():
        if skill not in known_skills:
            errors.append(f"ablation witness for unknown Skill: {skill}")
            continue
        witness = corpus_by_id().get(witness_id)
        if witness is None:
            errors.append(f"{skill}: missing witness behavior {witness_id}")
        elif skill not in witness.skills:
            errors.append(
                f"{skill}: witness {witness_id} does not use the candidate Skill"
            )

    missing_witnesses = known_skills - set(CANDIDATE_ABLATION_WITNESSES)
    if missing_witnesses:
        errors.append(
            "basis Skills without candidate ablation witness: "
            + ",".join(sorted(missing_witnesses))
        )

    return tuple(errors)
