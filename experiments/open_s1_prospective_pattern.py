from __future__ import annotations

import json
from dataclasses import dataclass

from experiments.cognition_consequence_loop import (
    ConsequenceComparison,
    ExpectedEvidence,
    ObservedEvidence,
    compare_consequence,
)
from relay_self.provenance import Provenance
from relay_self.relay_engine import CognitionDatum, OpenCognitionRequest


class InvalidProspectiveProposal(ValueError):
    """Raised when an experiment-local prospective proposal is malformed."""


@dataclass(frozen=True, slots=True)
class ProspectiveFixture:
    """One open proposal surface plus the later evidence hidden from that surface."""

    request: OpenCognitionRequest
    observed: ObservedEvidence


def build_reference_prospective_fixture(
    *,
    observed_key: str = "event:lambda",
    observed_code: str = "outcome:9",
) -> ProspectiveFixture:
    """Build one opaque prospective fixture without exposing its future observation."""

    current_prefix = (
        {"step": 0, "signal": "obs:theta", "level": 2},
        {"step": 1, "signal": "obs:iota", "level": 5},
    )
    selected_memory = {
        "memory_id": "episode:alpha",
        "prefix": (
            {"step": 0, "signal": "obs:alpha", "level": 2},
            {"step": 1, "signal": "obs:beta", "level": 5},
        ),
        "later_evidence": {
            "key": "event:kappa",
            "value": {"code": "outcome:3"},
        },
    }

    request = OpenCognitionRequest(
        request_id="open-s1-prospective-reference",
        instruction=(
            "Propose exactly one expected evidence pair for the next materially "
            "relevant observation. Return one JSON object with exactly keys key "
            "and value. Do not report the proposal as observed truth and do not explain."
        ),
        intent_id=None,
        focus="PROSPECTIVE_PATTERN",
        context=(
            CognitionDatum.from_value(
                "current_prefix",
                current_prefix,
                Provenance(
                    source="fixture.present",
                    reference="prospective:current-prefix",
                ),
            ),
            CognitionDatum.from_value(
                "selected_memory",
                selected_memory,
                Provenance(
                    source="fixture.memory",
                    reference="prospective:memory:episode-alpha",
                ),
            ),
        ),
    )
    observed = ObservedEvidence(
        key=observed_key,
        value={"code": observed_code},
        provenance=Provenance(
            source="fixture.world",
            reference="prospective:held-out-future",
        ),
    )
    fixture = ProspectiveFixture(request=request, observed=observed)
    if hidden_future_is_visible(fixture):
        raise ValueError("held-out future must not appear on the proposal surface")
    return fixture


def visible_request_json(request: OpenCognitionRequest) -> str:
    """Render only information available when the prospective proposal is requested."""

    payload = {
        "request_id": request.request_id,
        "instruction": request.instruction,
        "intent_id": request.intent_id,
        "focus": request.focus,
        "context": [
            {
                "key": datum.key,
                "value": json.loads(datum.value_json),
                "provenance": {
                    "source": datum.provenance.source,
                    "reference": datum.provenance.reference,
                },
            }
            for datum in request.context
        ],
    }
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def hidden_future_is_visible(fixture: ProspectiveFixture) -> bool:
    """Return whether the held-out evidence leaked into the proposal input."""

    visible = visible_request_json(fixture.request)
    key = json.dumps(fixture.observed.key, ensure_ascii=False)
    value = json.dumps(
        fixture.observed.value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return key in visible or value in visible


def parse_expected_evidence(text: str) -> ExpectedEvidence:
    """Parse the experiment-local open proposal envelope."""

    if not isinstance(text, str) or not text.strip():
        raise InvalidProspectiveProposal("proposal must be non-empty text")
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise InvalidProspectiveProposal("proposal must be valid JSON") from exc
    if not isinstance(value, dict) or set(value) != {"key", "value"}:
        raise InvalidProspectiveProposal(
            "proposal must be one JSON object with exactly key and value"
        )
    key = value["key"]
    if not isinstance(key, str) or not key.strip():
        raise InvalidProspectiveProposal("proposal key must be non-empty text")
    return ExpectedEvidence(key=key, value=value["value"])


def score_proposal(
    proposal: ExpectedEvidence,
    observed: ObservedEvidence | None,
) -> ConsequenceComparison:
    """Compare a predictive proposal with later grounded evidence."""

    return compare_consequence(proposal, observed)


def exact_replay_baseline(request: OpenCognitionRequest) -> ExpectedEvidence | None:
    """Replay prior evidence only when the current prefix is exactly the remembered prefix."""

    values = {
        datum.key: json.loads(datum.value_json)
        for datum in request.context
    }
    current = values.get("current_prefix")
    memory = values.get("selected_memory")
    if not isinstance(memory, dict) or current != memory.get("prefix"):
        return None

    later = memory.get("later_evidence")
    if not isinstance(later, dict) or set(later) != {"key", "value"}:
        return None
    key = later["key"]
    if not isinstance(key, str) or not key.strip():
        return None
    return ExpectedEvidence(key=key, value=later["value"])
