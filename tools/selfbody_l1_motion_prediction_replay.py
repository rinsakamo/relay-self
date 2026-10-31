"""Re-run the #653 L1-MP1 archival readback ONLY (no Minecraft launch)."""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from adapters.mineflayer.self_body_s50_l1_motion_prediction import (
    evaluate_heldout,
    from_archival_readback,
)

from adapters.mineflayer.self_body_s50_l1_motion_prequential import (
    TargetWorldIdentity,
    freeze_for_target,
    score_frozen,
    update_after_score,
)

ROOT = Path(__file__).resolve().parents[1]
A = ROOT / "docs/evidence/issue651-route-b-20261031/run1/independent-original-readback.json"
B = ROOT / (
    "docs/evidence/issue653-l1-motion-shadow-20261031/run1/"
    "independent-l1-original-readback.json"
)


def main() -> None:
    # Each readback is an immutable historical *audit report*. We do not
    # authenticate Java/Node original bytes or claim a new World execution.
    a = from_archival_readback(json.loads(A.read_text(encoding="utf-8")))
    b = from_archival_readback(json.loads(B.read_text(encoding="utf-8")))
    ticket = freeze_for_target(a, TargetWorldIdentity(
        b.session_id, b.paper_world_uuid, b.action_id, b.subject_uuid,
    ))
    scored = score_frozen(ticket, a, b)
    next_world = update_after_score(ticket, a, b, scored)
    print(json.dumps({
        "classification": "DEV_OFFLINE_ARCHIVAL_FREEZE_SCORE_REFIT_REPLAY_ONLY",
        "mp2_frozen_ticket": asdict(ticket),
        "mp2_scored": asdict(scored),
        "mp2_next_world_untested": asdict(next_world),
        "primary_652_train_654_heldout": asdict(evaluate_heldout(a, b)),
        "secondary_654_train_652_heldout": asdict(evaluate_heldout(b, a)),
        "training_l10": 0,
        "s10_updates": 0,
        "s11_grants": 0,
        "goal": "UNDETERMINED",
        "new_world_runs": 0,
        "qualification": "NO_GO",
        "science": "NOT_RUN",
    }, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
