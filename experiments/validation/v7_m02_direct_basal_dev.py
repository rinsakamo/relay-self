"""V7: additional 5 actual Paper DEV attempts, R-reviewed source accounting only.

The original five DEV attempts are immutable and retained separately. This
readout contains references/measurements from R's new original archive, not
independently downloaded bytes, new V science, or V7 prereg changes.
"""
from __future__ import annotations

import json
import math

from experiments.validation import v7_m02_physics as v7
from experiments.validation import v7_m02_seed61021_dev as old
from experiments.validation import v7_m02_trial_roster as roster

S_RUN = 38850179491
S_HEAD = "5defe85f55068b34d4ddae0ebe93afc892c09c2c"
R_RUN = 38850421003
R_HEAD = "125597a4e8844c48da0db77124bb1307372e2654"
R_ARCHIVE = 12024688755
PLUGIN_SHA = "af911877133f54e6a3f4ab2f5a9416daf75259af53cb7b4226f8730da9a8b1fc"
# S archive ZIP digest, actual R-readback BASAL requested/200 player callbacks,
# actual Paper packet horizontal path, actual source-side WALK debit. Each
# figure comes from separate real World originals independently read by R.
SOURCE = {
    "BASE_ON": ("5838cd4a813b60106b3dfec4e9e7ba5a12104c5503e84c334948e8e2f69bcfe8", 0.2, 1.0390903428873646, 0.010390903428873647),
    "SHAM_ON": ("89e673b634b47a20f56a8f2a3e93f25bca820352dfc232b327d4fba2469f118d", 0.2, 1.0390903428873624, 0.010390903428873624),
    "BASAL_ZERO": ("7ea7ecfda24d02a3bfebcf8854de0c719606273d62771d867ce7a17e7bcc2b19", 0.0, 1.2828913533098643, 0.012828913533098642),
    "WALK_ZERO": ("5abd5c10fc0db56d557791627ce110f3cb42a7760170aba3dda04525e52da444", 0.2, 1.0390903428873646, 0.0),
    "BOTH_ZERO": ("300d23f6c51c16ee154341638056b3fb0843ea03832c9450c32dc9dbda1a0261", 0.0, 1.2828913533098643, 0.0),
}


def review_real_direct_basal_dev_metadata() -> dict:
    """Add all new DEV attempts without consuming any V7 science slot."""
    v7.load_manifest()  # never alter frozen matched-path preregistration
    p = old.seed61021_prescience_roster()
    for slot in p["slots"]:
        if slot["seed"] == 61021:
            arm = slot["arm"]
            digest, _, _, _ = SOURCE[arm]
            slot["prescience_attempts"].append({
                "attempt_id": f"dev{S_RUN}-{arm}",
                "mode": "DEV",
                "outcome": "PASS_CLAIMED",
                "original_bundle_sha256": digest,
                "r_review": "REVIEW_ONLY",
                "science_trial": False,
                "grant_reused": False,
            })
    ledger = roster.review_roster(p)
    if ledger["prescience_attempts_preserved"] != {"DEV": 10, "QUALIFICATION": 0}:
        raise v7.V7Rejected("historical and new DEV attempts not preserved")
    measured = {}
    for arm in v7.ARMS:
        digest, basal_charge, path, walk_charge = SOURCE[arm]
        basal_mult, walk_mult = v7.MULTIPLIERS[arm]
        if not (len(digest) == 64 and all(c in "0123456789abcdef" for c in digest)
                and all(math.isfinite(x) for x in (basal_charge, path, walk_charge))
                and path > 0 and basal_charge >= 0 and walk_charge >= 0):
            raise v7.V7Rejected("missing/invalid new R source reference")
        basal_per_tick = basal_charge / 200.0
        walk_per_block = walk_charge / path
        if (abs(basal_per_tick - 0.001 * basal_mult) > 1e-8
                or abs(walk_per_block - 0.01 * walk_mult) > 1e-8):
            raise v7.V7Rejected("new R original requested cost not consistent")
        measured[arm] = {
            "source_original_s_artifact_zip_sha256": digest,
            "basal_requested_per_actual_player_callback": basal_per_tick,
            "basal_source_requested_first200": basal_charge,
            "walk_source_billed_per_actual_block": walk_per_block,
            "actual_packet_path_blocks": path,
            "actual_source_walk_debit": walk_charge,
        }
    paths = [measured[arm]["actual_packet_path_blocks"] for arm in v7.ARMS]
    spread = max(paths) - min(paths)
    tolerance = v7.load_manifest()["design"]["matched_path_tolerance_blocks"]
    if spread <= tolerance:
        raise v7.V7Rejected("new physical spread unexpectedly lost")
    return {
        "classification": "V7_M02_NEW_DIRECT_BASAL_FIVE_DEV_R_SOURCE_REVIEW_ONLY",
        "s_original_run": S_RUN,
        "s_source_head": S_HEAD,
        "r_independent_run": R_RUN,
        "r_source_head": R_HEAD,
        "r_immutable_archive_id": R_ARCHIVE,
        "plugin_new_unqualified_sha256": PLUGIN_SHA,
        "new_dev_worlds": 5,
        "historical_dev_worlds": 5,
        "total_prescience_dev_attempts_preserved": 10,
        "science_slots_unexecuted": ledger["prospective_science_slots"],
        "science_trials_credited": 0,
        "source_requested_basal_and_walk_consistent": True,
        "r_changed_plugin_engineering_qualified": False,
        "native_meter_ecological_effect_attested": False,
        "controlled_move_bracket_attested": False,
        "observed_max_path_spread_blocks": spread,
        "historic_v7_matched_path_tolerance_blocks": tolerance,
        "historic_v7_paired_comparison_admitted": False,
        "v7_science_go": False,
        "production_go": False,
        "arms": measured,
    }


def main() -> None:
    print(json.dumps(review_real_direct_basal_dev_metadata(), sort_keys=True))


if __name__ == "__main__":
    main()
