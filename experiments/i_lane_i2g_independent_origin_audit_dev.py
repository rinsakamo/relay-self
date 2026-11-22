"""I2g independent NEW ORIGINAL A/B born-v3 source audit and immutable seal.

Do not run in the original Paper process. Read raw Native stdin/stdout,
owned Paper stdout, exact same-generation typed v3 A/B owner cuts; only
after all checks may a NEW root SHA256SUMS be written once. Pins and the
new inert fork are created OUTSIDE source evidence in the offline phase.
No new World, model, Action, derived Pattern, or historical Stage28b rewrite.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from adapters.mineflayer.python_protocol import (
    MineflayerEffectResult,
    MineflayerObservation,
    parse_mineflayer_line,
)
from experiments.p0d_real_paper_smoke_dev import _write_bytes_new
from relay_self.cognitive_minimal_dev import initial_patterns
from relay_self.i_lane_i2f_future_source_pins_dev import I2fFutureSourcePins
from relay_self.persistent_cognition import load_persistent_cognition
from relay_self.resident_paper_presence_join_dev import (
    parse_owned_paper_resident_trace,
)
from relay_self.self_owner_checkpoint_dev import verify_typed_generation
from relay_self.stage28c1_inert_restore_dev import (
    inspect_stage28c_source,
    prepare_stage28c_inert_restore,
)
from relay_self.stage28c2b_historical_native_sessions_dev import (
    inspect_original_stage28b_native_sessions,
)


class I2gIndependentOriginHold(RuntimeError):
    """New original born-v3 Native/Paper/Schema source not independently safe."""


_I2G_CLASS = "I2G_REAL_ORIGINAL_V3_TYPED_A_B_CAPTURED_AUDIT_PENDING"
_NESTED_HASHES = {
    "world/SHA256SUMS",
    "paper-dimensions/world_nether/SHA256SUMS",
    "paper-dimensions/world_the_end/SHA256SUMS",
}


@dataclass(frozen=True, slots=True)
class I2gOriginalSourceReview:
    generation_id: str
    source_world_id: str
    source_branch_id: str
    source_committed_sha256: str
    original_native_ids: tuple[str, str, str]
    source_native_sha256: tuple[tuple[str, str, str], ...]
    same_generation_born_v3: bool = True
    original_world_actually_executed_by_auditor: bool = False
    world_was_started_by_source_runner: bool = True
    real_model_post_count: int = 0
    physical_action_count: int = 0
    independent_source_seal_was_present: bool = False


def _sha(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise I2gIndependentOriginHold("original evidence missing or symlinked")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _root_files(
    evidence: Path, *, generation: Path, manifest_exists: bool,
) -> dict[str, str]:
    """Exact exclusive root inventory, with only three typed World hashes."""
    if evidence.is_symlink() or not evidence.is_dir() or generation.is_symlink():
        raise I2gIndependentOriginHold("original real Native/Paper evidence root required")
    source_root = evidence.resolve(strict=True)
    gen = generation.resolve(strict=True)
    if (gen.parent.parent != source_root
            or gen.parent.name != "typed-world-self-generations"):
        raise I2gIndependentOriginHold("only actual original typed generation checksum files")
    prefix = gen.relative_to(source_root).as_posix() + "/"
    expected_nested = {prefix + p for p in _NESTED_HASHES}
    entries = {}
    nested = set()
    for p in sorted(evidence.rglob("*")):
        if p.is_symlink():
            raise I2gIndependentOriginHold("symlink in original source")
        if p.is_dir():
            continue
        if not p.is_file():
            raise I2gIndependentOriginHold("non-file in original source")
        name = p.relative_to(evidence).as_posix()
        if name == "SHA256SUMS":
            if not manifest_exists:
                raise I2gIndependentOriginHold("unexpected root manifest")
            continue
        if name.endswith("/SHA256SUMS"):
            nested.add(name)
            continue
        entries[name] = _sha(p)
    if nested != expected_nested or not entries:
        raise I2gIndependentOriginHold("three typed Paper original checksum sources required")
    return entries


def _require_i2h_original_paper_continuity(*, trace, trial: dict) -> None:
    """Check original A/B real Paper actor and epoch sequence, not just counts.

    This is a source-stream-only condition. It does not authenticate a Popen,
    nor does it bridge the Paper main-thread clock to Native day time.
    """
    events = trace.events
    if (
        any(x.name not in ("RelayA", "RelayB") for x in events)
        or not events
    ):
        raise I2gIndependentOriginHold("foreign Paper player in original isolated World")
    a = [x for x in events if x.name == "RelayA"]
    b = [x for x in events if x.name == "RelayB"]
    a_joins = [x for x in a if x.event == "JOIN"]
    a_quits = [x for x in a if x.event == "QUIT"]
    b_joins = [x for x in b if x.event == "JOIN"]
    b_quits = [x for x in b if x.event == "QUIT"]
    if (
        len(a_joins) != 2 or len(a_quits) != 2
        or len(b_joins) != 1 or len(b_quits) != 1
        or len({x.actor_uuid for x in a}) != 1
        or len({x.actor_uuid for x in b}) != 1
        or a[0].actor_uuid == b[0].actor_uuid
        or trial.get("a_actor_uuid") != a[0].actor_uuid
        or trial.get("b_actor_uuid") != b[0].actor_uuid
        or trial.get("a_paper_quit_tick") != a_quits[0].tick
        or trial.get("a_paper_rejoin_tick") != a_joins[1].tick
        or trial.get("b_paper_continuation_tick") is None
        or type(trial["b_paper_continuation_tick"]) is not int
        or a[0].line != a_joins[0].line
        or a[-1].line != a_quits[1].line
        or b[0].line != b_joins[0].line
        or b[-1].line != b_quits[0].line
    ):
        raise I2gIndependentOriginHold("Paper A/B actor identity and original receipts differ")
    if not (
        a_joins[0].line < b_joins[0].line < a_quits[0].line
        < a_joins[1].line < a_quits[1].line < b_quits[0].line
    ):
        raise I2gIndependentOriginHold("Paper A/B original logout-reJOIN epoch order wrong")
    # In the full original _owned_resident_trial, B has to remain online
    # (PRESENT or MOVE) strictly between A's first QUIT and next JOIN.
    between = [
        x for x in b if a_quits[0].line < x.line < a_joins[1].line
        and x.event in ("PRESENT", "MOVE")
    ]
    before = [
        x for x in b if b_joins[0].line <= x.line < a_quits[0].line
    ]
    if (
        not between or not before
        or trial["b_paper_continuation_tick"] != between[-1].tick
        or not any(x.event in ("PRESENT", "MOVE") for x in a
                if a_joins[0].line < x.line < a_quits[0].line)
    ):
        raise I2gIndependentOriginHold("Paper B continuation or A two resident epochs absent")


def independently_read_i2g_original(
    *, evidence: Path, generation: Path,
) -> I2gOriginalSourceReview:
    """Read-only original byte-level audit before any source manifest exists.

    Does not certify model or operator's actual local hardware from a report.
    Source qualification requires further pin comparison before I2f World.
    """
    evidence, generation = Path(evidence), Path(generation)
    if evidence.is_symlink() or generation.is_symlink():
        raise I2gIndependentOriginHold("symlinked source")
    root = evidence.resolve(strict=True)
    source = generation.resolve(strict=True)
    try:
        if source.parent.parent != root or source.parent.name != "typed-world-self-generations":
            raise I2gIndependentOriginHold("same original trial typed generation not in evidence")
        report_file = root / "resident-presence-result.json"
        report = json.loads(report_file.read_bytes())
        if (
            type(report) is not dict or report.get("classification") != _I2G_CLASS
            or report.get("i2g_original_v3_source") is not True
            or report.get("i2g_initial_source_verified") is not True
            or report.get("i2g_source_manifest_independent_verified") is not False
            or report.get("real_gpu") is not False
            or report.get("real_b_physical_action") is not False
            or report.get("autonomous_l1_skill_selection") is not False
            or report.get("cleanup_uncertain")
            or type(report.get("steps")) is not list or len(report["steps"]) != 1
            or type(report.get("i2g_original_raw_native")) is not list
            or len(report["i2g_original_raw_native"]) != 3
        ):
            raise I2gIndependentOriginHold("one passive real original born-v3 trial not attested")
        trial = report["steps"][0]
        world_id = trial["world_uuid"]
        branch_id = "p0d-real-resident-presence"
        if (report.get("world_uuid") != world_id
                or report["typed_world_self_generation"] != str(source)
                or trial["typed_world_self_generation"] != str(source)
                or trial.get("b_actual_physical_action") is not False
                or trial.get("b_move_action_causality") is not False
                or trial.get("real_l1_l2_gpu_executed") is not False
                or trial.get("i2g_initial_exploration_pattern_learned") is not False
                or trial.get("i2g_initial_physical_action_issued") is not False
                or trial.get("i2g_original_issuer_observation_only") is not True):
            raise I2gIndependentOriginHold("unqualified World original trial/effect")
        checked = inspect_stage28c_source(
            source, expected_world_id=world_id,
            expected_source_branch_id=branch_id,
            expected_generation_id=source.name,
        )
        if checked.roster != ("A", "B"):
            raise I2gIndependentOriginHold("source cut lost one original Self")
        cuts = verify_typed_generation(source)
        if tuple(c.self_id for c in cuts) != ("A", "B"):
            raise I2gIndependentOriginHold("new generation typed source lost A/B")
        receipt = report["i2g_initial_schema_receipt"]
        if (
            receipt.get("self_ids") != ["A", "B"]
            or receipt.get("born_initial_only") is not True
            or receipt.get("learning_claimed") is not False
            or receipt.get("physical_action_authorized") is not False
            or receipt.get("original_registry_revisions") != [["A", 0], ["B", 0]]
            or receipt.get("schema_modes") != [
                ["A", "NO_EXPLORATION_MODULE"], ["B", "NO_EXPLORATION_MODULE"],
            ]
        ):
            raise I2gIndependentOriginHold("new A/B source Schema was not original empty v3")
        initial_sha = dict(receipt["initial_cognition_sha256"])
        if set(initial_sha) != {"A", "B"}:
            raise I2gIndependentOriginHold("born cognition SHA provenance missing")
        for cut in cuts:
            sid = cut.self_id
            actual = source / "selves" / sid / "cognition.json"
            saved = load_persistent_cognition(actual)
            if (
                cut.pattern_registry != initial_patterns()
                or cut.recorded_schema is None
                or cut.recorded_schema.self_id != sid
                or cut.recorded_schema.modules
                or cut.recorded_schema.revision != 0
                or saved.pattern_registry != cut.pattern_registry
                or saved.memories or saved.exploration_continuity is not None
                or cut.cognition_sha256 != _sha(actual)
                or initial_sha[sid] != _sha(actual)
            ):
                raise I2gIndependentOriginHold(
                    "no learned Pattern and exact initial durable born Schema required"
                )
        # Archive actual original owned Paper stdout, not a generated event
        # summary, and correlate 2 A JOINs plus one continuing B JOIN.
        session = trial["paper_session_id"]
        if type(session) is not str or not session.startswith("paper-owned-"):
            raise I2gIndependentOriginHold("original owned Paper session missing")
        paper_stdout = root / (session + ".log")
        raw_paper = paper_stdout.read_bytes()
        trace = parse_owned_paper_resident_trace(
            owned_paper_session_id=session, expected_world_uuid=world_id,
            owned_paper_log=raw_paper,
            log_ref="i2g-original-paper:" + session + ":sha256:" + _sha(paper_stdout),
        )
        _require_i2h_original_paper_continuity(trace=trace, trial=trial)
        # OwnedPaperWorld writes a PID file for the exact Popen instance.
        # PID is supporting attribution only (never process authentication).
        pid_source = root / (session + ".pid")
        pid_raw = pid_source.read_text(encoding="utf-8")
        if (
            re.fullmatch(r"[1-9][0-9]{0,9}\n", pid_raw) is None
            or b"Saved the game" not in raw_paper
            or b"Stopping server" not in raw_paper
            or raw_paper.rfind(b"Saved the game")
            > raw_paper.rfind(b"Stopping server")
        ):
            raise I2gIndependentOriginHold(
                "original Paper owned PID/flush/terminal stdout missing"
            )
        paper_pid = int(pid_raw.strip())
        # The B first Native must remain identical through A's logout/reJOIN.
        first = trial["i2g_original_first_login_evidence"]
        second_a = trial["a_relogin_evidence"]
        expected = {
            first["A"]["native_session_id"]: ("A", first["A"]),
            first["B"]["native_session_id"]: ("B", first["B"]),
            second_a["native_session_id"]: ("A", second_a),
        }
        if (
            len(expected) != 3
            or expected[first["A"]["native_session_id"]][0] != "A"
            or expected[first["B"]["native_session_id"]][0] != "B"
            or trial["a_original_native_session"]
            != first["A"]["native_session_id"]
            or trial["b_original_native_session"]
            != first["B"]["native_session_id"]
            or trial["b_probe"]["session"]
            != first["B"]["native_session_id"]
        ):
            raise I2gIndependentOriginHold("original A/B Native actor/session lineage wrong")
        saved_native = {cut.self_id: cut.former_native_session_id for cut in cuts}
        if (saved_native != {
            "A": second_a["native_session_id"],
            "B": first["B"]["native_session_id"],
        }):
            raise I2gIndependentOriginHold(
                "recorded v3 Original Owner does not match last actual Native A/B"
            )
        for idx, (sid, login) in enumerate((
            ("A", first["A"]), ("B", first["B"]), ("A", second_a),
        )):
            if (
                login.get("self_id") != sid
                or login.get("native_session_id") not in expected
                or login.get("paper_session_id") != session
                or login.get("world_id") != world_id
                or login.get("branch_id") != branch_id
                or login.get("world_epoch") != 0
                or login.get("login_seq") != (2 if idx == 2 else 1)
                or any(login.get(key) is not True for key in (
                    "old_native_invalidated", "physical_wal_clear",
                    "stale_gpu_fenced", "stale_transport_fenced",
                    "new_native_source_verified",
                ))
                or login.get("action_issue_authorized") is not False
            ):
                raise I2gIndependentOriginHold(
                    "Original A/B native identity, issuer and born epoch not fully witnessed"
                )
        captured = {}
        for item in report["i2g_original_raw_native"]:
            uid, name = item["native_session_id"], item["username"]
            if (
                type(uid) is not str
                or re.fullmatch(r"[A-Za-z0-9-]{1,150}", uid) is None
                or uid not in expected or uid in captured
                or name != "Relay" + expected[uid][0]
                or type(item["pid"]) is not int or item["pid"] <= 0
                or item["pid"] == paper_pid
            ):
                raise I2gIndependentOriginHold("missing or foreign actual Native child process")
            out = root / f"i2g-native-{name}-{uid}.jsonl"
            commands = root / f"i2g-commands-{name}-{uid}.jsonl"
            if (
                item["raw_stdout_sha256"] != _sha(out)
                or item["raw_stdin_sha256"] != _sha(commands)
                or item["raw_stdout_bytes"] != out.stat().st_size
                or item["raw_stdin_bytes"] != commands.stat().st_size
                or not out.read_bytes().endswith(b"\n")
                or not commands.read_bytes().endswith(b"\n")
                or out.stat().st_size > 32 * 1024 * 1024
                or commands.stat().st_size > 128 * 1024
            ):
                raise I2gIndependentOriginHold("actual original Native raw source bytes changed")
            # Every outbound byte must be an observation request, never an
            # effect. The response must be exact current native session
            # and contain exactly its original login request-correlated probe.
            requests = []
            for line in commands.read_bytes().splitlines():
                row = json.loads(line)
                if (
                    type(row) is not dict or set(row) != {"type", "request_id"}
                    or row["type"] != "observe"
                    or type(row["request_id"]) is not str
                    or not row["request_id"]
                ):
                    raise I2gIndependentOriginHold("original source issued physical Native command")
                requests.append(row["request_id"])
            if len(set(requests)) != len(requests):
                raise I2gIndependentOriginHold("replayed Native observe command")
            probes = []
            last_seq = -1
            for line in out.read_bytes().splitlines():
                msg = parse_mineflayer_line(line.decode("utf-8"))
                if (msg.session_id != uid or type(msg.seq) is not int
                        or msg.seq <= last_seq
                        or isinstance(msg, MineflayerEffectResult)):
                    raise I2gIndependentOriginHold("foreign/reordered/native physical stdout")
                last_seq = msg.seq
                if isinstance(msg, MineflayerObservation) and msg.kind == "probe":
                    probes.append(msg)
            # For this passive birth trial the entire outbound command
            # census is fixed: A's two separate sessions each LOGIN probe,
            # and B's single continuous native session LOGIN + one observe.
            expected_count = 2 if uid == first["B"]["native_session_id"] else 1
            if (
                len(requests) != expected_count
                or len(probes) != expected_count
                or {p.request_id for p in probes} != set(requests)
                or any(requests.count(p.request_id) != 1 for p in probes)
            ):
                raise I2gIndependentOriginHold(
                    "unpaired or excess passive Native stdin/stdout observation"
                )
            native_login = expected[uid][1]
            matched = [p for p in probes if p.request_id == native_login["observation_ref"]]
            if (
                len(matched) != 1
                or matched[0].snapshot.time is None
                or matched[0].snapshot.time.day * 24000
                + matched[0].snapshot.time.time_of_day
                != native_login["observed_world_tick"]
                or requests.count(native_login["observation_ref"]) != 1
            ):
                raise I2gIndependentOriginHold("original current Native World clock not witnessed")
            if expected[uid][0] == "B":
                manual = trial["b_probe"]["request_id"]
                if (
                    requests.count(manual) != 1
                    or len([p for p in probes if p.request_id == manual]) != 1
                ):
                    raise I2gIndependentOriginHold("B continuing real Native probe missing")
            captured[uid] = (name, item["raw_stdout_sha256"], item["raw_stdin_sha256"])
        if set(captured) != set(expected):
            raise I2gIndependentOriginHold("complete original A/B+A Native raw sources missing")
        return I2gOriginalSourceReview(
            source.name, world_id, branch_id, checked.committed_sha256,
            tuple(sorted(captured)),
            tuple((uid, captured[uid][1], captured[uid][2])
                  for uid in sorted(captured)),
        )
    except I2gIndependentOriginHold:
        raise
    except (OSError, RuntimeError, ValueError, TypeError, KeyError, AttributeError) as exc:
        raise I2gIndependentOriginHold(
            "original new-v3 World, Native, Paper, or model-free Self source incomplete"
        ) from exc


def seal_i2g_original_manifest_once(
    *, evidence: Path, generation: Path,
) -> tuple[I2gOriginalSourceReview, str, int]:
    """Separate-process explicit immutable SHA256SUMS; never re-seals."""
    review = independently_read_i2g_original(
        evidence=evidence, generation=generation,
    )
    root = Path(evidence)
    if (root / "SHA256SUMS").exists() or (root / "SHA256SUMS").is_symlink():
        raise I2gIndependentOriginHold("original source already sealed")
    inventory = _root_files(root, generation=generation, manifest_exists=False)
    manifest_bytes = "".join(
        f"{digest}  {path}\n" for path, digest in sorted(inventory.items())
    ).encode()
    _write_bytes_new(root / "SHA256SUMS", manifest_bytes)
    digest = _sha(root / "SHA256SUMS")
    try:
        attested = inspect_original_stage28b_native_sessions(
            root, generation, expected_manifest_sha256=digest,
            expected_files=len(inventory),
            expected_report_classification=_I2G_CLASS,
        )
        if (
            set(attested.historical_native_sessions)
            != set(review.original_native_ids)
            or attested.source_manifest_sha256 != digest
        ):
            raise I2gIndependentOriginHold("final source root seal differs from actual Native")
    except (ValueError, RuntimeError, OSError) as exc:
        raise I2gIndependentOriginHold(
            "new original manifest failed after first immutable write; retain HOLD"
        ) from exc
    return review, digest, len(inventory)


def prepare_i2g_inert_fork_and_pins_once(
    *, evidence: Path, generation: Path,
    sealed_manifest_sha256: str, manifest_files: int,
    destination: Path, restore_id: str, pins_output: Path,
) -> I2fFutureSourcePins:
    """New fork only after independent seal; never issue World/Model."""
    if (
        type(sealed_manifest_sha256) is not str
        or re.fullmatch(r"[0-9a-f]{64}", sealed_manifest_sha256) is None
        or type(manifest_files) is not int or manifest_files < 1
        or pins_output.is_symlink() or pins_output.exists()
        or not pins_output.parent.is_dir()
        or any(
            source == pins_output.resolve() or source in pins_output.resolve().parents
            for source in (
                evidence.resolve(), generation.resolve(), destination.resolve()
            )
        )
    ):
        raise I2gIndependentOriginHold("external fixed original pins and fresh fork required")
    review = independently_read_i2g_original(
        evidence=evidence, generation=generation,
    )
    inspected = inspect_original_stage28b_native_sessions(
        evidence, generation, expected_manifest_sha256=sealed_manifest_sha256,
        expected_files=manifest_files,
        expected_report_classification=_I2G_CLASS,
    )
    if set(inspected.historical_native_sessions) != set(review.original_native_ids):
        raise I2gIndependentOriginHold("external pins differ from original Native actor history")
    restored = prepare_stage28c_inert_restore(
        generation, destination,
        expected_world_id=review.source_world_id,
        expected_source_branch_id=review.source_branch_id,
        expected_committed_sha256=review.source_committed_sha256,
        restore_id=restore_id, expected_generation_id=review.generation_id,
    )
    pins = I2fFutureSourcePins(
        review.source_world_id, review.source_branch_id,
        review.source_committed_sha256, restored.restored_branch_id,
        sealed_manifest_sha256, manifest_files,
    )
    # Re-verify the sealed source after inert restore but before pin export.
    inspected_after = inspect_original_stage28b_native_sessions(
        evidence, generation, expected_manifest_sha256=sealed_manifest_sha256,
        expected_files=manifest_files,
        expected_report_classification=_I2G_CLASS,
    )
    if inspected_after != inspected:
        raise I2gIndependentOriginHold("original sealed evidence changed during inert restore")
    _write_bytes_new(
        pins_output,
        (json.dumps(asdict(pins), sort_keys=True, indent=2) + "\n").encode(),
    )
    return pins


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-evidence", type=Path, required=True)
    parser.add_argument("--generation", type=Path, required=True)
    operations = parser.add_mutually_exclusive_group(required=True)
    operations.add_argument("--inspect-unsealed", action="store_true")
    operations.add_argument("--seal-once", action="store_true")
    operations.add_argument("--prepare-fork-once", action="store_true")
    parser.add_argument("--expected-manifest-sha256")
    parser.add_argument("--manifest-files", type=int)
    parser.add_argument("--restored", type=Path)
    parser.add_argument("--restore-id")
    parser.add_argument("--pins-output", type=Path)
    args = parser.parse_args()
    try:
        if args.inspect_unsealed:
            if (
                args.expected_manifest_sha256 is not None
                or args.manifest_files is not None or args.restored is not None
                or args.restore_id is not None or args.pins_output is not None
            ):
                raise I2gIndependentOriginHold("read-only inspection may not seal/fork")
            receipt = independently_read_i2g_original(
                evidence=args.original_evidence, generation=args.generation,
            )
            print(json.dumps(asdict(receipt), sort_keys=True))
        elif args.seal_once:
            if (
                args.expected_manifest_sha256 is not None
                or args.manifest_files is not None or args.restored is not None
                or args.restore_id is not None or args.pins_output is not None
            ):
                raise I2gIndependentOriginHold("one seal cannot also prepare fork")
            receipt, sha, count = seal_i2g_original_manifest_once(
                evidence=args.original_evidence, generation=args.generation,
            )
            print(json.dumps({
                "classification": "I2G_NEW_V3_ORIGINAL_NATIVE_PAPER_SOURCE_SEALED_DEV",
                "original_evidence_root_sha256": sha,
                "original_manifest_files": count,
                "review": asdict(receipt),
                "new_real_world_started_by_auditor": False,
                "real_gemma_posts": 0,
                "physical_action_count": 0,
            }, sort_keys=True))
        else:
            if (
                not args.expected_manifest_sha256
                or args.manifest_files is None
                or args.restored is None or args.restore_id is None
                or args.pins_output is None
            ):
                raise I2gIndependentOriginHold("sealed SHA and separate inert fork pin required")
            pins = prepare_i2g_inert_fork_and_pins_once(
                evidence=args.original_evidence, generation=args.generation,
                sealed_manifest_sha256=args.expected_manifest_sha256,
                manifest_files=args.manifest_files,
                destination=args.restored,
                restore_id=args.restore_id, pins_output=args.pins_output,
            )
            print(json.dumps({
                "classification": "I2G_NEW_V3_ORIGINAL_FORK_INERT_PINS_PREPARED_DEV",
                "pins": asdict(pins),
                "real_world_started": False, "real_model_post": 0,
            }, sort_keys=True))
        return 0
    except BaseException as exc:
        print(f"I2G_INDEPENDENT_ORIGINAL_HOLD={type(exc).__name__}:{exc}",
              file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
