"""R #575: independent V6 World-start and three-clock PRE-ADMISSION checks.

No launcher, World mutation, inferred Minecraft age or scientific GO.
Golden stopped-source bytes may be independently read with check_stopped_clones.
The frame audit is strict structural evidence, not independent original-byte
provenance; only an R original-readback can bind its claims to native bytes.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from experiments.standard_env.golden_admission import verify_qualified_world
from experiments.standard_env.world_binding import _seed_from_level, _world_files

V6_START_SCHEMA = "RSEE_V6_THREE_CLOCK_PRE_ADMISSION_1"
GOLDEN_HEAD = "34820f6bf391c77f325d7c29d3b779a33e3ca835"
GOLDEN_MANIFEST_SHA256 = "5b1876db6a97fc8b9c4331938ca47727037c5626a241213d871b2073665996f8"
ARMS = (
    "SENSOR_ON", "SHAM_ON", "SENSOR_MASKED_HIGH",
    "ALWAYS_SEEK", "ALWAYS_WAIT", "EQUAL_INFO_CHEAP_THRESHOLD",
)
ENERGIES = {"LOW": 12, "HIGH": 20}
EXPECTED_M0_TICKS = 11
WORLD_DAY_TICKS = 24000


class V6ClockRejected(ValueError):
    """World, native-time or M0 evidence may not be promoted."""


def _need(condition: bool, reason: str) -> None:
    if not condition:
        raise V6ClockRejected(reason)


def plan() -> dict[str, Any]:
    return {
        "classification": "RSEE_V6_WORLD_TIME_PRE_ADMISSION_PLAN",
        "golden_head": GOLDEN_HEAD,
        "golden_world_manifest_sha256": GOLDEN_MANIFEST_SHA256,
        "world_start_bytes": "NOT_READ",
        "actual_host_monotonic_time": "NOT_READ",
        "native_time_of_day": "NOT_READ",
        "minecraft_world_age_tick": "NOT_IN_FROZEN_MINEFLAYER_SOURCE",
        "m0_tick": "NOT_WORLD_TICK",
        "cross_arm_native_world_elapsed_parity": "NOT_ATTESTED",
        "science_g3": "NO_GO",
        "physical_execution_authorized": False,
        "side_effects": "NONE",
    }


def check_stopped_clones(
    jar: Path, golden: Path, manifest: Path, initial_evidence: Path,
    clones: tuple[Path, ...],
) -> dict[str, Any]:
    """Read only existing unstarted clone bytes against independently pinned RSEE.

    Source Golden identity is checked by the already-qualified RSEE verifier;
    no new manifest is synthesized from a candidate clone. A clone pass
    establishes snapshot byte equivalence *at time of this read*, NOT
    launch-state parity, native time equality or identical random processes.
    """
    _need(
        type(clones) is tuple and bool(clones) and len(clones) <= 48,
        "one to 48 explicit clone directories needed",
    )
    _need(len({str(p) for p in clones}) == len(clones), "duplicate clone root")
    for path in (jar, golden, manifest, initial_evidence, *clones):
        _need(
            isinstance(path, Path) and path.is_absolute()
            and not path.is_symlink() and path.resolve(strict=True) == path
            and not any(p.is_symlink() for p in path.parents),
            "noncanonical/symlinked/unavailable World path",
        )
    binding = verify_qualified_world(jar, golden, manifest, initial_evidence)
    _need(binding.manifest_sha256 == GOLDEN_MANIFEST_SHA256, "Golden drift")
    checked = []
    for root in clones:
        _need(root != golden, "clone must not alias immutable Golden snapshot")
        _need(root.is_dir(), "clone must exist")
        _need(_world_files(root) == binding.files, "clone SHA256/file index differs")
        _need(_seed_from_level(root / "level.dat")
              == _seed_from_level(golden / "level.dat"),
              "clone seed differs")
        checked.append({"snapshot": str(root), "verified_files": len(binding.files)})
    return {
        "classification": "RSEE_V6_STOPPED_WORLD_BYTES_MATCH_REVIEW_ONLY",
        "golden_head": GOLDEN_HEAD,
        "golden_manifest_sha256": binding.manifest_sha256,
        "stopped_world_file_count": len(binding.files),
        "existing_clones_checked": checked,
        "clone_time_scope": "BYTE_MATCH_AT_READ_ONLY_INSTANT_NOT_LAUNCH",
        "real_world_time_matched": False,
        "native_world_age_attested": False,
        "physical_execution_authorized": False,
        "science_g3": "NO_GO",
    }


def _frame(row: Any, *, session: str, index: int, previous_seq: int,
           previous_host_ns: int) -> tuple[int, int]:
    _need(type(row) is dict and set(row) == {
        "session_id", "native_seq", "request_id", "host_monotonic_ns",
        "m0_tick", "native_time", "world_age_tick", "item_visible",
        "issued_action", "m0_energy",
    }, "clock frame fields missing/extra")
    _need(
        row["session_id"] == session
        and type(row["native_seq"]) is int
        and row["native_seq"] > previous_seq
        and type(row["request_id"]) is str and bool(row["request_id"])
        and type(row["host_monotonic_ns"]) is int
        and row["host_monotonic_ns"] > previous_host_ns
        and type(row["m0_tick"]) is int and row["m0_tick"] == min(index, 11)
        and type(row["item_visible"]) is bool
        and row["item_visible"] == (index == 12)
        and row["issued_action"] is False
        and type(row["m0_energy"]) in (float, int),
        "session/sequence/host/M0/item/Action chronology inconsistent",
    )
    nt = row["native_time"]
    _need(type(nt) is dict and set(nt) == {"day", "time_of_day", "is_day"}
          and type(nt["day"]) is int and nt["day"] >= 0
          and type(nt["time_of_day"]) is int and 0 <= nt["time_of_day"] < WORLD_DAY_TICKS
          and type(nt["is_day"]) is bool, "invalid native time-of-day source")
    age = row["world_age_tick"]
    _need(age is None or (type(age) is int and age >= 0),
          "invalid/invented independent world-age type")
    return row["native_seq"], row["host_monotonic_ns"]


def review_clock_trace(trace: dict[str, Any]) -> dict[str, Any]:
    """One candidate session; no raw file readback and no actual execution.

    The caller must separately bind every row to full native original SHA
    before this could be meaningful beyond typed offline source evidence.
    """
    _need(type(trace) is dict and set(trace) == {
        "schema", "world_start_slot", "arm", "regime", "native_session",
        "stopped_world_manifest_sha256", "frames",
    }, "trace schema changed")
    _need(trace["schema"] == V6_START_SCHEMA
          and trace["world_start_slot"] in (
              "WORLD_START_A", "WORLD_START_B", "WORLD_START_C", "WORLD_START_D"
          )
          and trace["arm"] in ARMS and trace["regime"] in ENERGIES
          and isinstance(trace["native_session"], str)
          and bool(trace["native_session"])
          and trace["stopped_world_manifest_sha256"] == GOLDEN_MANIFEST_SHA256,
          "unregistered V6 start/arm/GOLDEN reference")
    frames = trace["frames"]
    _need(type(frames) is list and len(frames) == 13,
          "requires first native probe, 11 real-shaped WAITs, and item")
    seq, host = -1, -1
    requests = set()
    for i, row in enumerate(frames):
        seq, host = _frame(row, session=trace["native_session"], index=i,
                           previous_seq=seq, previous_host_ns=host)
        _need(row["request_id"] not in requests, "duplicate native request")
        requests.add(row["request_id"])
        expected = ENERGIES[trace["regime"]] - .5 * min(i, 11)
        _need(row["m0_energy"] == expected, "M0 energy/11 basal charges differ")
    ages = [frame["world_age_tick"] for frame in frames]
    known_ages = all(age is not None for age in ages)
    if known_ages:
        _need(all(right > left for left, right in zip(ages, ages[1:])),
              "world age not strictly progressing despite later native probes")
    # day*timeOfDay is clock display/phase only. It is NOT a native World age.
    phases = [
        row["native_time"]["day"] * WORLD_DAY_TICKS
        + row["native_time"]["time_of_day"]
        for row in frames
    ]
    return {
        "classification": "RSEE_V6_THREE_CLOCK_STRUCTURAL_REVIEW_ONLY",
        "world_start_slot": trace["world_start_slot"],
        "arm": trace["arm"],
        "regime": trace["regime"],
        "native_session": trace["native_session"],
        "host_elapsed_ns_start_to_item": frames[-1]["host_monotonic_ns"]
        - frames[0]["host_monotonic_ns"],
        "m0_wait_charges": 11,
        "m0_tick_at_item": frames[-1]["m0_tick"],
        "m0_energy_at_item": frames[-1]["m0_energy"],
        "native_clock_display_daytime_start_to_item": [phases[0], phases[-1]],
        "native_time_of_day_is_not_world_age": True,
        "world_age_sample_presence": "ALL_UNBOUND" if known_ages else "INCOMPLETE",
        "world_age_elapsed_ticks_start_to_item": (
            ages[-1] - ages[0] if known_ages else None
        ),
        "original_native_sha256_verified": False,
        "world_start_clone_bytes_verified": False,
        "matched_world_elapsed_tick_attested": False,
        "live_world_trial_authorized": False,
        "science_g3": "NO_GO",
    }


def review_paired_start(traces: list[dict[str, Any]]) -> dict[str, Any]:
    """One planned 12-arm block, with strict identity/chronology and NO GO."""
    _need(type(traces) is list and len(traces) == 12,
          "V6 requires LOW/HIGH x all six arms per start")
    validated = [review_clock_trace(row) for row in traces]
    slot = validated[0]["world_start_slot"]
    pairs = [(x["regime"], x["arm"]) for x in validated]
    _need(all(x["world_start_slot"] == slot for x in validated)
          and len(set(pairs)) == 12
          and set(pairs) == {(p, a) for p in ENERGIES for a in ARMS}
          and len({x["native_session"] for x in validated}) == 12,
          "missing/cross-start/duplicate paired arm or session")
    deltas = [x["world_age_elapsed_ticks_start_to_item"] for x in validated]
    possible_match = all(t is not None for t in deltas) and len(set(deltas)) == 1
    return {
        "classification": "RSEE_V6_PAIRED_CLOCK_REVIEW_ONLY_NOT_ADMITTED",
        "world_start_slot": slot, "planned_arms": len(validated),
        "host_elapsed_ns_by_arm": {
            x["regime"] + ":" + x["arm"]: x["host_elapsed_ns_start_to_item"]
            for x in validated
        },
        "m0_tick_per_arm": 11,
        "claimed_world_age_delta_parity_possible": possible_match,
        "native_world_age_authenticity_verified": False,
        "independent_golden_clone_bytes_verified": False,
        "source_original_sha256_verified": False,
        "matched_native_world_elapsed_tick_attested": False,
        "actual_world_starts": 0,
        "physical_execution_authorized": False,
        "science_g3": "NO_GO",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    print(json.dumps(plan(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
