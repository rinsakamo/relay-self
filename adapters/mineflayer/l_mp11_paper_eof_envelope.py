"""Future-run-only original Paper EOF envelope, not a historical requalification.

Original raw bytes are NEVER rewritten. Only two exact shutdown forms are
recognized: complete-line EOF, or a complete line followed by the JLine
single prompt b'> '. This envelope MUST be opted in before future execution.
"""
from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass

MAX_ORIGINAL_BYTES = 16_000_000
SCHEMA = "L_MP11_PAPER_EOF_ENVELOPE_V1"
PROMPT = b"> "


class PaperEOFRejected(ValueError):
    """Unrecognized incomplete original Paper source at the EOF boundary."""


@dataclass(frozen=True, slots=True)
class PaperEOFEnvelope:
    schema: str
    original_sha256: str
    original_length: int
    complete_lines_sha256: str
    complete_lines_length: int
    suffix_hex: str
    end_state: str
    post_shutdown: bool
    admission: str = "FUTURE_RUN_OPT_IN_PAPER_SOURCE_SHAPE_ONLY"


def seal_after_shutdown(original: bytes, *, predeclared: bool) -> PaperEOFEnvelope:
    """Inspect raw bytes after process exit, with a pre-World protocol gate."""
    if (
        type(predeclared) is not bool or not predeclared
        or type(original) is not bytes
        or not 0 < len(original) <= MAX_ORIGINAL_BYTES
        or b"\x00" in original
    ):
        raise PaperEOFRejected("exact new run predeclared original is required")
    if original.endswith(b"\n"):
        complete, tail, state = original, b"", "EXACT_COMPLETE_LINES"
    elif original.endswith(b"\n" + PROMPT):
        complete, tail, state = original[:-len(PROMPT)], PROMPT, "JLINE_PROMPT_2_BYTES"
    else:
        raise PaperEOFRejected("truncated line, unsupported console suffix or malformed EOF")
    if (
        not complete.endswith(b"\n")
        or b"\r" in tail
        or not complete.strip()
    ):
        raise PaperEOFRejected("missing completed original Paper records")
    try:
        complete.decode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise PaperEOFRejected("invalid original UTF-8 in complete records") from exc
    return PaperEOFEnvelope(
        schema=SCHEMA,
        original_sha256=hashlib.sha256(original).hexdigest(),
        original_length=len(original),
        complete_lines_sha256=hashlib.sha256(complete).hexdigest(),
        complete_lines_length=len(complete),
        suffix_hex=tail.hex(),
        end_state=state,
        post_shutdown=True,
    )


def verified_complete_lines(
    original: bytes, report_envelope: object, *, predeclared: bool,
) -> bytes:
    """Recheck full original SHA and every envelope field, never trust a label."""
    if type(report_envelope) is not dict:
        raise PaperEOFRejected("missing bounded original envelope report")
    expected = asdict(seal_after_shutdown(original, predeclared=predeclared))
    if (report_envelope != expected
            or any(type(report_envelope[k]) is not type(v)
                   for k, v in expected.items())):
        raise PaperEOFRejected("original Paper envelope changed or foreign")
    n = expected["complete_lines_length"]
    return original[:n]
