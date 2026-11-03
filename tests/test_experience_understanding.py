"""L-EU offline source and relation graph tests. No memory/learning admission."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from relay_self.experience_understanding import (
    EULedger,
    EUPairRejected,
    Experience,
    PairLink,
    Understanding,
    decode_ledger,
    encode_ledger,
)
from tools.l_eu_pair_z2c_original_replay import build_z2c_eu_ledger

REPO = Path(__file__).resolve().parents[1]
WORLD_ID = "0c73cad5-ad84-4112-a708-4a1fb9ff9fc4"
SHA_A = "a" * 64
SHA_B = "b" * 64


def experience(eid="E_A"):
    return Experience(eid, SHA_A, "docs/original.raw", "WORLD_OUTCOME",
                      "ARCHIVED_REPLAY_VERIFIED", WORLD_ID,
                      "Observed new physical movement in an archived World.",
                      "PAPER_T10_TO_T30")


def understanding(uid="U_A", *, parent=(), evid=("E_A",)):
    return Understanding(
        understanding_id=uid,
        stage="ORIGINAL_HYPOTHESIS" if not parent else "POST_OUTCOME_REINTERPRETATION",
        original_response_sha256=SHA_B,
        source_kind="MODEL_RAW",
        source_strategy="STATIONARY",
        original_decision="ORIGINAL_FORECAST_SELECTION",
        original_speed_m_per_tick=None,
        applicability="CONDITIONS_UNRESOLVED",
        reason_original="Previous model asserted a stationary candidate.",
        falsification_original="If future motion exceeds threshold, retest STATIONARY.",
        parent_ids=parent,
        evidence_ids=evid,
    )


def connected():
    return (
        EULedger("eu-demo").add_experience(experience())
        .add_understanding(understanding())
        .link(PairLink("E_A", "U_A", "TESTED_BY", "UNTESTED",
                       SHA_A, "FIXTURE_NOT_REAL_WORLD",
                       "A source-linked interpretation, no authority."))
    )


def test_basic_pair_is_immutable_and_has_no_memory_learning_or_action_authority():
    ledger = connected()
    initial = ledger.add_experience(experience("E_B"))
    assert len(ledger.experiences) == 1 and len(initial.experiences) == 2
    assert ledger.understandings[0].source_strategy == "STATIONARY"
    assert ledger.memory_commits == ledger.habit_promotions == 0
    assert ledger.action_authority is ledger.learning_admitted is ledger.science_qualified is False
    assert ledger.interpretations_for("E_A") == ledger.understandings
    with pytest.raises(EUPairRejected):
        ledger.interpretations_for("E_UNKNOWN")
    with pytest.raises(AttributeError):
        ledger.understandings[0].reason_original = "overwrite"


def test_one_experience_many_competing_understandings_and_revision_graph():
    ledger = connected()
    u = understanding("U_B", parent=("U_A",))
    revised_ledger = ledger.add_understanding(u).link(
        PairLink("E_A", "U_B", "REVISES_ABOUT", "PROPOSAL_NOT_ADMITTED",
                 SHA_B, "MODEL_SOURCE_TEST", "New candidate, old one retained.")
    )
    assert revised_ledger.understandings == (ledger.understandings[0], u)
    assert len(revised_ledger.interpretations_for("E_A")) == 2
    assert revised_ledger.links[0].review == "UNTESTED"
    assert not revised_ledger.learning_admitted
    with pytest.raises(EUPairRejected, match="preceding"):
        EULedger("eu-a", (experience(),), (u, ledger.understandings[0]))


@pytest.mark.parametrize("bad", [
    dict(source_sha256="A"*64),
    dict(source_sha256="not-sha"),
    dict(source_path="../../passwd"),
    dict(source_path="/tmp/forged"),
    dict(source_status="QUALIFIED_PHYSICALLY"),
    dict(source_kind="UNSUPPORTED"),
    dict(world_uuid="white space"),
])
def test_invalid_original_experience_rejected(bad):
    with pytest.raises(EUPairRejected):
        replace(experience(), **bad)


@pytest.mark.parametrize("bad", [
    dict(source_strategy=""),
    dict(original_decision=""),
    dict(original_speed_m_per_tick=True),
    dict(original_speed_m_per_tick=float("nan")),
    dict(original_speed_m_per_tick=-0.1),
    dict(original_response_sha256="wrong"),
    dict(epistemic_status="ACCEPTED_LEARNING"),
    dict(parent_ids=("U_A",)),
    dict(evidence_ids=()),
    dict(evidence_ids=("E_A", "E_A")),
])
def test_invalid_understanding_and_self_learning_rejected(bad):
    with pytest.raises(EUPairRejected):
        replace(understanding(), **bad)


def test_unbound_and_duplicate_references_rejected():
    ledger = connected()
    with pytest.raises(EUPairRejected, match="duplicate experience"):
        ledger.add_experience(experience())
    with pytest.raises(EUPairRejected, match="duplicate understanding"):
        ledger.add_understanding(understanding())
    with pytest.raises(EUPairRejected, match="duplicate pair"):
        ledger.link(ledger.links[0])
    with pytest.raises(EUPairRejected, match="endpoint"):
        ledger.link(replace(ledger.links[0], experience_id="E_B"))
    with pytest.raises(EUPairRejected, match="missing original experience"):
        ledger.add_understanding(understanding("U_B", parent=("U_A",), evid=("E_B",)))


@pytest.mark.parametrize("bad", [
    dict(memory_commits=1), dict(habit_promotions=1),
    dict(action_authority=True), dict(learning_admitted=True),
    dict(science_qualified=True),
])
def test_ledger_cannot_create_learning_or_action_admission(bad):
    with pytest.raises(EUPairRejected, match="cannot own"):
        replace(connected(), **bad)


def test_roundtrip_canonical_sha_and_duplicate_json_field_fail_closed():
    source = connected()
    original = encode_ledger(source)
    assert decode_ledger(original) == source
    assert encode_ledger(decode_ledger(original)) == original
    with pytest.raises(EUPairRejected):
        decode_ledger(original + b" ")
    tampered = json.loads(original)
    tampered["payload"]["ledger"]["understandings"][0]["reason_original"] = "FORGED"
    with pytest.raises(EUPairRejected):
        decode_ledger(json.dumps(tampered).encode() + b"\n")
    with pytest.raises(EUPairRejected):
        decode_ledger(original.replace(b'"schema":', b'"schema":"forged","schema":', 1))


def test_actual_archived_z2b_z2c_eu_pair_replay_without_any_new_real_actions():
    graph = build_z2c_eu_ledger(REPO)
    assert len(graph.experiences) == 2
    assert len(graph.understandings) == 2
    assert len(graph.links) == 3
    assert graph.experiences[0].world_uuid == WORLD_ID
    assert graph.experiences[0].source_sha256 == (
        "1c20c9e7aa456cdf163edf56a3caab3eead2431febb3f40743896054730e4815"
    )
    assert graph.experiences[1].source_sha256 == (
        "66e47bcf99f72fea9e32ca49ad3dc806cd5794f56d6fbdb050a6c97b7ee51a78"
    )
    h1, h2 = graph.understandings
    assert h1.source_strategy == "STATIONARY"
    assert "CONSTANT_VELOCITY" in h1.falsification_original
    assert h2.parent_ids == (h1.understanding_id,)
    assert h2.source_strategy == "TARGET_APPROACH"
    assert h2.original_decision == "ABSTAIN_PENDING_MORE_EVIDENCE"
    assert h2.original_speed_m_per_tick is None
    assert h1.original_decision == "ORIGINAL_FORECAST_SELECTION"
    assert h2.epistemic_status == "UNADMITTED_MODEL_CLAIM"
    assert graph.links[-1].review == "NUMERIC_LIMITED_SEMANTIC_FAIL"
    assert graph.links[-1].review_provenance == "HOST_SEMANTIC_REVIEW_NOT_INDEPENDENT"
    assert not graph.learning_admitted
    assert decode_ledger(encode_ledger(graph)) == graph


def test_missing_archived_response_fails_before_pair_build(tmp_path):
    root = tmp_path / "copy"
    shutil.copytree(REPO / "docs/evidence/l-z2b-real-20261102",
                    root / "docs/evidence/l-z2b-real-20261102")
    shutil.copytree(REPO / "docs/evidence/l-z2c-real-h2-20261103",
                    root / "docs/evidence/l-z2c-real-h2-20261103")
    bad = root / "docs/evidence/l-z2c-real-h2-20261103/h2-original/h2-response-1.raw.json"
    bad.write_bytes(bad.read_bytes() + b"\n")
    with pytest.raises(ValueError):
        build_z2c_eu_ledger(root)


def test_eu_builder_cli_creates_exclusive_only_shadow_receipt(tmp_path):
    out = tmp_path / "eu-ledger.json"
    cmd = [
        sys.executable, "-m", "tools.l_eu_pair_z2c_original_replay",
        "--repo", str(REPO), "--output", str(out),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr
    receipt = json.loads(proc.stdout)
    assert receipt["status"] == "EU_SHADOW_ORIGINAL_REPLAY_PASS_NO_ADMISSION"
    assert receipt["experiences"] == 2 and receipt["understandings"] == 2
    assert receipt["learning_updates"] == receipt["worlds_started"] == 0
    assert decode_ledger(out.read_bytes()) == build_z2c_eu_ledger(REPO)
    assert subprocess.run(cmd, capture_output=True, check=False).returncode == 2



def test_tampered_host_semantic_review_does_not_become_verified_experience(tmp_path):
    root = tmp_path / "copy"
    shutil.copytree(REPO / "docs/evidence/l-z2b-real-20261102",
                    root / "docs/evidence/l-z2b-real-20261102")
    shutil.copytree(REPO / "docs/evidence/l-z2c-real-h2-20261103",
                    root / "docs/evidence/l-z2c-real-h2-20261103")
    hostile = root / "docs/evidence/l-z2c-real-h2-20261103/semantic-review.json"
    original = hostile.read_bytes()
    hostile.write_bytes(original.replace(b'"FAIL"', b'"PASS"'))
    with pytest.raises(EUPairRejected, match="manifest mismatch"):
        build_z2c_eu_ledger(root)
    assert (REPO / "docs/evidence/l-z2c-real-h2-20261103/semantic-review.json").read_bytes() == original
