"""U20: original one-slot bounded Gemma HTTP source compatible with Stage26.

Reuses the owned raw HTTP producer; no second inference lane, model retry,
Action permission, scripted choice, or source-authentication claim.
"""
from __future__ import annotations

import hashlib
import threading
from dataclasses import dataclass
from pathlib import Path

from experiments.stage28c2c_real_original_l1_dev import (
    OriginalRawBoundedLlamaProvider,
)
from relay_self.relay_engine import (
    BoundedChoiceRequest,
    CognitionMode,
    ProviderDecision,
)


class U20Stage26RawHold(RuntimeError):
    """Original Stage26 HTTP request/response provenance cannot be replayed."""


@dataclass(frozen=True, slots=True)
class U20Stage26RawReceipt:
    request_path: str
    request_sha256: str
    response_path: str
    response_sha256: str
    response_bytes: int


class U20Stage26RawBoundedProvider(OriginalRawBoundedLlamaProvider):
    """Bind each existing raw HTTP POST to its actual Stage26 request ID.

    The inherited producer permits only two ordinary bounded POSTs; a call
    that errors remains attempted and is never retried. Receipts are minted
    only after an actual HTTP response has been captured and model parsing
    has completed. Readback rechecks disk bytes each time the Owner asks.
    """

    def __init__(
        self, *, endpoint: str, model: str, raw_dir: Path,
        timeout: float = 45.0,
    ) -> None:
        super().__init__(
            endpoint=endpoint, model=model, raw_dir=raw_dir, timeout=timeout,
        )
        self._stage26_gate = threading.Lock()
        self._stage26_receipts: dict[str, U20Stage26RawReceipt] = {}

    def __call__(
        self, request: BoundedChoiceRequest, *, mode: CognitionMode,
    ) -> ProviderDecision:
        if (
            not isinstance(request, BoundedChoiceRequest)
            or mode is not CognitionMode.BOUNDED
            or type(request.request_id) is not str
            or not request.request_id
        ):
            raise U20Stage26RawHold("only actual Stage26 bounded request is allowed")
        # One actual model POST at a time, even if a caller submits work
        # outside the existing ResidentLlamaInferenceLane single GPU slot.
        with self._stage26_gate:
            if request.request_id in self._stage26_receipts:
                raise U20Stage26RawHold("same original model request cannot replay")
            ordinal = self.attempted + 1
            answer = super().__call__(request, mode=mode)
            if (
                not isinstance(answer, ProviderDecision)
                or self.attempted != ordinal
                or self.completed != ordinal
                or len(self.source_receipts) != ordinal
            ):
                raise U20Stage26RawHold("original HTTP response not terminal")
            origin = self.source_receipts[-1]
            if (
                origin.get("ordinal") != ordinal
                or origin.get("http_status") != 200
            ):
                raise U20Stage26RawHold("original HTTP ordinal/status mismatch")
            prefix = "bounded-" + str(ordinal)
            request_file = self.raw_dir / (prefix + "-request-body.bin")
            response_file = self.raw_dir / (prefix + "-response-body.bin")
            if (
                any(
                    path.is_symlink() or not path.is_file()
                    or path.parent != self.raw_dir
                    for path in (request_file, response_file)
                )
            ):
                raise U20Stage26RawHold("actual HTTP source bytes missing")
            req = request_file.read_bytes()
            res = response_file.read_bytes()
            if (
                not req or not res
                or len(req) != origin.get("request_body_bytes")
                or len(res) != origin.get("response_body_bytes")
                or hashlib.sha256(req).hexdigest() != origin.get("request_body_sha256")
                or hashlib.sha256(res).hexdigest() != origin.get("response_body_sha256")
            ):
                raise U20Stage26RawHold("original HTTP source changed before adoption")
            self._stage26_receipts[request.request_id] = U20Stage26RawReceipt(
                str(request_file), origin["request_body_sha256"],
                str(response_file), origin["response_body_sha256"],
                len(res),
            )
            return answer

    def stage26_raw_receipt(self, request_id: str) -> U20Stage26RawReceipt:
        """Existing Stage26/27 source-receipt seam, not model permission."""
        if type(request_id) is not str or not request_id:
            raise U20Stage26RawHold("original Stage26 request ID required")
        with self._stage26_gate:
            old = self._stage26_receipts.get(request_id)
            if old is None:
                raise U20Stage26RawHold("no completed original Stage26 HTTP response")
            for path, digest in (
                (Path(old.request_path), old.request_sha256),
                (Path(old.response_path), old.response_sha256),
            ):
                if (
                    path.is_symlink() or not path.is_file()
                    or path.parent != self.raw_dir
                    or hashlib.sha256(path.read_bytes()).hexdigest() != digest
                ):
                    raise U20Stage26RawHold("Stage26 original HTTP bytes changed")
            return old
