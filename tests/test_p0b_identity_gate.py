"""Synthetic pre-issue identity gate examples; no World actions."""
import json

import pytest

from experiments.cognitive_physical_attack_issue_dev import PhysicalAttackRefusal
from experiments.cognitive_physical_attack_runner import check_p0b_identity_witness


def test_same_probe_identity_required(tmp_path):
    actor = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    target = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
    expected = tmp_path / "expected.json"
    witness = tmp_path / "native.jsonl"
    expected.write_text(json.dumps({"actor_uuid": actor, "target_uuid": target}))
    row = {"session_id": "s", "probe_seq": 8, "actor": {"id": 2, "uuid": actor},
           "targets": [{"id": 9, "uuid": target}]}
    witness.write_text(json.dumps(row) + "\n")
    check_p0b_identity_witness(witness, expected, session_id="s", seq=8, target_id=9)
    for session, seq, entity in (("other", 8, 9), ("s", 7, 9), ("s", 8, 10)):
        with pytest.raises(PhysicalAttackRefusal):
            check_p0b_identity_witness(witness, expected, session_id=session, seq=seq, target_id=entity)
    row["targets"][0]["uuid"] = actor
    witness.write_text(json.dumps(row) + "\n")
    with pytest.raises(PhysicalAttackRefusal):
        check_p0b_identity_witness(witness, expected, session_id="s", seq=8, target_id=9)
