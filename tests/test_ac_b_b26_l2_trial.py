"""B26 source-only actual World trials, mock transport only (NO real L2 in CI)."""
from __future__ import annotations

import json
from dataclasses import replace

import pytest

from experiments.ac_b_b24_structural_transfer import ANCHORS, HELDOUT, StructuralWorld
from experiments.ac_b_b26_l2_trial import (
    InvalidB26Proposal,
    _local_endpoint,
    cheap_anf,
    evaluate_frozen_proposal,
    examples_only,
    main,
    parse_and_qualify,
    predict,
    prompt_messages,
    run_local_one_call,
    train_original_world,
)

# These two fixture vectors are NOT outputs of any actual L2.
NORMAL = tuple(int(i in (1, 2, 3, 4, 8)) for i in range(16))
TWIN = tuple(NORMAL[i] ^ int(i in (7, 11, 13, 14, 15)) for i in range(16))


def original_train():
    first = StructuralWorld("b26-train-normal", twin=False)
    other = StructuralWorld("b26-train-twin", twin=True)
    n = train_original_world(first)
    t = train_original_world(other)
    return first, n, other, t


def injected(bits, examples):
    return parse_and_qualify(
        json.dumps({"coefficients": list(bits)}), examples,
        source="B26_TEST_ONLY_INJECTED",
    )


def test_original_issued_training_actions_identical_normal_and_twin():
    nworld, n, tworld, t = original_train()
    assert len(n) == len(t) == 11
    assert nworld.actions_executed == tworld.actions_executed == 16
    assert examples_only(n) == examples_only(t)
    assert tuple(x.cue for x in n) == ANCHORS
    for world, data in ((nworld, n), (tworld, t)):
        assert len({o.event_id for x in data for o in x.original_outcomes}) == 16
        assert all(
            world.observed(o) and o.cue == x.cue
            for x in data for o in x.original_outcomes
        )
        assert all(
            x.original_outcomes[-1].succeeded
            and x.original_outcomes[-1].action == x.winner
            for x in data
        )
        assert sum(len(x.original_outcomes) == 2 for x in data) == 5


def test_llm_prompt_is_byte_identical_across_laws_and_no_hidden_targets():
    _, n, _, t = original_train()
    assert prompt_messages(n) == prompt_messages(t)
    p = prompt_messages(n)
    assert [x["role"] for x in p] == ["system", "user"]
    assert "NORMAL" not in json.dumps(p)
    assert "TWIN" not in json.dumps(p)
    assert "H1_HIGHER_ORDER" not in json.dumps(p)
    data = json.loads(p[1]["content"])
    assert sorted(data) == [
        "feature_names", "instruction", "observations", "representation",
    ]
    assert data["feature_names"] == ["a", "b", "c", "d"]
    assert len(data["observations"]) == 11
    assert {tuple(e["features"]) for e in data["observations"]} == set(ANCHORS)
    assert not any(
        tuple(e["features"]) in HELDOUT for e in data["observations"]
    )


def test_two_structures_both_fit_original_training_and_cheap_coeff():
    _, n, _, t = original_train()
    assert injected(NORMAL, n).coefficients == NORMAL
    assert injected(TWIN, n).coefficients == TWIN
    assert injected(TWIN, t).coefficients == TWIN
    assert cheap_anf(n).coefficients == cheap_anf(t).coefficients == NORMAL
    assert all(predict(NORMAL, c) == predict(TWIN, c) for c in ANCHORS)
    assert all(predict(NORMAL, c) != predict(TWIN, c) for c in HELDOUT)


@pytest.mark.parametrize("bits,expected", [
    (NORMAL, (5, 0)),
    (TWIN, (0, 5)),
    (tuple(NORMAL[i] ^ int(i == 15) for i in range(16)), (4, 1)),
])
def test_original_heldout_source_actions_after_frozen_injected_model(bits, expected):
    _, train, _, _ = original_train()
    report = evaluate_frozen_proposal(injected(bits, train))
    assert report["classification"] == "B26_OFFLINE_FROZEN_PROPOSAL_BENCHMARK"
    assert report["model_call_was_performed_by_this_evaluator"] is False
    assert report["proposal_origin"] == "B26_TEST_ONLY_INJECTED"
    assert report["receipt_scope"] == "B26_TEST_ONLY_INJECTED_NOT_L2"
    assert report["original_training_equal_for_both_hidden_world_laws"]
    assert report["novel_truth_complementarity_for_frozen_proposal"]
    assert report["not_physical_minecraft"] and report["not_production_S11"]
    data = report["worlds"]
    assert (
        data["NORMAL:LOCAL_L2_FROZEN_PROPOSAL"]["novel_first_correct"],
        data["TWIN:LOCAL_L2_FROZEN_PROPOSAL"]["novel_first_correct"],
    ) == expected
    assert (
        data["NORMAL:CHEAP_DEG2"]["novel_first_correct"],
        data["TWIN:CHEAP_DEG2"]["novel_first_correct"],
    ) == (5, 0)
    for row in data.values():
        assert row["training_action_attempts"] == 16
        assert row["encounters"] == 5
        assert row["novel_action_attempts"] == 10 - row["novel_first_correct"]
        assert row["total_original_world_actions"] == (
            16 + row["novel_action_attempts"]
        )
        assert len(row["events"]) == 5
        assert sum(
            len(x["actually_issued_event_ids"]) for x in row["events"]
        ) == row["novel_action_attempts"]
        for event in row["events"]:
            assert event["actually_executed_actions"][0] == event["first_action"]
            if not event["first_correct"]:
                assert event["actually_executed_actions"][1] == (
                    1 - event["first_action"]
                )
    assert report["total_independently_issued_offline_world_actions"] == 94


@pytest.mark.parametrize("raw", [
    '{"coefficients":[0]}',
    '{"coefficients":"guess"}',
    '{"coefficients":[]}',
    '{"coefficients":null}',
    '{"coefficients":[0],"extra":1}',
    '{"other":[0]}',
    '{"coefficients":[0],"coefficients":[1]}',
    'not json',
    'BEGIN{"coefficients":[]}END',
    '{"coefficients":[' + ",".join(["false"] * 16) + ']}',
])
def test_partial_duplicate_nonbinary_or_other_output_rejected(raw):
    _, source, _, _ = original_train()
    with pytest.raises(InvalidB26Proposal):
        parse_and_qualify(raw, source)


def test_proposal_must_fit_real_training_and_cannot_modify_source_labels():
    _, source, _, _ = original_train()
    incorrect = list(NORMAL)
    incorrect[0] ^= 1
    with pytest.raises(InvalidB26Proposal, match="contradicts executed training"):
        injected(tuple(incorrect), source)
    with pytest.raises(InvalidB26Proposal, match="11 original source anchors"):
        parse_and_qualify(
            json.dumps({"coefficients": list(NORMAL)}), source[:10]
        )
    forged = replace(source[0], winner=1 - source[0].winner)
    with pytest.raises(InvalidB26Proposal, match="lack actual Action outcomes"):
        injected(NORMAL, (forged,) + source[1:])


def test_ghost_source_event_and_unissued_outcome_cannot_make_training():
    w = StructuralWorld("b26-ghost-test", twin=False)
    training = train_original_world(w)
    bad = replace(training[0], original_outcomes=())
    with pytest.raises(InvalidB26Proposal, match="lack actual Action outcomes"):
        examples_only((bad,) + training[1:])
    bad2 = replace(training[0], source_event_ids=("never-issued",))
    with pytest.raises(InvalidB26Proposal, match="lack actual Action outcomes"):
        examples_only((bad2,) + training[1:])
    assert w.actions_executed == 16


def test_prediction_is_pure_no_world_oracle_before_source_action():
    assert predict(NORMAL, HELDOUT[0]) in (0, 1)
    assert predict(TWIN, HELDOUT[0]) != predict(NORMAL, HELDOUT[0])
    assert set(ANCHORS).isdisjoint(HELDOUT)


def test_no_local_inference_triggered_by_default_and_endpoint_is_local(monkeypatch):
    for url in (
        "https://example.com/v1/chat/completions",
        "http://api.example.com/v1/chat/completions",
        "http://127.0.0.1:1234/v1/wrong",
        "http://localhost/v1/chat/completions",
    ):
        with pytest.raises(InvalidB26Proposal):
            _local_endpoint(url)
    assert _local_endpoint("http://127.0.0.1:1234/v1/chat/completions")
    def fail_network(*_args, **_kwargs):
        raise AssertionError("real L2 network call in CI")
    monkeypatch.setattr(
        "experiments.ac_b_b26_l2_trial.urlopen", fail_network
    )
    with pytest.raises(SystemExit) as e:
        main([])
    assert e.value.code == 2


def test_exact_one_mocked_local_completion_not_claimed_as_real_l2(monkeypatch):
    calls = []
    class DummyReply:
        def __enter__(self):
            return self
        def __exit__(self, *_args):
            return None
        def read(self, _limit):
            return json.dumps({
                "choices": [{"message": {
                    "content": json.dumps({"coefficients": list(NORMAL)})
                }}],
                "model": "MOCKED_NOT_AN_LLM",
                "usage": {"prompt_tokens": 10, "completion_tokens": 23},
            }).encode("utf-8")
    def fake_network(request, timeout):
        calls.append((request, timeout))
        return DummyReply()
    monkeypatch.setattr(
        "experiments.ac_b_b26_l2_trial.urlopen", fake_network
    )
    result = run_local_one_call(
        endpoint="http://127.0.0.1:1234/v1/chat/completions",
        model="TEST_FAKE_MODEL",
        messages=prompt_messages(original_train()[1]),
        timeout_seconds=21,
    )
    assert len(calls) == 1 and calls[0][1] == 21
    body = json.loads(calls[0][0].data.decode("utf-8"))
    assert body["model"] == "TEST_FAKE_MODEL"
    assert body["temperature"] == 0 and body["stream"] is False
    assert len(body["messages"]) == 2
    assert result["reported_model"] == "MOCKED_NOT_AN_LLM"
    assert result["reported_usage"]["completion_tokens"] == 23
    assert parse_and_qualify(
        result["raw_completion"], original_train()[1]
    ).coefficients == NORMAL
