"""Negative-first conformance for I0's offline-only, no-production gate."""

import ast
import copy
import itertools
import json
import subprocess
import sys
from pathlib import Path

import pytest

from experiments import ac_integration_i0_gate as gate


@pytest.fixture
def manifest():
    return gate.strict_json(gate.DEFAULT_MANIFEST.read_text(encoding="utf-8"))


def pointers(manifest):
    return [
        {key: row[key] for key in ("lane", "issue", "pr", "head", "ci_run", "evidence")}
        for row in manifest["lanes"]
    ]


def test_canonical_freeze_and_scoped_outputs(manifest):
    assert gate.digest(manifest) == gate.FROZEN_SHA256
    result = gate.reconcile(manifest)
    assert result["classification"] == "I0_OFFLINE_READ_ONLY_RECONCILED"
    assert result["manifest_sha256"] == gate.FROZEN_SHA256
    assert result["joint_runtime_go"] is False
    assert result["production_selector_go"] is False
    assert result["physical_world_effect"] == "UNDETERMINED"
    assert result["retained_update"] == "NOT_ATTESTED"
    assert result["source_authentication"] == "NOT_PROVIDED_BY_LEDGER"
    assert result["grand_null"] == "SIMPLE_GATE_SUFFICIENT_UNDER_FROZEN_UTILITY"


def test_exact_pointers_are_order_invariant_not_source_attestation(manifest):
    for permutation in itertools.permutations(pointers(manifest)):
        assert gate.reconcile(manifest, list(permutation))["joint_runtime_go"] is False


@pytest.mark.parametrize(
    "change",
    [
        lambda p: p.pop(),
        lambda p: p.append(copy.deepcopy(p[0])),
        lambda p: p[0].update({"head": "0" * 40}),
        lambda p: p[0].update({"ci_run": p[1]["ci_run"]}),
        lambda p: p[1].update({"pr": p[0]["pr"]}),
        lambda p: p[2].update({"issue": True}),
        lambda p: p[1].update({"source_session": "fake-native-session"}),
        lambda p: p[2].update({"approved": True}),
        lambda p: p[0].update({"physical_pass": True}),
        lambda p: p[2].update({"production_go": True}),
    ],
)
def test_untrusted_pointer_mutations_rejected(manifest, change):
    presented = pointers(manifest)
    change(presented)
    with pytest.raises(gate.EvidenceRejected):
        gate.reconcile(manifest, presented)


@pytest.mark.parametrize(
    "lane,key,value",
    [
        ("A", "physical_trials", 36),
        ("A", "physical_trials", True),
        ("A", "physical_effect", "PHYSICAL_PASS"),
        ("A", "cheap_comparator", "NONE"),
        ("B", "physical_source_actions", 8),
        ("B", "learning_commit", "APPROVED"),
        ("B", "handoff", "AUTHORITATIVE_HABIT"),
        ("B", "feedback_direction", "POSITIVE"),
        ("C", "simple_gate_utility_tenths", 0),
        ("C", "resource_utility_tenths", 90000),
        ("C", "physical_compute", "MEASURED_GPU_JOULES"),
        ("C", "production_selector", "APPROVED"),
        ("C", "resource_correct", 1440),
        ("C", "heldout_opportunities", 1440.0),
        ("C", "ci_run", 0),
    ],
)
def test_fabricated_authority_and_altered_results_rejected(manifest, lane, key, value):
    mutant = copy.deepcopy(manifest)
    next(r for r in mutant["lanes"] if r["lane"] == lane)[key] = value
    with pytest.raises(gate.EvidenceRejected):
        gate.validate_manifest(mutant, check_digest=False)


@pytest.mark.parametrize(
    "key,value",
    [
        ("joint_runtime_go", True),
        ("production_selector_go", True),
        ("physical_world_effect", "PHYSICAL_PASS"),
        ("retained_update", "QUALIFIED"),
        ("owner_issue", True),
        ("baseline_main", "new-branch"),
        ("version", "AC-INTEGRATION-I1-v1"),
    ],
)
def test_joint_authority_laundering_rejected(manifest, key, value):
    mutant = copy.deepcopy(manifest)
    mutant[key] = value
    with pytest.raises(gate.EvidenceRejected):
        gate.validate_manifest(mutant, check_digest=False)


def test_schema_rejects_missing_extra_lane_and_reordered_manifest_digest(manifest):
    mutant = copy.deepcopy(manifest)
    mutant["lanes"] = [mutant["lanes"][1], mutant["lanes"][0], mutant["lanes"][2]]
    with pytest.raises(gate.EvidenceRejected, match="SHA256"):
        gate.validate_manifest(mutant)
    mutant = copy.deepcopy(manifest)
    mutant["lanes"][1]["unobserved_counterfactual"] = "SAFE"
    with pytest.raises(gate.EvidenceRejected):
        gate.validate_manifest(mutant, check_digest=False)
    mutant = copy.deepcopy(manifest)
    mutant["lanes"] = [mutant["lanes"][0]] * 3
    with pytest.raises(gate.EvidenceRejected):
        gate.validate_manifest(mutant, check_digest=False)
    mutant = copy.deepcopy(manifest)
    mutant["forbidden_promotions"].pop()
    with pytest.raises(gate.EvidenceRejected):
        gate.validate_manifest(mutant, check_digest=False)


@pytest.mark.parametrize(
    "text",
    [
        '{"x":1,"x":2}',
        '{"value":NaN}',
        '{"value":Infinity}',
        '{"value":-Infinity}',
        "not-json",
    ],
)
def test_json_parser_rejects_duplicates_nonfinite_or_non_json(text):
    with pytest.raises(gate.EvidenceRejected):
        gate.strict_json(text)


@pytest.mark.parametrize("requested", ["runtime", "action", "learning", "L0", "physical"])
def test_no_runtime_promotion_even_with_all_frozen_pointers(manifest, requested):
    with pytest.raises(gate.PromotionDenied):
        gate.reconcile(manifest, pointers(manifest), request=requested)


def test_cli_exit_codes_and_stable_offline_output(tmp_path, manifest):
    script = Path(gate.__file__)
    okay = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
    denied = subprocess.run(
        [sys.executable, str(script), "--request", "runtime"], capture_output=True, text=True
    )
    invalid_path = tmp_path / "invalid.json"
    invalid_path.write_text('{"x":1,"x":2}', encoding="utf-8")
    invalid = subprocess.run(
        [sys.executable, str(script), "--manifest", str(invalid_path)],
        capture_output=True,
        text=True,
    )
    assert okay.returncode == 0
    assert json.loads(okay.stdout) == gate.reconcile(manifest)
    assert denied.returncode == 3
    assert json.loads(denied.stdout)["classification"] == "I0_PROMOTION_DENIED"
    assert invalid.returncode == 2
    assert json.loads(invalid.stdout)["classification"] == "I0_REJECTED"


def test_no_runtime_sibling_imports_or_action_calls():
    source = Path(gate.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    module_imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            module_imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module_imports.add((node.module or "").split(".")[0])
    assert module_imports <= {"__future__", "argparse", "hashlib", "json", "pathlib", "typing"}
    assert "ActionSupervisor" not in source
    assert "Mineflayer" not in source
    assert "LearningUpdateAuthority" not in source
