"""Read-only original audit for #653; saved diagnostics are not typed authority."""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from adapters.mineflayer.m02_paper_dev.s50_live_paper_window import capture_s50_live_paper_window
from tools.selfbody_route_b_readback import review as review_route_b


def review(root: Path) -> dict[str, object]:
    route = review_route_b(root)
    report = json.loads((root / "s49-report.json").read_bytes())
    shadow = report["l1_motion_shadow"]
    prior = route["live_window"]
    window = capture_s50_live_paper_window(
        (root / "live-paper-prefix.log").read_bytes(),
        session_id=prior["session_id"], action_id=prior["action_id"],
        world=prior["paper_world_uuid"], subject_uuid=prior["subject_uuid"],
    )
    assert asdict(window) == prior
    motion = [t.world_tick for t in window.ticks
              if t.displacement_m > 0 and not t.last_reported_input_active]
    body = report["live_next_epoch"]["current_body"]
    obs = body["observation"]
    assert shadow["session_id"] == window.session_id == report["session_id"]
    assert shadow["epoch_id"] == body["epoch_id"]
    assert shadow["current_native_seq"] == obs["native_seq"]
    assert shadow["current_native_source_ref"] == (
        f'native-probe:{window.session_id}:{obs["native_seq"]}:{obs["request_id"]}'
    )
    assert shadow["prior_action_id"] == window.action_id
    assert shadow["prior_paper_prefix_sha256"] == window.paper_prefix_sha256
    assert shadow["previous_motion_ticks"] == motion
    assert shadow["current_s_choice"] == report["decisions"][-1]["selected"] == "WAIT"
    assert shadow["without_experience"] == "ABSTAIN_NO_PRIOR_MOTION_EVIDENCE"
    expected = ("RECHECK_SAMPLED_POST_CLEAR_MOTION" if motion
                else "NO_SAMPLED_MOTION_NOT_PHYSICALLY_STABLE")
    assert shadow["with_experience"] == shadow["cheap_same_information"] == expected
    assert shadow["attention_candidate_differs"] is bool(motion)
    assert shadow["contrast"] == ("cheap_one_bit_prior_motion_equivalent" if motion
                                   else "no_sampled_motion_no_attention_change")
    for key in ("cognitive_priority_committed", "learned_l1_policy", "paper_input_is_full_tick",
                "effective_clear_tick_attested", "goal_admitted", "original_l0_decision_modified"):
        assert shadow[key] is False
    for key in ("original_s_choice_kept", "current_native_present_unchanged"):
        assert shadow[key] is True
    for key in ("l10_training_episodes", "s10_updates", "s11_grants", "p1_wait_admitted",
                "new_native_probes", "extra_actions", "model_calls"):
        assert type(shadow[key]) is int and shadow[key] == 0
    assert shadow["classification"] == "DEV_L1_PRIOR_MOTION_ATTENTION_SHADOW_CHEAP_EQUIVALENT"
    return {"classification": "DEV_LIVE_L1_MOTION_SHADOW_ORIGINAL_AUDIT_PASS",
            "route_b": route, "shadow": shadow,
            "independent_rule_motion_ticks": motion,
            "typed_identity_scope": "Original live host only; no JSON typed reauthentication",
            "goal": "UNDETERMINED", "qualification": "NO_GO", "science": "NOT_RUN"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = review(args.root)
    with args.output.open("x") as out:
        out.write(json.dumps(result, indent=2) + "\n")
    print(result["classification"])


if __name__ == "__main__":
    main()
