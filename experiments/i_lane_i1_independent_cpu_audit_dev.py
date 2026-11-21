"""I Lane I1: independent read-only audit of original Native/Paper -> CPU epochs.

Run in a fresh process AFTER Stage28c2b exits. The original Stage28 audit first
qualifies historical owners, physical WAL, original real Native/Paper streams
and clean retirement. This auditor independently checks the *new* I1 claims:
each read-only request in raw native JSONL, each owned Paper ACK/prefix and
replays the bounded CPU Schema from the original immutable PatternRegistry.

The I1 capture report cannot be promoted by the legacy Stage28 auditor.
DEV only: no LLM, World launch, physical action or source mutation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import fields
from pathlib import Path

from adapters.mineflayer.python_protocol import MineflayerObservation, parse_mineflayer_line
from experiments.stage28c2b_independent_rejoin_audit_dev import (
    _sha,
    _verify_main_thread_ack,
    independently_audit_recovered_real_rejoin,
)
from experiments.stage28c2b_real_recovered_rejoin_dev import (
    _SOURCE_WORLD,
    inspect_real_recovered_sources,
)
from relay_self.cognitive_minimal_dev import (
    WorldPercept,
    assemble_l1_select,
    cpu_schema_epoch,
)
from relay_self.common_io import ScopeRef
from relay_self.i_lane_i1_cpu_schema_probe_dev import _exact_food
from relay_self.i_lane_i1_normal_runtime_dev import (
    I1OriginalCPUEpoch,
    prepare_i1_original_schema_bootstrap,
)
from relay_self.resident_paper_presence_join_dev import parse_owned_paper_resident_trace


class I1IndependentAuditHold(RuntimeError):
    """Independent original A/B Native, Paper or cognitive evidence is absent."""


_I1_REQUEST = re.compile(r"i1-original-sense-[0-9a-f]{32}\Z")
_I1_CLASS = "I1_ORIGINAL_CPU_SENSE_CAPTURED_INDEPENDENT_AUDIT_PENDING"
_I1_AUDITED = "I1_ORIGINAL_A_B_NATIVE_PAPER_CPU_SOURCE_AUDITED_DEV"
_I1_BASE = "I1_BASE_ORIGINAL_NATIVE_PAPER_A_B_SOURCE_VERIFIED_DEV"


def _paper_prefixes(frozen: bytes) -> dict[str, int]:
    """Hash to byte offset of a real line-complete prefix (bounded memory)."""
    if not frozen or len(frozen) > 64 * 1024 * 1024:
        raise I1IndependentAuditHold("bounded frozen owned Paper log required")
    prefixes: dict[str, int] = {}
    digest = hashlib.sha256()
    offset = 0
    for line in frozen.splitlines(keepends=True):
        offset += len(line)
        digest.update(line)
        if line.endswith(b"\n"):
            prefixes[digest.hexdigest()] = offset
    return prefixes


def _i1_native_probes(
    *, evidence: Path, report: dict, sid: str,
) -> tuple[MineflayerObservation, list[MineflayerObservation]]:
    native_id = report["native_login_evidence"][sid]["native_session_id"]
    file = evidence / f"native-Relay{sid}-{native_id}.jsonl"
    if (
        _sha(file) != report["raw_native_file_sha256"]["Relay" + sid]
        or file.stat().st_size > 32 * 1024 * 1024
    ):
        raise I1IndependentAuditHold("original I1 Native JSONL integrity mismatch")
    matches = []
    original_probes = []
    original_request = report["native_login_evidence"][sid]["observation_ref"]
    previous_seq = -1
    for raw in file.read_bytes().splitlines():
        try:
            decoded = parse_mineflayer_line(raw.decode("utf-8"))
        except (UnicodeError, ValueError, TypeError) as exc:
            raise I1IndependentAuditHold("invalid original Native JSONL") from exc
        if (decoded.session_id != native_id
                or type(decoded.seq) is not int or decoded.seq <= previous_seq):
            raise I1IndependentAuditHold("foreign/reordered original native sequence")
        previous_seq = decoded.seq
        if (isinstance(decoded, MineflayerObservation)
                and decoded.kind == "probe"
                and decoded.request_id == original_request):
            original_probes.append(decoded)
        if isinstance(decoded, MineflayerObservation) and (
            decoded.request_id is not None
            and decoded.request_id.startswith("i1-original-sense-")
        ):
            if (decoded.kind != "probe"
                    or _I1_REQUEST.fullmatch(decoded.request_id) is None
                    or decoded.snapshot.time is None):
                raise I1IndependentAuditHold("invalid correlated original I1 Native probe")
            matches.append(decoded)
    if len(original_probes) != 1 or len(matches) != 2:
        raise I1IndependentAuditHold("original login and two I1 probes required")
    return original_probes[0], matches


def _i1_original_commands(
    *, evidence: Path, report: dict, sid: str,
    original: MineflayerObservation, probes: list[MineflayerObservation],
) -> None:
    """Compare exact original stdin bytes with three independently parsed stdout probes.

    Stdin evidence is captured at the SINGLE original adapter sender after
    drain(), before logout. It is not proof of the child's receipt or the
    Minecraft state. The Paper and raw stdout checks remain mandatory.
    """
    native_id = report["native_login_evidence"][sid]["native_session_id"]
    digests = report.get("raw_native_command_file_sha256")
    if (type(digests) is not dict or set(digests) != {"RelayA", "RelayB"}):
        raise I1IndependentAuditHold("original A/B Native outbound transcript absent")
    path = evidence / f"native-commands-Relay{sid}-{native_id}.jsonl"
    try:
        actual_sha = _sha(path)
        size = path.stat().st_size
    except (OSError, RuntimeError) as exc:
        raise I1IndependentAuditHold(
            "original Native outbound transcript missing or untrusted"
        ) from exc
    if actual_sha != digests["Relay" + sid] or size > 128 * 1024:
        raise I1IndependentAuditHold("original Native outbound transcript SHA mismatch")
    raw = path.read_bytes()
    if not raw.endswith(b"\n"):
        raise I1IndependentAuditHold("outbound Native command missing last line ending")
    commands = []
    for line in raw.splitlines():
        try:
            command = json.loads(line.decode("utf-8"))
        except (UnicodeError, ValueError) as exc:
            raise I1IndependentAuditHold("invalid original outbound Native command") from exc
        if (type(command) is not dict or set(command) != {"type", "request_id"}
                or command.get("type") != "observe"
                or type(command.get("request_id")) is not str):
            raise I1IndependentAuditHold(
                "unqualified physical or additional native command during I1"
            )
        commands.append(command["request_id"])
    if (len(commands) != 3
            or commands != [original.request_id, *(p.request_id for p in probes)]
            or len(set(commands)) != 3):
        raise I1IndependentAuditHold(
            "original send-observe commands and raw probe replies do not match"
        )


def _replay_cpu(row: dict, observation: MineflayerObservation, owner, paper_session: str) -> None:
    """Independent original finite CPU Schema replay; no new owner or LLM."""
    snapshot = observation.snapshot
    threat_cue = any(
        entity.name == "zombie" or entity.entity_type == "zombie"
        for entity in snapshot.nearby_entities
    )
    percept = WorldPercept(
        scope=ScopeRef(row["self_id"], paper_session),
        source=observation.provenance,
        sequence=observation.seq,
        hunger=_exact_food(snapshot.food),
        fatigue_high=None,
        targets=(),
        threat_cue=threat_cue,
        exploration_need=False,
        oxygen_reserve=snapshot.oxygen_level,
    )
    schema = cpu_schema_epoch(
        percept, owner.pattern_registry, allowed_skills=frozenset(),
        epoch=row["resident_epoch"],
    )
    proposal = assemble_l1_select(schema, intent_owner=owner.intent, recent_3self=())
    goals = [goal.goal_id for goal in schema.goals]
    numbered = [description for _, description in proposal.numbered]
    if (
        row["goal_ids"] != goals
        or row["l1_descriptions"] != numbered
        or row["schema_revision"] != owner.pattern_registry.revision
        or row["inquiry_ref"] is not None
        or schema.options
        or numbered != ["ESCALATE_L2", "DEFER"]
    ):
        raise I1IndependentAuditHold("I1 CPU goals/numbered choices differ from raw Native replay")


def _audit_i1_epochs(
    *, report: dict, evidence: Path, executable: Path,
    owners: dict,
) -> dict:
    """Read actual raw source bytes; test fixtures can exercise this in isolation."""
    if (
        report.get("classification") != _I1_CLASS
        or report.get("i1_original_cpu_sense_enabled") is not True
        or report.get("i1_normal_continuous_native_observed") is not True
        or report.get("real_gemma_post") != 0
        or report.get("real_action_issued") != 0
        or report.get("physical_action_issue_authorized") is not False
        or report.get("fresh_l1_run") is not False
        or report.get("cleanup_uncertain")
        or report.get("raw_source_audit_uncertain")
    ):
        raise I1IndependentAuditHold("I1 original capture incomplete / effects present")
    ledger = report.get("i1_cpu_epochs")
    expected_fields = {f.name for f in fields(I1OriginalCPUEpoch)}
    if (
        type(ledger) is not dict
        or set(ledger) != {
            "epochs", "per_self_counts", "continuous_native_updates_observed",
            "model_invoked", "action_issue_authorized",
        }
        or ledger["continuous_native_updates_observed"] is not True
        or ledger["model_invoked"] is not False
        or ledger["action_issue_authorized"] is not False
        or ledger["per_self_counts"] != [["A", 2], ["B", 2]]
        or type(ledger["epochs"]) is not list or len(ledger["epochs"]) != 4
        or [row.get("self_id") for row in ledger["epochs"]
            if type(row) is dict] != ["A", "B", "A", "B"]
        or len([row for row in ledger["epochs"] if type(row) is dict]) != 4
        or any(set(row) != expected_fields for row in ledger["epochs"])
    ):
        raise I1IndependentAuditHold("bounded exact A/B CPU epoch manifest missing")

    original_boot = report.get("paper_boot")
    paper_session = report.get("paper_session_id")
    paper_pid = report.get("paper_pid")
    link_by_self = {
        link["self_id"]: link for link in report.get("fresh_body_links", ())
    }
    if (
        type(original_boot) is not dict
        or type(paper_session) is not str or not paper_session
        or paper_pid != original_boot.get("paper_pid")
        or set(link_by_self) != {"A", "B"}
        or set(owners) != {"A", "B"}
    ):
        raise I1IndependentAuditHold("original A/B Paper epoch or resident source missing")
    if any(
        owner.pattern_registry.revision != 0
        or any(pattern.schema_id == "exploration" for pattern in owner.pattern_registry.patterns)
        for owner in owners.values()
    ):
        # Current Stage28 pinned original Self has NO exploration. Without a
        # genuine saved exploration Need, an inquiry cannot be fabricated.
        raise I1IndependentAuditHold("unqualified old Self exploration registry")
    frozen = (evidence / "prestop-paper-resident-owned.log").read_bytes()
    complete_paper = (evidence / (paper_session + ".log")).read_bytes()
    if not complete_paper.startswith(frozen):
        raise I1IndependentAuditHold("owned Paper prefix differs after termination")
    prefixes = _paper_prefixes(frozen)
    probe_by_id = {
        sid: _i1_native_probes(evidence=evidence, report=report, sid=sid)
        for sid in ("A", "B")
    }
    for sid in ("A", "B"):
        original_probe, i1_probes = probe_by_id[sid]
        _i1_original_commands(
            evidence=evidence, report=report, sid=sid,
            original=original_probe, probes=i1_probes,
        )
    processed = {"A": 0, "B": 0}
    seen_requests: set[str] = set()
    prior_paper: int | None = None
    prior_digest_size = 0
    prior_nonce: str | None = None
    records = ledger["epochs"]
    for row in records:
        sid = row["self_id"]
        number = processed[sid]
        original_probe, i1_probes = probe_by_id[sid]
        observation = i1_probes[number]
        original = report["owner_worldbody_observations"][sid]
        native = report["native_login_evidence"][sid]
        paper_ref = row["paper_tick_source_ref"]
        log_ref = row["paper_log_sha256"]
        req = row["native_request_id"]
        if (
            type(req) is not str or _I1_REQUEST.fullmatch(req) is None
            or req in seen_requests
            or observation.request_id != req
            or row["native_session_id"] != native["native_session_id"]
            or type(row["native_seq"]) is not int
            or row["native_seq"] != observation.seq
            or row["native_seq"] <= original_probe.seq
            or original["seq"] != original_probe.seq
            or row["native_observation_ref"] != observation.provenance.reference
            or row["sense_revision"] !=
            f"mineflayer:{native['native_session_id']}:{observation.seq}"
            or row["resident_epoch"] != 1
            or row["paper_actor_uuid"] != link_by_self[sid]["paper_actor_uuid"]
            or type(row["paper_tick"]) is not int
            or row["paper_tick"] < original_boot["boot_tick"]
            or type(log_ref) is not str or log_ref not in prefixes
            or type(paper_ref) is not str
            or type(row["source_revision_refs"]) is not list
            or len(row["source_revision_refs"]) != 3
            or row["model_invoked"] is not False
            or row["action_issue_authorized"] is not False
        ):
            raise I1IndependentAuditHold("I1 CPU row not the exact original Native probe")
        refs = row["source_revision_refs"]
        expected_native = (
            f"native:{native['native_session_id']}:{native['observation_ref']}:"
            f"{original_probe.seq}:{original_probe.provenance.reference}"
        )
        expected_paper = (
            f"paper:{paper_session}:{original_boot['paper_boot_id']}:"
            f"{log_ref}:{paper_ref}"
        )
        if refs != [expected_native, expected_paper, row["sense_revision"]]:
            raise I1IndependentAuditHold("I1 composited Native/Paper/SENSE refs disagree")
        prefix_size = prefixes[log_ref]
        prefix = frozen[:prefix_size]
        if (prefix_size < prior_digest_size
                or prior_paper is not None and row["paper_tick"] < prior_paper):
            raise I1IndependentAuditHold("Paper source moved backward during CPU loop")
        try:
            _verify_main_thread_ack(
                executable, paper_session=paper_session, world_id=_SOURCE_WORLD,
                boot_id=original_boot["paper_boot_id"],
                ref=paper_ref, tick=row["paper_tick"],
                paper_stdout=prefix,
            )
            seen = parse_owned_paper_resident_trace(
                owned_paper_session_id=paper_session,
                expected_world_uuid=_SOURCE_WORLD,
                owned_paper_log=prefix,
                log_ref="i1-paper-prefix:" + log_ref,
            )
        except (OSError, RuntimeError, ValueError) as exc:
            raise I1IndependentAuditHold("independent original Paper ACK/prefix invalid") from exc
        for self_id in ("A", "B"):
            events = [event for event in seen.events if event.name == "Relay" + self_id]
            if (not events or events[0].event != "JOIN"
                    or any(event.event == "QUIT" for event in events)
                    or len({event.actor_uuid for event in events}) != 1
                    or events[0].actor_uuid != link_by_self[self_id]["paper_actor_uuid"]
                    or events[-1].tick > row["paper_tick"]):
                raise I1IndependentAuditHold("A/B Paper actor not alive at CPU epoch")
        _replay_cpu(row, observation, owners[sid], paper_session)
        processed[sid] += 1
        seen_requests.add(req)
        prior_paper = row["paper_tick"]
        prior_digest_size = prefix_size
        prior_nonce = paper_ref
    if processed != {"A": 2, "B": 2} or prior_nonce is None:
        raise I1IndependentAuditHold("two independently sourced CPU epochs per Self missing")
    return {
        "classification": _I1_AUDITED,
        "self_ids": ["A", "B"],
        "native_observation_counts": [["A", 2], ["B", 2]],
        "independent_paper_ack_per_epoch": True,
        "independent_cpu_replay": True,
        "unmodified_original_registry": True,
        "native_world_clock_is_not_paper_tick": True,
        "real_gemma_post": 0,
        "real_action_issued": 0,
        "qual_go": False,
        "science_run": False,
    }


def independently_audit_i1_original_cpu(
    result_path: Path, *, generation: Path, restored: Path,
    stage28b_evidence: Path, executable: Path,
) -> dict:
    """Two independent read-only gates. The older audit cannot promote I1."""
    base = independently_audit_recovered_real_rejoin(
        result_path, generation=generation, restored=restored,
        stage28b_evidence=stage28b_evidence, executable=executable,
        expected_gemma_posts=0, expected_i1_cpu_sense=True,
    )
    if base.get("classification") != _I1_BASE:
        raise I1IndependentAuditHold("original Native/Paper owner base not qualified")
    _, prepared = inspect_real_recovered_sources(
        generation, restored, stage28b_evidence,
    )
    schemas = prepare_i1_original_schema_bootstrap(prepared.cognitive_work)
    if (len(schemas) != 2 or any(schema.modules for schema in schemas)):
        raise I1IndependentAuditHold("old original Self Schema cannot be rebootstraped")
    path = Path(result_path)
    return _audit_i1_epochs(
        report=json.loads(path.read_bytes()), evidence=path.parent,
        executable=Path(executable), owners=prepared.owners,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--generation", type=Path, required=True)
    parser.add_argument("--restored", type=Path, required=True)
    parser.add_argument("--stage28b-evidence", type=Path, required=True)
    parser.add_argument("--execution-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = independently_audit_i1_original_cpu(
            args.result, generation=args.generation, restored=args.restored,
            stage28b_evidence=args.stage28b_evidence,
            executable=args.execution_dir,
        )
        print(json.dumps(result, sort_keys=True), flush=True)
        return 0
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as exc:
        print(
            f"I1_INDEPENDENT_AUDIT_HOLD={type(exc).__name__}:{exc}",
            file=sys.stderr, flush=True,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
