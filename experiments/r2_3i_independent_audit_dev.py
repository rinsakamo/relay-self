"""Read-only audit of the frozen R2-3i Paper, Native, WAL and HTTP records."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from adapters.llama_cpp.relay_engine import parse_llama_cpp_decision, render_llama_cpp_request
from adapters.mineflayer.python_protocol import (
    MineflayerAdapterStarted,
    MineflayerObservation,
    MineflayerStreamDecoder,
)
from experiments.p0d_real_paper_smoke_dev import file_sha256
from experiments.stage24g_model_gate_dev import PINNED_STAGE24G_GGUF_SHA256
from relay_self.b_np1b_initial_source_dev import _revision
from relay_self.paper_tick_witness_dev import _receipt
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    BoundedChoice,
    BoundedChoiceRequest,
    CognitionDatum,
    CognitionMode,
)
from relay_self.resident_paper_presence_join_dev import (
    join_resident_paper_presence,
    parse_owned_paper_resident_trace,
)
from relay_self.stage28c2b_native_paper_body_link_dev import paper_tick_ack_matches
from relay_self.world_resident_lifecycle_dev import (
    LogoutFenceEvidence,
    NativeLoginEvidence,
    WorldLifetime,
)


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def read_native(path: Path, actor: str) -> tuple[str, dict]:
    decoder = MineflayerStreamDecoder()
    with path.open(encoding="utf-8") as source:
        started = decoder.decode(next(source))
        require(isinstance(started, MineflayerAdapterStarted)
                and started.config.username == actor, "Native actor mismatch")
        probes = {}
        for line in source:
            event = decoder.decode(line)
            if isinstance(event, MineflayerObservation) and event.kind == "probe":
                require(event.request_id not in probes, "duplicate Native request")
                probes[event.request_id] = event
        require(bool(probes), "missing Native probe")
    return started.session_id, probes


def verify_manifest(root: Path) -> None:
    manifest = root / "sha256-manifest.json"
    paths = set(root.rglob("*"))
    require(not root.is_symlink() and not any(p.is_symlink() for p in paths),
            "symlink in evidence tree")
    expected = {p.relative_to(root).as_posix(): file_sha256(p)
                for p in paths if p.is_file() and p != manifest}
    require(json.loads(manifest.read_bytes()) == expected, "evidence manifest mismatch")


def audit_tick(root, raw, world, boot, tick, ref):
    match = re.fullmatch(r"paper-main-thread:p0d:([\w-]+):([\w-]+):sha256:([0-9a-f]{64})", ref)
    require(match is not None and match[1] == boot, "Paper tick boot mismatch")
    ack = (root / "paper-tick-spool" / "acks" / f"{match[2]}.ack").read_bytes()
    require(hashlib.sha256(ack).hexdigest() == match[3] and _receipt(ack) == {
        "boot_id": boot, "nonce": match[2], "paper_tick": str(tick),
        "server_session_id": world.paper_session_id, "source": "PAPER_MAIN_THREAD",
        "world_uuid": world.world_id,
    } and paper_tick_ack_matches(
        source_ref=ref, boot_id=boot, session_id=world.paper_session_id,
        world_id=world.world_id, tick=tick, log=raw,
    ), "Paper tick ACK mismatch")


def audit_world(root: Path, report: dict) -> dict:
    def load(name):
        return json.loads((root / name).read_bytes())

    require(report.get("cleanup_uncertain", False) is False
            and report["world_attempts"] == 1 and report["original_rejoin_dev"] is True
            and re.fullmatch(r"[0-9a-f]{40}", report["exact_git_head"]) is not None,
            "Original trial identity or cleanup uncertain")
    stop = load("paper-stopped.json")
    trial = json.loads((root / "original-world-rejoin.json").read_bytes())
    login = NativeLoginEvidence(**trial["a_relogin_evidence"])
    retired = LogoutFenceEvidence(**load("A-first-logout-original.json"))
    world = WorldLifetime(login.world_id, login.branch_id, login.paper_session_id,
                          login.world_epoch, 0)
    require(report["world_uuid"] == world.world_id
            and trial["paper_session_id"] == world.paper_session_id
            and stop["world_id"] == world.world_id
            and stop["old_server_session_id"] == world.paper_session_id
            and stop["process_exit_code"] == 0 and stop["all_dimensions_saved"] is True,
            "Paper save/stop mismatch")
    raw = (root / f"{world.paper_session_id}.log").read_bytes()
    cut = (root / "paper-joined-cut.log").read_bytes()
    previous = b""
    for phase in ("initial", "historical", "offline", "rejoin"):
        current = (root / f"paper-{phase}.log").read_bytes()
        require(current.startswith(previous) and len(current) > len(previous),
                f"Paper {phase} is not an advancing original prefix")
        previous = current
    require(raw.startswith(cut) and cut.startswith(previous)
            and b"Saved the game" in raw and b"Stopping server" in raw,
            "owned Paper lifecycle log mismatch")
    trace_args = dict(owned_paper_session_id=world.paper_session_id,
                      expected_world_uuid=world.world_id)
    trace = parse_owned_paper_resident_trace(**trace_args, owned_paper_log=cut, log_ref="cut")
    final_trace = parse_owned_paper_resident_trace(**trace_args, owned_paper_log=raw, log_ref="stop")
    for actor, edges in (("RelayA", ["JOIN", "QUIT", "JOIN", "QUIT"]),
                         ("RelayB", ["JOIN", "QUIT"])):
        require([e.event for e in final_trace.events if e.name == actor
                 and e.event in ("JOIN", "QUIT")] == edges, f"Paper {actor} edges mismatch")
    require(trace.boot_id == final_trace.boot_id == trial["paper_boot"],
            "Paper boot mismatch")
    paper_pid = int((root / f"{world.paper_session_id}.pid").read_text())
    stop_boot = stop["tick_source_ref"].split(":")[2]
    audit_tick(root, raw, world, stop_boot, stop["logical_tick"], stop["tick_source_ref"])

    old_a, a_probes = read_native(root / "native-RelayA-1.jsonl", "RelayA")
    b, b_probes = read_native(root / "native-RelayB-2.jsonl", "RelayB")
    new_a, rejoin_probes = read_native(root / "native-RelayA-3.jsonl", "RelayA")
    result = join_resident_paper_presence(
        trace=trace, world=world, a_name="RelayA", b_name="RelayB",
        a_logout=retired, a_relogin=login,
        original_b_native=b, surviving_b_native=b,
    )
    require((old_a, new_a, b) == (result.prior_native_a, result.new_native_a,
                                result.continuous_native_b), "Native rotation mismatch")
    native = report["native_processes"]
    require(set(native) == {old_a, new_a, b}
            and all(type(p["returncode"]) is int and p["pid"] > 0 for p in native.values())
            and len({p["pid"] for p in native.values()}) == 3, "Native retirement/PID mismatch")
    continuity = load("original-B-continuity.json")
    pair = load("normal-cpu-world-source-readback.json")

    digests = set()
    prefix = hashlib.sha256()
    for line in raw.splitlines(keepends=True):
        prefix.update(line)
        digests.add(prefix.hexdigest())

    def check_source(receipt, sid, session, probes, actor_uuid):
        probe = probes[receipt["native_request_id"]]
        require((receipt["self_id"], receipt["native_session_id"], receipt["native_sequence"],
                 receipt["native_source_ref"], receipt["native_world_time"])
                == (sid, session, probe.seq, probe.provenance.reference,
                    probe.snapshot.time.day * 24000 + probe.snapshot.time.time_of_day),
                "Native probe and Original Source mismatch")
        require((receipt["world_id"], receipt["world_epoch"], receipt["paper_session_id"],
                 receipt["paper_pid"], receipt["paper_actor_uuid"])
                == (world.world_id, world.epoch, world.paper_session_id, paper_pid, actor_uuid),
                "Paper and Original Source scope mismatch")
        require(receipt["paper_log_sha256"] in digests, "Paper Source prefix SHA mismatch")
        audit_tick(root, raw, world, receipt["paper_boot_id"],
                   receipt["paper_tick"], receipt["paper_tick_ref"])

    for name in ("normal-cpu-original-A-initial", "normal-cpu-original-A-composite"):
        check_source(load(name + ".json"), "A", old_a, a_probes, result.a_actor_uuid)
    b_initial = load("normal-cpu-original-B-initial.json")
    check_source(b_initial, "B", b, b_probes, result.b_actor_uuid)
    for phase in ("first", "later"):
        check_source(pair[f"{phase}_a"], "A", new_a, rejoin_probes, result.a_actor_uuid)
        check_source(pair[f"{phase}_b"], "B", b, b_probes, result.b_actor_uuid)
    require(pair["first_b"]["native_sequence"] > b_initial["native_sequence"]
            and pair["later_b"]["native_sequence"] > pair["first_b"]["native_sequence"]
            and continuity["same_owner_retained_and_intent"] is True
            and continuity["scope"] == [b_initial["resident_epoch"], b, world.epoch]
            and continuity["owned_child_pid"] == native[b]["pid"],
            "B Owner continuity mismatch")
    live = root / "original-live-source.json"
    if live.is_file():
        original = json.loads(live.read_bytes())
        a_cut, b_cut = original["a_composite"], original["b_composite"]
        check_source(a_cut, "A", new_a, rejoin_probes, result.a_actor_uuid)
        check_source(b_cut, "B", b, b_probes, result.b_actor_uuid)
        for key, receipt in (("a", a_cut), ("b", b_cut)):
            require(original[f"{key}_scope"] == [receipt["resident_epoch"],
                    receipt["native_session_id"], receipt["world_epoch"]]
                    and original[f"{key}_source_refs"] == [
                        f'native:{receipt["native_session_id"]}:{receipt["native_request_id"]}:'
                        f'{receipt["native_sequence"]}:{receipt["native_source_ref"]}',
                        f'paper:{receipt["paper_session_id"]}:{receipt["paper_boot_id"]}:'
                        f'{receipt["paper_log_sha256"]}:{receipt["paper_tick_ref"]}',
                        f'composite:rejoin:{receipt["composite_revision"]}',
                    ], "Original CURRENT ref mismatch")
        require(a_cut["paper_log_sha256"] == b_cut["paper_log_sha256"]
                and original["source_pair_revision"] == _revision(dict(
                    a_composite=a_cut["composite_revision"], b_composite=b_cut["composite_revision"],
                    a_native=a_cut["native_revision"], b_native=b_cut["native_revision"],
                    paper_sha256=a_cut["paper_log_sha256"],
                )), "Original CURRENT pair mismatch")
    for sid, session in (("A", new_a), ("B", b)):
        proof = LogoutFenceEvidence(**load(f"{sid}-final-logout-original.json"))
        require(proof.self_id == sid and proof.world_epoch == world.epoch
                and proof.native_session_id == session and proof.native_terminated
                and proof.physical_wal_clear and proof.no_physical_inflight
                and proof.physical_issuer_revoked and proof.stale_gpu_fenced
                and proof.peer_transport_drained, "final logout fence mismatch")
        require(not PhysicalActionJournal.read_snapshot(root / f"final-{sid}-wal.json",
                                                        self_id=sid, require_clear=True),
                "Physical WAL not empty")
    return {"world_uuid": world.world_id, "paper_pid": paper_pid, "paper_boot": trace.boot_id,
            "a_old": old_a, "a_new": new_a, "b_continuous": b,
            "paper_ticks": [result.a_quit_tick, result.b_later_tick, result.a_rejoin_tick]}


def decode_request(raw: dict) -> BoundedChoiceRequest:
    def datum(data):
        return CognitionDatum(data["key"], data["value_json"], Provenance(**data["provenance"]))

    return BoundedChoiceRequest(**{
        **raw, "choices": tuple(BoundedChoice(**choice) for choice in raw["choices"]),
        "context": tuple(datum(item) for item in raw["context"]),
        "identity_context": datum(raw["identity_context"]),
    })


def audit_http(root: Path) -> dict:
    summary = root / "original-question-result.json"
    if not summary.exists() and not (root / "gemma").exists():
        return {"attempts": 0, "captured": False, "reason": "World stopped before model stage"}
    report = json.loads(summary.read_bytes())
    posts = report["post_attempted"]
    require(type(posts) is int and posts in (0, 1), "Question POST count invalid")
    if posts == 0:
        return {"attempts": 0, "captured": False, "reason": report.get("reason")}
    gemma = root / "gemma"
    http = gemma / "original-question-model-http"
    names = {"bounded-1-request-body.bin", "bounded-1-response-body.bin",
             "bounded-1-http-evidence.json"}
    require({p.name for p in http.iterdir()} <= names, "unexpected repeated HTTP capture")
    if not (http / "bounded-1-http-evidence.json").is_file():
        return {"attempts": 1, "captured": False, "reason": "HTTP exchange incomplete"}
    exchange = json.loads((http / "bounded-1-http-evidence.json").read_bytes())
    for kind in ("request", "response"):
        body = (http / f"bounded-1-{kind}-body.bin").read_bytes()
        require(exchange[f"{kind}_body_sha256"] == hashlib.sha256(body).hexdigest()
                and exchange[f"{kind}_body_bytes"] == len(body), "HTTP body mismatch")
    gate = json.loads((gemma / "model-gate.json").read_bytes())
    request = json.loads((http / "bounded-1-request-body.bin").read_bytes())
    require(gate["gguf_sha256"] == PINNED_STAGE24G_GGUF_SHA256
            and gate["slot_count"] == 1 and gate["slot_id"] == 0
            and gate["model_alias"] == request["model"]
            and exchange["ordinal"] == 1, "HTTP/model gate mismatch")
    response = json.loads((http / "bounded-1-response-body.bin").read_bytes())
    model = json.loads((gemma / "r23h-original-real-model-report.json").read_bytes())
    frozen = decode_request(model["original_request"])
    rendered = render_llama_cpp_request(frozen, mode=CognitionMode.BOUNDED, model=gate["model_alias"])
    require(request == rendered and model["model_post_attempted"] == 1
            and model["original_request_id"] == frozen.request_id, "frozen Original HTTP request mismatch")
    terminal = model.get("backend_terminal_idle", {})
    ticket = model.get("original_gpu_ticket", {})
    original = model["original_first_rejoin_source"]
    require(original == json.loads((root / "original-live-source.json").read_bytes()),
            "Question preflight Source mismatch")
    for stage in ("initial", "terminal"):
        body = gemma / f"{stage}-slots.bin"
        if body.is_file():
            slots = json.loads(body.read_bytes())
            require(type(slots) is list and len(slots) == 1 and slots[0]["id"] == 0
                    and slots[0]["is_processing"] is False, "raw slot witness mismatch")
    attested = (
        exchange["http_status"] == 200 and response.get("model") == gate["model_alias"]
        and terminal.get("is_processing") is False and terminal.get("n_slots") == 1
        and all((gemma / f"{stage}-slots.bin").is_file() for stage in ("initial", "terminal"))
        and model.get("terminal_source_revision_refs") == model["original_source_revision_refs"]
        == original["a_source_refs"]
        and model.get("terminal_source_pair_revision") == original["source_pair_revision"]
        and ticket.get("purpose") == "original_rejoin_question"
        and ticket.get("self_id") == "A"
        and [ticket.get(k) for k in ("self_epoch", "native_session_id", "world_epoch")]
        == original["a_scope"]
        and ticket.get("work_ref") == model["original_work_ref"]
        and ticket.get("request_id") == model["original_request_id"]
        and model["original_request"]["focus"] == original["request_question_ref"]
        and model["question_adopted"] is False and model["memory_written"] is False
        and model["physical_issue_authorized"] is False
        and report["classification"] == "TERMINAL_SOURCE_VALIDATED"
    )
    if attested:
        content = response["choices"][0]["message"]["content"]
        decision = parse_llama_cpp_decision(content, mode=CognitionMode.BOUNDED)
        selection = {"1": "ADOPT", "2": "HOLD", "3": "DECLINE"}.get(
            decision.choice_id, "UNRESOLVED",
        )
        require(model["selection"] == selection, "terminal Original model selection mismatch")
    return {"attempts": 1, "captured": True, "attested": attested,
            "http_status": exchange["http_status"], "usage": response.get("usage")}



def audit_initial_world(root: Path, report: dict) -> dict:
    """Verify the independently measurable part of a stopped early trial."""
    stop = json.loads((root / "paper-stopped.json").read_bytes())
    session = stop["old_server_session_id"]
    world = WorldLifetime(report["world_uuid"], stop["branch_id"], session, 0, 0)
    raw = (root / f"{session}.log").read_bytes()
    initial = (root / "paper-initial.log").read_bytes()
    require(raw.startswith(initial) and stop["world_id"] == world.world_id
            and stop["process_exit_code"] == 0 and stop["all_dimensions_saved"] is True
            and b"Saved the game" in raw and b"Stopping server" in raw,
            "initial Paper prefix/save mismatch")
    trace = parse_owned_paper_resident_trace(
        owned_paper_session_id=session, expected_world_uuid=world.world_id,
        owned_paper_log=initial, log_ref="initial",
    )
    require(len({e.actor_uuid for e in trace.events}) == 2, "initial Paper actor mismatch")
    native = {}
    for index, sid in enumerate(("A", "B"), 1):
        actor = f"Relay{sid}"
        events = [e.event for e in trace.events if e.name == actor]
        require(events and events[0] == "JOIN" and events.count("JOIN") == 1
                and "QUIT" not in events and "PRESENT" in events, "initial Paper JOIN/PRESENT missing")
        native_id, probes = read_native(root / f"native-{actor}-{index}.jsonl", actor)
        process = report["native_processes"][native_id]
        require(type(process["returncode"]) is int and process["pid"] > 0,
                "initial owned Native process exit missing")
        require(not PhysicalActionJournal.read_snapshot(root / f"final-{sid}-wal.json",
                                                        self_id=sid, require_clear=True),
                "initial Physical WAL not empty")
        native[sid] = {"session": native_id, "pid": process["pid"], "probes": len(probes)}
    require(native["A"]["session"] != native["B"]["session"], "initial Native collision")
    audit_tick(root, raw, world, stop["tick_source_ref"].split(":")[2],
               stop["logical_tick"], stop["tick_source_ref"])
    return {"world_uuid": world.world_id, "paper_boot": trace.boot_id,
            "paper_pid": int((root / f"{session}.pid").read_text()),
            "paper_stop_tick": stop["logical_tick"], "native": native,
            "owner_cleanup_uncertain": report.get("cleanup_uncertain", False)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    root = args.evidence
    result = {}
    try:
        verify_manifest(root)
        report = json.loads((root / "resident-presence-result.json").read_bytes())
        result["manifest"] = "VERIFIED"
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"manifest": "HOLD", "reason": str(exc)}, indent=2))
        return 2
    for key, verify in (("world", lambda: audit_world(root, report)),
                        ("model", lambda: audit_http(root))):
        try:
            result[key] = verify()
        except (OSError, ValueError, KeyError, TypeError, AttributeError, StopIteration) as exc:
            result[key] = {"classification": "HOLD", "reason": str(exc)}
    if result["world"].get("classification") == "HOLD":
        try:
            result["initial_world"] = audit_initial_world(root, report)
        except (OSError, ValueError, KeyError, TypeError, AttributeError, StopIteration) as exc:
            result["initial_world"] = {"classification": "HOLD", "reason": str(exc)}
    tags = ["R2_3_PRODUCT_L1_SWITCH_HOLD", "QUAL_NO_GO", "SCIENCE_NOT_RUN"]
    world_ok = result["world"].get("classification") != "HOLD"
    model = result["model"]
    if world_ok:
        tags.extend(("R2_3I_REAL_ORIGINAL_A_REJOIN_B_CONTINUITY_DEV_PASS",
                     "R2_3I_INDEPENDENT_SOURCE_AUDITED_DEV_PASS"))
    if model.get("captured"):
        tags.append("R2_3I_REAL_GEMMA_ONE_SHOT_CAPTURED")
    if world_ok and model.get("attested"):
        tags.append("R2_3I_ORIGINAL_SOURCE_RESULT_ATTESTED_DEV_PASS")
    result["qualifications"] = tags
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if world_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
