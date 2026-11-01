"""Readonly sole-collector hook. Host read order is not Paper physical time."""
from __future__ import annotations

import hashlib
import json
import math
import os
import time
from dataclasses import asdict
from pathlib import Path

from adapters.mineflayer.self_body_s50_l1_motion_prediction import from_archival_readback
from adapters.mineflayer.self_body_s50_l1_motion_prequential import (
    TargetWorldIdentity,
    freeze_for_target,
)


class _ObservedLogPath(type(Path())):
    """Per-call sink capability; leaves protected collector and Path global intact."""
    def open(self, mode='r', *args, **kwargs):
        sink = super().open(mode, *args, **kwargs)
        if mode != 'w':
            return sink
        observer = self.observer

        class Sink:
            pending = ''

            def __enter__(inner):
                sink.__enter__()
                return inner

            def write(inner, line):
                result = sink.write(line)
                inner.pending += line
                return result

            def flush(inner):
                sink.flush()
                pending, inner.pending = inner.pending, ''
                if pending:
                    observer(pending.encode('utf-8'))

            def __exit__(inner, *exc):
                return sink.__exit__(*exc)

        return Sink()


class HostPrediction:
    def __init__(self, path: Path):
        archive = Path(__file__).resolve().parents[2] / (
            'docs/evidence/issue651-route-b-20261031/run1/independent-original-readback.json'
        )
        self.training = from_archival_readback(json.loads(archive.read_text()))
        self.path = path
        with path.open('xb'):
            pass
        self.identity = None
        self.ticket = None
        self.last_tick = None
        self.count = 0
        self.write('TRAINING_FIXED', training=asdict(self.training))

    def collector_log(self, path):
        observed = _ObservedLogPath(path)
        observed.observer = self.observe
        return observed

    def write(self, kind, **payload):
        with self.path.open('ab') as out:
            out.write((json.dumps(dict(kind=kind, host_monotonic_ns=time.monotonic_ns(),
                                      **payload), allow_nan=False) + '\n').encode())
            out.flush()
            os.fsync(out.fileno())

    def arm(self, session, action, marker):
        if self.identity is not None:
            raise ValueError('MP3 already armed')
        self.identity = (session, action, marker)
        self.write('ARM', session=session, action=action, marker=marker)

    def observe(self, raw):
        if self.identity is None or b'S50_' not in raw:
            return
        line = raw.decode('utf-8', errors='strict')
        fields = dict(x.split('=', 1) for x in line.split() if '=' in x)
        session, action, marker = self.identity
        if fields.get('marker_id') != marker:
            return
        digest = hashlib.sha256(raw).hexdigest()
        if 'M02_DEV_S50_PHASE ' in line and fields.get('phase') == 'PRE_FORWARD':
            if self.ticket is not None:
                raise ValueError('duplicate PRE_FORWARD')
            self.ticket = freeze_for_target(self.training, TargetWorldIdentity(
                session, fields['world'], action, self.training.subject_uuid,
            ), capture_mode='PROSPECTIVE_LOCAL_ORDER_NOT_EXTERNALLY_ATTESTED')
            self.write('TARGET_FIXED', ticket=asdict(self.ticket), source_line_sha256=digest,
                       subject_status='PLANNED_FROM_TRAINING_VERIFY_WITH_ORIGINAL_INPUT')
        if 'S50_DEV_WAIT_TICK ' in line:
            if self.ticket is None or fields['world'] != self.ticket.target.paper_world_uuid:
                raise ValueError('unbound WAIT')
            tick = int(fields['tick'])
            if int(fields['index']) != self.count + 1 or (
                self.last_tick is not None and tick != self.last_tick + 1
            ) or self.count >= 8:
                raise ValueError('invalid callback order')
            displacement = math.dist([float(fields['from_' + k]) for k in 'xyz'],
                                     [float(fields[k]) for k in 'xyz'])
            if not math.isfinite(displacement):
                raise ValueError('nonfinite displacement')
            self.count += 1
            self.last_tick = tick
            self.write('OBSERVED', tick=tick, index=self.count, displacement_m=displacement,
                       source_line_sha256=digest)
            if self.count < 8:
                self.write('PREDICTION_FIXED', target_tick=tick + 1,
                           prediction_m=self.ticket.model.slope * displacement,
                           last_m=displacement, zero_m=0.0,
                           ticket_sha256=self.ticket.ticket_sha256,
                           ceiling='HOST_BEFORE_NEXT_READ_ONLY_PAPER_TIME_NOT_ATTESTED')
