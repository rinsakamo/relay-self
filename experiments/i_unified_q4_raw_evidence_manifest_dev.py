"""U16: freeze raw original Q4 World DEV files, never claim World PASS.

This small manifest is an operator/evidence handoff to independent Q. It
cannot authenticate Native/Paper producers, prove STOP, unlock physical IO
or substitute for the actual unmodified source files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from pathlib import Path


class Q4RawManifestHold(ValueError):
    """Evidence custody is incomplete, ambiguous or changed while reading."""


_ROLES = (
    "native_stdout", "native_stdin", "paper_ticks", "owner_wal",
    "owner_cognition", "host_monotonic", "process_exit",
)
_MAX_BYTES = 32 * 1024 * 1024
_MANIFEST_VERSION = "q4-original-raw-evidence-dev-v1"


def _read_original(root: Path, source: Path) -> dict[str, object]:
    if (
        type(source) is not Path or not source.is_absolute()
        or source.is_symlink() or not source.is_file()
        or source.parent.is_symlink()
    ):
        raise Q4RawManifestHold("absolute non-symlink raw evidence file required")
    try:
        relative = source.relative_to(root)
    except ValueError as exc:
        raise Q4RawManifestHold("raw evidence escapes isolated trial root") from exc
    if not relative.parts or len(relative.parts) > 4:
        raise Q4RawManifestHold("bounded evidence path required")
    # No symlink in any path component; do not follow an escaping parent.
    if any((root.joinpath(*relative.parts[:i])).is_symlink()
           for i in range(1, len(relative.parts))):
        raise Q4RawManifestHold("symlink in original evidence parent")
    try:
        before = source.stat(follow_symlinks=False)
        fd = os.open(source, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            opened = os.fstat(fd)
            if (
                not stat.S_ISREG(opened.st_mode)
                or opened.st_dev != before.st_dev
                or opened.st_ino != before.st_ino
                or opened.st_size < 1 or opened.st_size > _MAX_BYTES
                or opened.st_nlink != 1
            ):
                raise Q4RawManifestHold("raw evidence file not stable and exclusive")
            digest = hashlib.sha256()
            total = 0
            while True:
                data = os.read(fd, 128 * 1024)
                if not data:
                    break
                total += len(data)
                if total > _MAX_BYTES:
                    raise Q4RawManifestHold("original evidence grew beyond cap")
                digest.update(data)
            end_fd = os.fstat(fd)
        finally:
            os.close(fd)
        after = source.stat(follow_symlinks=False)
    except OSError as exc:
        raise Q4RawManifestHold("original evidence inaccessible") from exc
    if (
        total != before.st_size or total != end_fd.st_size
        or end_fd.st_dev != before.st_dev or end_fd.st_ino != before.st_ino
        or end_fd.st_mtime_ns != before.st_mtime_ns
        or end_fd.st_ctime_ns != before.st_ctime_ns
        or (end_fd.st_mode & 0o777) != (before.st_mode & 0o777)
        or after.st_dev != before.st_dev or after.st_ino != before.st_ino
        or after.st_size != before.st_size
        or after.st_mtime_ns != before.st_mtime_ns
        or after.st_ctime_ns != before.st_ctime_ns
    ):
        raise Q4RawManifestHold("original raw bytes changed during readback")
    return {
        "path": relative.as_posix(),
        "sha256": digest.hexdigest(),
        "size_bytes": total,
        "device": before.st_dev,
        "inode": before.st_ino,
        "mtime_ns": before.st_mtime_ns,
    }


def seal_q4_original_raw_manifest(
    *, root: Path, mode: str, evidence: dict[str, Path],
    output: Path,
) -> dict[str, object]:
    """Seal a single isolated trial's exact 7 original files atomically.

    `two_moves` and `stop_failure` are *separate* runs; each must have
    independent full raw streams. This does not judge either as successful.
    """
    if (
        type(root) is not Path or not root.is_absolute() or root.is_symlink()
        or not root.is_dir() or root.resolve() != root
        or mode not in ("two_moves", "stop_failure")
        or type(output) is not Path or not output.is_absolute()
        or output.parent != root or output.is_symlink() or output.exists()
        or type(evidence) is not dict or set(evidence) != set(_ROLES)
    ):
        raise Q4RawManifestHold("fresh isolated Q4 trial root and all 7 originals required")
    values: dict[str, dict[str, object]] = {}
    seen: set[tuple[int, int]] = set()
    for role in _ROLES:
        item = _read_original(root, evidence[role])
        fingerprint = (item["device"], item["inode"])
        if fingerprint in seen:
            raise Q4RawManifestHold("two evidence roles alias the same raw file")
        seen.add(fingerprint)
        values[role] = item
    manifest: dict[str, object] = {
        "schema": _MANIFEST_VERSION,
        "trial": mode,
        "status": "RAW_EVIDENCE_MANIFEST_SEALED_NOT_VERIFIED",
        "real_world_dev_pass": False,
        "qual_go": False,
        "science_run": False,
        "independent_paper_source_audited": False,
        "independent_q_audited": False,
        "evidence": values,
    }
    payload = (
        json.dumps(manifest, sort_keys=True, ensure_ascii=False,
                   separators=(",", ":"), allow_nan=False) + "\n"
    ).encode("utf-8")
    # Refuse overwrites, links and fabricated success-only manifests.
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(output, flags, 0o600)
        try:
            os.write(fd, payload)
            os.fsync(fd)
        finally:
            os.close(fd)
        dirfd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(dirfd)
        finally:
            os.close(dirfd)
    except OSError as exc:
        raise Q4RawManifestHold("cannot seal exclusive evidence manifest") from exc
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--mode", choices=("two_moves", "stop_failure"), required=True)
    parser.add_argument("--out", required=True, type=Path)
    for role in _ROLES:
        parser.add_argument("--" + role.replace("_", "-"), required=True, type=Path)
    args = parser.parse_args()
    try:
        manifest = seal_q4_original_raw_manifest(
            root=args.root,
            mode=args.mode,
            evidence={role: getattr(args, role) for role in _ROLES},
            output=args.out,
        )
    except (Q4RawManifestHold, OSError, TypeError, ValueError) as exc:
        print(f"Q4_RAW_MANIFEST_HOLD: {exc}")
        return 2
    print(json.dumps({
        "status": manifest["status"], "real_world_dev_pass": False,
        "path": str(args.out), "entries": len(manifest["evidence"]),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
