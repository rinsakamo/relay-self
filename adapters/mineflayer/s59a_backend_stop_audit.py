"""S59-A read-only source/version admission for an in-flight L2 stop test.

NO stop commands are issued; source review does not prove runtime features.
This avoids misclassifying HTTP client close, reasoning_end, slot erase, or
whole-backend kill as independently acknowledged request-scoped cancellation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

SOURCE_HEAD_S57 = "e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d"
BINARY_SHA256_S57 = (
    "ad5d4787bc739ad88a55b614c18d29580b3ec071cad632edb0ebb42b89f78536"
)
REQUIRED_FILES = (
    "tools/server/README.md",
    "tools/server/server-context.cpp",
    "tools/server/server-http.cpp",
)


class StopAuditRejected(ValueError):
    """Runtime/source identity, documented stop API or stop ACK not established."""


def digest_file(path: Path) -> str:
    if not isinstance(path, Path) or not path.is_file():
        raise StopAuditRejected("readable pinned backend executable required")
    sha = hashlib.sha256()
    with path.open("rb") as data:
        for block in iter(lambda: data.read(1024 * 1024), b""):
            sha.update(block)
    return sha.hexdigest()


@dataclass(frozen=True, slots=True)
class StopSourceFacts:
    source_head: str
    binary_digest: str
    control_reasoning_end_only: bool
    slot_erase_deferred_when_busy: bool
    internal_cancel_task_exists: bool
    source_reader_sees_disconnect_predicate: bool
    documented_request_stop_ack: bool
    examined_source_files: tuple[str, ...]
    source_binary_build_binding_attested: bool = False

    @property
    def request_stop_admissible(self) -> bool:
        return self.documented_request_stop_ack and self.source_binary_build_binding_attested

    def public_report(self) -> dict[str, object]:
        return {
            "milestone": "S59-A",
            "status": "BLOCKED",
            "classification": "REQUEST_SCOPED_STOP_ACK_NOT_AVAILABLE_ON_QUALIFIED_PATH",
            "source_head": self.source_head,
            "binary_sha256": self.binary_digest,
            "source_files": list(self.examined_source_files),
            "control_reasoning_end_only": self.control_reasoning_end_only,
            "slot_erase_deferred_when_busy": self.slot_erase_deferred_when_busy,
            "internal_cancel_task_exists": self.internal_cancel_task_exists,
            "source_reader_sees_disconnect_predicate": self.source_reader_sees_disconnect_predicate,
            "documented_request_stop_ack": self.documented_request_stop_ack,
            "source_binary_build_binding_attested": self.source_binary_build_binding_attested,
            "request_stop_admissible": self.request_stop_admissible,
            "runtime_model_call_attempted": False,
            "backend_stop_command_sent": False,
            "gpu_preemption_claimed": False,
            "gpu_vram_released_claimed": False,
            "note": (
                "Static pinned-source feasibility only; independently prove the "
                "exact runtime process and a request-scoped stop ACK before "
                "any physical promotion. No stop endpoint is assumed."
            ),
        }


def inspect_pinned_source_text(
    readme: str, context: str, http: str, *,
    source_head: str, binary_digest: str,
) -> StopSourceFacts:
    if source_head != SOURCE_HEAD_S57 or binary_digest != BINARY_SHA256_S57:
        raise StopAuditRejected("S57 exact source/binary authority mismatch")
    p = context.find("this->post_control =")
    q = context.find("case SERVER_TASK_TYPE_SLOT_ERASE:")
    c = context.find("case SERVER_TASK_TYPE_CANCEL:")
    if min(p, q, c) < 0:
        raise StopAuditRejected("expected pinned server API internals missing")
    control_section = context[p : p + 1100]
    erase_section = context[q : q + 1200]
    cancel_section = context[c : c + 400]
    control_only = (
        'action != "reasoning_end"' in control_section
        and "unknown control action" in control_section
        and "reasoning_end" in readme
    )
    erase_deferred = (
        "if (slot->is_processing())" in erase_section
        and "queue_tasks.defer" in erase_section
        and "action=erase" in readme
    )
    internal_cancel = (
        "SERVER_TASK_TYPE_CANCEL" in cancel_section
        and "slot.release()" in cancel_section
    )
    # Do not confuse a predicate captured by the HTTP adapter with a native
    # completion-stop ACK or proof that the generation loop uses it.
    source_reads_disconnect = "is_connection_closed" in context
    if (
        not control_only or not erase_deferred or not internal_cancel
        or "is_connection_closed" not in http
    ):
        raise StopAuditRejected("exact S57 source features do not match review")
    return StopSourceFacts(
        source_head=source_head,
        binary_digest=binary_digest,
        control_reasoning_end_only=control_only,
        slot_erase_deferred_when_busy=erase_deferred,
        internal_cancel_task_exists=internal_cancel,
        source_reader_sees_disconnect_predicate=source_reads_disconnect,
        documented_request_stop_ack=False,
        examined_source_files=REQUIRED_FILES,
    )


def source_git_identity(source_dir: Path) -> str:
    if not isinstance(source_dir, Path) or not source_dir.is_dir():
        raise StopAuditRejected("existing exact source checkout required")
    try:
        head = subprocess.run(
            ["git", "-C", str(source_dir), "rev-parse", "HEAD"],
            capture_output=True, check=True, text=True, timeout=10,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "-C", str(source_dir), "status", "--porcelain",
             "--untracked-files=no"],
            capture_output=True, check=True, text=True, timeout=10,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError) as exc:
        raise StopAuditRejected("source checkout cannot be independently read") from exc
    if head != SOURCE_HEAD_S57 or dirty:
        raise StopAuditRejected("unqualified source revision or modified tracked files")
    return head


def audit(binary: Path, source_dir: Path,
          expected_binary_sha256: str) -> StopSourceFacts:
    if (
        not isinstance(expected_binary_sha256, str)
        or not re.fullmatch(r"[0-9a-fA-F]{64}", expected_binary_sha256)
        or expected_binary_sha256.lower() != BINARY_SHA256_S57
    ):
        raise StopAuditRejected("exact S57 binary checksum not declared")
    binary_digest = digest_file(binary)
    if binary_digest != expected_binary_sha256.lower():
        raise StopAuditRejected("binary checksum mismatch")
    head = source_git_identity(source_dir)
    try:
        contents = [
            (source_dir / relative).read_text(encoding="utf-8")
            for relative in REQUIRED_FILES
        ]
    except (OSError, UnicodeError) as exc:
        raise StopAuditRejected("pinned source files unavailable") from exc
    return inspect_pinned_source_text(
        *contents, source_head=head, binary_digest=binary_digest,
    )


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--llama-server", type=Path, required=True)
    p.add_argument("--expected-binary-sha256", required=True)
    p.add_argument("--source-checkout", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    args = p.parse_args()
    try:
        result = audit(
            args.llama_server, args.source_checkout,
            args.expected_binary_sha256,
        ).public_report()
    except (StopAuditRejected, OSError, ValueError) as exc:
        result = {
            "milestone": "S59-A",
            "status": "BLOCKED",
            "classification": "PINNED_STOP_SOURCE_AUDIT_UNQUALIFIED",
            "error_type": type(exc).__name__,
            "runtime_model_call_attempted": False,
            "backend_stop_command_sent": False,
            "gpu_preemption_claimed": False,
        }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print("S59_AUDIT=" + json.dumps(result, sort_keys=True))
    # Neither "matching static source" nor an invalid source is permission
    # to perform a destructive or mislabeled stop experiment.
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
