"""Opt-in evidence capture for the B-NP1b Original Paper trial."""
from __future__ import annotations

import asyncio
import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

from experiments.p0d_real_paper_smoke_dev import _write_bytes_new, file_sha256
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.resident_paper_presence_join_dev import (
    parse_owned_paper_resident_trace,
)


@dataclass(frozen=True)
class OriginalQuestionModel:
    gguf: Path
    pid: int
    alias: str
    endpoint: str


def write_record(path: Path, value: object) -> None:
    _write_bytes_new(path, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode())


def require_passive_original(bridge) -> None:
    if not bridge.physical.observation_only or bridge.physical.active_action_ids:
        raise RuntimeError("R2-3i requires observation-only Original Physical")
    for sid, owner in bridge.owners.items():
        wal = PhysicalActionJournal.restore(owner.files.physical_wal_file, self_id=sid)
        if wal.records or wal.unresolved or owner.supervisor.open_actions:
            raise RuntimeError(f"R2-3i requires empty Original WAL for {sid}")


async def wait_for_paper_present(bridge, evidence: Path, phase: str, timeout: float) -> None:
    """Wait on original Paper events, with a separate clock from Native."""
    world = bridge.lifecycle.world
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        raw = bridge.paper.read_owned_log(world.paper_session_id)
        if b"P0D_RESIDENT event=PRESENT " in raw:
            trace = parse_owned_paper_resident_trace(
                owned_paper_session_id=world.paper_session_id,
                expected_world_uuid=world.world_id, owned_paper_log=raw, log_ref=phase,
            )
            a, b = ([event for event in trace.events if event.name == name]
                    for name in ("RelayA", "RelayB"))
            a_edges, b_edges = ([e for e in events if e.event in ("JOIN", "QUIT")]
                                for events in (a, b))
            expected = {
                "initial": ["JOIN"], "historical": ["JOIN"],
                "offline": ["JOIN", "QUIT"], "rejoin": ["JOIN", "QUIT", "JOIN"],
            }[phase]
            if ([e.event for e in a_edges] == expected
                    and [e.event for e in b_edges] == ["JOIN"]):
                cutoff = max(a_edges[-1].line, b_edges[-1].line)
                if phase == "historical":
                    initial = (evidence / "paper-initial.log").read_bytes()
                    cutoff = max(cutoff, len(initial.splitlines()))
                a_present = any(e.event == "PRESENT" and e.line > cutoff for e in a)
                b_present = any(e.event == "PRESENT" and e.line > cutoff for e in b)
                if b_present and (a_present or phase == "offline"):
                    _write_bytes_new(evidence / f"paper-{phase}.log", raw)
                    return
        await asyncio.sleep(0.05)
    raise RuntimeError(f"Paper PRESENT deadline for {phase}")


async def capture_question(bridge, evidence: Path, model: OriginalQuestionModel | None) -> None:
    from experiments.r2_3h_original_rejoin_real_question_dev import (
        inspect_r23h_original_live_source,
        run_r23h_original_real_question_once,
    )

    require_passive_original(bridge)
    result: dict[str, object] = {"classification": "HOLD", "post_attempted": 0}
    try:
        source = inspect_r23h_original_live_source(bridge=bridge, self_id="A")
        write_record(evidence / "original-live-source.json", asdict(source))
        if model is None:
            result["reason"] = "MODEL_PREFLIGHT_HOLD: no admitted model"
            return
        readback = await run_r23h_original_real_question_once(
            bridge=bridge, self_id="A", gguf=model.gguf, llama_pid=model.pid,
            model_alias=model.alias, endpoint=model.endpoint,
            evidence_dir=evidence / "gemma", real_model_post_grant=True,
        )
        result.update(classification="TERMINAL_SOURCE_VALIDATED",
                      post_attempted=readback.model_post_attempted)
    except (RuntimeError, ValueError, OSError, TimeoutError) as exc:
        reasons = []
        cause = exc
        while cause is not None:
            reasons.append(f"{type(cause).__name__}: {cause}")
            cause = cause.__cause__
        result["reason"] = reasons
    finally:
        report = evidence / "gemma" / "r23h-original-real-model-report.json"
        if report.is_file():
            result["post_attempted"] = json.loads(report.read_bytes())["model_post_attempted"]
        write_record(evidence / "original-question-result.json", result)


def git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=Path(__file__).resolve().parents[1], text=True,
    ).strip()


def seal_evidence(evidence: Path) -> None:
    write_record(evidence / "sha256-manifest.json", {
        path.relative_to(evidence).as_posix(): file_sha256(path)
        for path in sorted(evidence.rglob("*")) if path.is_file()
    })
