"""Accepted Schema Presets survive only as bounded inert cognition knowledge.

All tests are deterministic offline and use the real PersistentCognition file
writer/reader, not physical Action grants or an actual Paper World.
"""
from __future__ import annotations

import json
from dataclasses import replace

import pytest

from adapters.mineflayer.python_protocol import MineflayerPosition
from relay_self.cognitive_minimal_dev import (
    AcceptedSkillPreset,
    Origin,
    PatternKind,
    PatternRegistry,
    Predicate,
    PresetAcceptanceReceipt,
    SchemaPattern,
    accept_skill_parameter_preset,
    initial_patterns,
)
from relay_self.initial_skill_ir import initial_skill_definitions
from relay_self.persistent_cognition import (
    IdentitySpecification,
    InvalidPersistentCognitionData,
    PersistentCognition,
    load_persistent_cognition,
    save_persistent_cognition,
)
from relay_self.preset_checkpoint_recovery_dev import (
    reconcile_restored_self_schema,
    reconcile_restored_self_schema_file,
)
from relay_self.preset_registry_checkpoint import (
    PresetCheckpointRefusal,
    decode_pattern_registry,
    encode_pattern_registry,
)
from relay_self.provenance import Provenance
from relay_self.skill_invocation import (
    ArgumentKind,
    SkillArgument,
    SkillBudget,
    SkillConstraints,
    SkillCostEstimate,
    SkillParameterPreset,
    SkillTarget,
)

SOURCE = Provenance("Self", "accepted-preset")
DEF = {(d.skill_id, d.version): d for d in initial_skill_definitions()}


def registry_for_self(self_id="self-A"):
    r = initial_patterns()
    d = DEF[("EAT", 1)]
    p = SkillParameterPreset(
        "hunger-eat", "BreadV1", 1, d.definition_ref,
        SkillConstraints((SkillArgument("item_available", ArgumentKind.FLAG, True),)),
        SkillBudget(2, 1800, 3.0, 12), SOURCE,
        expected_cost=SkillCostEstimate(1, 700, 1.5),
    )
    return accept_skill_parameter_preset(
        r, p, definition=d,
        receipt=PresetAcceptanceReceipt(
            self_id, "event-001", p.preset_ref, SOURCE,
        ),
        accepted_by_self=True, expected_revision=r.revision,
        available_skills=frozenset({("EAT", 1)}),
    )


def cognition(self_id="self-A", registry=None):
    return PersistentCognition(
        identity=IdentitySpecification(
            self_id, ("Protect agency and revise beliefs using evidence.",),
            Provenance("SOUL", "initial-v1"),
        ),
        pattern_registry=registry,
    )


def test_actual_self_cognition_file_retains_registry_and_same_self_receipts(tmp_path):
    source = registry_for_self()
    old = cognition(registry=initial_patterns())
    retained = old.retain_schema_registry(source, expected_revision=0)
    assert old.pattern_registry.revision == 0
    path = tmp_path / "cognition.json"
    save_persistent_cognition(path, retained)
    raw = json.loads(path.read_text())
    assert raw["schema_version"] == 3
    assert raw["pattern_registry"]["schema"] == 2
    assert raw["pattern_registry"]["self_id"] == "self-A"
    assert raw["pattern_registry"]["accepted_presets"][0]["preset"]["preset_ref"].startswith(
        "skill-preset:v1@"
    )
    after = load_persistent_cognition(path)
    assert after.pattern_registry == retained.pattern_registry
    assert after.identity == retained.identity
    assert after.pattern_registry.accepted_presets[0].receipt.event_id == "event-001"
    assert after.pattern_registry.accepted_presets[0].preset.expected_cost.duration_ms == 700


def test_registry_roundtrip_supports_typed_positions_and_targets():
    d = DEF[("MOVE", 1)]
    p = SkillParameterPreset(
        "exploration-move", "Step", 1, d.definition_ref,
        SkillConstraints((SkillArgument("max_slope", ArgumentKind.NUMBER, 0.5),)),
        SkillBudget(4, 5000, 6.0), SOURCE,
        arguments=(
            SkillArgument("direction", ArgumentKind.POSITION,
                          MineflayerPosition(1.25, 65, -0.5)),
            SkillArgument("alternate", ArgumentKind.TARGET,
                          SkillTarget("destination:alternate", "DESTINATION")),
            SkillArgument("optional_flag", ArgumentKind.FLAG, False),
            SkillArgument("trace", ArgumentKind.REFERENCE, "example-ref"),
        ),
    )
    schema = initial_patterns()
    move = SchemaPattern(
        "exploration-move", 1, "exploration", PatternKind.GOAL,
        Predicate.EXPLORE, "EXPLORE_WORLD", "MOVE", 1, "DESTINATION",
        Origin.INNATE, SOURCE,
    )
    registry = PatternRegistry(
        1, schema.patterns + (move,),
        (AcceptedSkillPreset(1, p, PresetAcceptanceReceipt(
            "self-A", "test-move", p.preset_ref, SOURCE,
        )),),
    )
    wire = encode_pattern_registry(registry, self_id="self-A")
    assert decode_pattern_registry(wire, expected_self_id="self-A") == registry
    assert encode_pattern_registry(
        decode_pattern_registry(wire, expected_self_id="self-A"),
        self_id="self-A",
    ) == wire


def test_owner_cut_and_persistent_cognition_must_match_before_inert_rehydrate(tmp_path):
    registry = registry_for_self()
    path = tmp_path / "cognition.json"
    save_persistent_cognition(path, cognition(registry=registry))
    cut_wire = encode_pattern_registry(registry, self_id="self-A")
    inert = reconcile_restored_self_schema_file(
        path, owner_cut_pattern_registry=cut_wire, expected_self_id="self-A",
    )
    assert inert.registry == registry
    assert inert.prior_registry_revision == registry.revision
    assert inert.new_worldbody_observation_required
    assert not inert.old_target_current
    assert not inert.old_intent_or_skill_resume_authorized
    assert not inert.old_llm_output_current
    assert not inert.native_action_issue_authorized

    different = replace(registry, revision=registry.revision + 1)
    with pytest.raises(PresetCheckpointRefusal, match="disagree"):
        reconcile_restored_self_schema(
            cognition(registry=registry), expected_self_id="self-A",
            owner_cut_pattern_registry=encode_pattern_registry(
                different, self_id="self-A",
            ),
        )
    with pytest.raises(PresetCheckpointRefusal, match="missing"):
        reconcile_restored_self_schema(
            cognition(), expected_self_id="self-A",
            owner_cut_pattern_registry=cut_wire,
        )


@pytest.mark.parametrize("mutation", [
    lambda b: b.update(self_id="self-B"),
    lambda b: b.update(schema=1),
    lambda b: b["accepted_presets"][0]["preset"].update(version=9),
    lambda b: b["accepted_presets"][0]["receipt"].update(event_id=""),
    lambda b: b["accepted_presets"][0]["preset"]["budget"].update(max_actions=900),
    lambda b: b["patterns"][0].update(skill_id="MOVE"),
    lambda b: b.pop("accepted_presets"),
    lambda b: b["accepted_presets"][0]["preset"].update(unknown_field="BAD"),
])
def test_wrong_self_or_corrupt_preset_checkpoint_fails_closed(mutation, tmp_path):
    path = tmp_path / "cognition.json"
    save_persistent_cognition(path, cognition(registry=registry_for_self()))
    record = json.loads(path.read_text())
    mutation(record["pattern_registry"])
    path.write_text(json.dumps(record))
    with pytest.raises((InvalidPersistentCognitionData, PresetCheckpointRefusal,
                        ValueError)):
        load_persistent_cognition(path)


def test_v1_and_v2_cognition_migration_never_invents_accepted_presets(tmp_path):
    path = tmp_path / "old.json"
    save_persistent_cognition(path, cognition())
    record = json.loads(path.read_text())
    record["schema_version"] = 2
    del record["pattern_registry"]
    path.write_text(json.dumps(record))
    v2 = load_persistent_cognition(path)
    assert v2.pattern_registry is None
    record["schema_version"] = 1
    del record["appraisal_dispositions"]
    path.write_text(json.dumps(record))
    v1 = load_persistent_cognition(path)
    assert v1.pattern_registry is None
    with pytest.raises(PresetCheckpointRefusal, match="missing"):
        reconcile_restored_self_schema(
            v1, owner_cut_pattern_registry=encode_pattern_registry(
                registry_for_self(), self_id="self-A",
            ), expected_self_id="self-A",
        )


def test_cross_self_snapshot_and_forged_cut_never_rehydrate():
    a = registry_for_self("self-A")
    b = registry_for_self("self-B")
    with pytest.raises(InvalidPersistentCognitionData, match="foreign"):
        cognition(self_id="self-B", registry=a)
    with pytest.raises(PresetCheckpointRefusal, match="wrong Self"):
        decode_pattern_registry(
            encode_pattern_registry(a, self_id="self-A"),
            expected_self_id="self-B",
        )
    with pytest.raises(PresetCheckpointRefusal, match="wrong Self"):
        reconcile_restored_self_schema(
            cognition(registry=a),
            owner_cut_pattern_registry=encode_pattern_registry(b, self_id="self-B"),
            expected_self_id="self-A",
        )


def test_retaining_registry_requires_cas_and_cannot_roll_back_revision():
    start = cognition(registry=registry_for_self())
    future = replace(start.pattern_registry, revision=2)
    with pytest.raises(InvalidPersistentCognitionData, match="stale"):
        start.retain_schema_registry(future, expected_revision=0)
    with pytest.raises(InvalidPersistentCognitionData, match="stale"):
        start.retain_schema_registry(
            replace(future, revision=1), expected_revision=1,
        )
    next_one = start.retain_schema_registry(future, expected_revision=1)
    assert next_one.pattern_registry.revision == 2
    assert start.pattern_registry.revision == 1
