"""Neutral identifier length control. Counterfactual DEV inputs only."""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import asdict, replace
from pathlib import Path

from adapters.llama_cpp.relay_engine import render_llama_cpp_request
from experiments.self_world_metadata_ablation import (
    _external_new,
    _nonmetadata,
    _surface,
    canonical,
    digest,
    prepare_arms,
)
from experiments.self_world_model_ab import W4ModelABBlocked, _write_new_report
from relay_self.provenance import Provenance
from relay_self.relay_engine import CognitionDatum, CognitionMode, RelayEngine

ARMS = ('R', 'S', 'NL', 'NS')
ORDER = (ARMS, ARMS, ('S', 'NS', 'R', 'NL'),
         ('NS', 'NL', 'S', 'R'), ('NL', 'R', 'NS', 'S'))
ANCHORS = ('4203cc3655ca41bc4df4dc489869aff65aa8b65ccdc965a5ce901557fee28fd2',
           '840a92f7880dd15e3d1189f572f941d5253f16e1543b455759842477c5b4f09b')
# Fixed before tokenizer/model launch. First matching n in [0, 1024] per target.
# SHA256 hex is meaningless alphanumeric; no model outputs enter selection.
PAYLOAD = ''.join(hashlib.sha256(f'w4-neutral-padding-v1:{i}'.encode()).hexdigest()
                  for i in range(16))
RULE = {'version': 1, 'self_id_base': 'n0', 'session_id': 'n1',
        'epoch_id': 'n2-after-5', 'reference': 'n1:5',
        'source_ref': 'present:n1:5:n3', 'payload': PAYLOAD,
        'candidate_order': 'prefix length 0..1024 ascending; first exact match',
        'targets': {'NL': 486, 'NS': 360}}


def anchors(source):
    old = prepare_arms(source)
    pair = (old['B'], old['D'])
    actual = tuple(digest(render_llama_cpp_request(r, mode=CognitionMode.BOUNDED,
                                                 model='gemma4-12b-q4km')) for r in pair)
    if actual != ANCHORS:
        raise W4ModelABBlocked('original R/S rendered SHA mismatch')
    return pair


def neutral(base, n):
    if type(n) is not int or not 0 <= n <= 1024:
        raise W4ModelABBlocked('padding length out of preregistered bounds')
    value = {'status': 'observed', 'coverage_truncated': False,
             'self_id': 'n0' + PAYLOAD[:n], 'session_id': 'n1',
             'epoch_id': 'n2-after-5', 'source_ref': 'present:n1:5:n3'}
    provenance = Provenance('mineflayer', 'n1:5')
    return replace(base, context=(
        CognitionDatum.from_value('self_world_observer', value, provenance),
        CognitionDatum.from_value('self_world_observed', [], provenance)))


def validate_control(arms):
    if tuple(arms) != ARMS:
        raise W4ModelABBlocked('four fixed arms required')
    for i, arm in enumerate(('R', 'S')):
        if digest(render_llama_cpp_request(arms[arm], mode=CognitionMode.BOUNDED,
                                          model='gemma4-12b-q4km')) != ANCHORS[i]:
            raise W4ModelABBlocked('anchor changed')
    baseline = _nonmetadata(arms['R'])
    for r in arms.values():
        if r.request_id != arms['S'].request_id or _nonmetadata(r) != baseline:
            raise W4ModelABBlocked('nonallowlisted change')
    for arm in ('NL', 'NS'):
        v = json.loads(arms[arm].context[0].value_json)
        n = len(v['self_id']) - 2
        if arms[arm] != neutral(arms['S'], n):
            raise W4ModelABBlocked('neutral template changed')


def freeze_control(arms, *, model, output, token_evidence):
    validate_control(arms)
    if token_evidence['counts'] != {'R': 486, 'S': 360, 'NL': 486, 'NS': 360}:
        raise W4ModelABBlocked('TOKENIZER_MATCH_BLOCKED')
    _external_new(output)
    rendered = {a: {m.value: render_llama_cpp_request(r, mode=m, model=model)
                    for m in (CognitionMode.BOUNDED, CognitionMode.THINK)}
                for a, r in arms.items()}
    def diff(a, b, path=''):
        if isinstance(a, dict) and isinstance(b, dict) and a.keys() == b.keys():
            return sum((diff(a[k], b[k], path + '/' + k) for k in a), [])
        if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)) and len(a) == len(b):
            return sum((diff(x, y, path + '/' + str(i))
                        for i, (x, y) in enumerate(zip(a, b))), [])
        return [] if a == b else [path]
    surfaces = {a: _surface(r) for a, r in arms.items()}
    plan = {'model': model, 'order': ORDER, 'rule': RULE,
            'scope': 'COUNTERFACTUAL_MODEL_INPUT_ONLY', 'expected_choice': 'DEFER_RECHECK',
            'token_evidence': token_evidence, 'surfaces': surfaces,
            'differences_from_R': {a: diff(surfaces['R'], s) for a, s in surfaces.items()},
            'neutral_difference': diff(surfaces['NS'], surfaces['NL']),
            'rendered': rendered,
            'request_sha256': {a: {m: digest(b) for m, b in modes.items()}
                               for a, modes in rendered.items()}}
    _write_new_report(output, plan)
    return hashlib.sha256(output.read_bytes()).hexdigest()


def execute_control(arms, *, provider, frozen: Path, frozen_sha256: str,
                      output: Path):
    """Exactly one finite block. Any exception retains journal and partial report.

    The recorder delegates each call to the existing provider unchanged. It is
    instrumentation, not a new inference engine or process owner. No retries.
    """
    validate_control(arms)
    if hashlib.sha256(frozen.read_bytes()).hexdigest() != frozen_sha256:
        raise W4ModelABBlocked('frozen manifest changed')
    plan = json.loads(frozen.read_bytes())
    for a, r in arms.items():
        for m in (CognitionMode.BOUNDED, CognitionMode.THINK):
            if digest(render_llama_cpp_request(r, mode=m, model=plan['model'])) != (
                plan['request_sha256'][a][m.value]
            ):
                raise W4ModelABBlocked('rendered request changed')
    journal = output.with_name(output.name + '.journal.jsonl')
    _external_new(output)
    _external_new(journal)
    if output.parent != frozen.parent or output.is_relative_to(Path(__file__).resolve().parents[1]):
        raise W4ModelABBlocked('exclusive external frozen evidence root required')
    # Reserve final output as well as journal before any model call.
    fd = os.open(output, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        jf = os.open(journal, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except BaseException:
        os.close(fd)
        raise
    rows, calls = [], []
    active = {}
    terminal = None
    with os.fdopen(fd, 'wb') as report, os.fdopen(jf, 'wb') as witness:
        def record(value):
            witness.write(canonical(value) + b'\n')
            witness.flush()
            os.fsync(witness.fileno())

        def counted(request, *, mode):
            if mode not in (CognitionMode.BOUNDED, CognitionMode.THINK) or len(calls) >= 40:
                raise W4ModelABBlocked('provider call ceiling or mode violated')
            if digest(render_llama_cpp_request(request, mode=mode, model=plan['model'])) != (
                plan['request_sha256'][active['arm']][mode.value]
            ):
                raise W4ModelABBlocked('provider-bound request changed')
            call = {**active, 'event': 'provider', 'call': len(calls) + 1,
                    'mode': mode.value, 'request_sha256': plan['request_sha256'][active['arm']][mode.value]}
            calls.append(call)
            record({**call, 'event': 'provider_start'})
            start = time.perf_counter_ns()
            try:
                result = provider(request, mode=mode)
                call.update(status=result.status.value, choice_id=result.choice_id,
                            facts=asdict(result.call_facts) if result.call_facts else None)
                return result
            except BaseException as exc:
                call.update(error_type=type(exc).__name__, error=str(exc))
                raise
            finally:
                call['wall_ns'] = time.perf_counter_ns() - start
                record(call)

        engine = RelayEngine(counted)
        record({'event': 'begin', 'frozen_sha256': frozen_sha256, 'order': ORDER})
        try:
            for repeat, order in enumerate(ORDER):
                for position, arm in enumerate(order):
                    active = {'arm': arm, 'repeat': repeat, 'position': position,
                              'warmup': repeat == 0, 'index': len(rows)}
                    row = {**active, 'expected_choice': 'DEFER_RECHECK',
                           'request_sha256': plan['request_sha256'][arm]['bounded']}
                    first = len(calls)
                    start = time.perf_counter_ns()
                    record({**row, 'event': 'request_start'})
                    try:
                        result = engine(arms[arm])
                        row.update(status=result.status.value, choice_id=result.choice_id,
                                   escalated=result.escalated,
                                   prompt_tokens=result.observed_prompt_tokens,
                                   completion_tokens=result.observed_completion_tokens)
                    except BaseException as exc:
                        row.update(error_type=type(exc).__name__, error=str(exc))
                        raise
                    finally:
                        row.update(provider_calls=len(calls) - first,
                                   think_calls=sum(c['mode'] == 'think' for c in calls[first:]),
                                   wall_ns=time.perf_counter_ns() - start)
                        rows.append(row)
                        record({**row, 'event': 'request_end'})
        except BaseException as exc:
            terminal = {'error_type': type(exc).__name__, 'error': str(exc)}
            raise
        finally:
            result = {'classification': 'W4_SELF_WORLD_NEUTRAL_METADATA_LENGTH_CONTROL_DEV_RESULT'
                      if terminal is None else 'DEV_FAIL', 'scope': 'DEV_ONLY',
                      'qualification': 'NO_GO', 'science': 'NOT_RUN',
                      'frozen_sha256': frozen_sha256, 'rows': rows, 'calls': calls,
                      'terminal': terminal, 'bounded_requests': len(rows),
                      'provider_calls': len(calls)}
            record({'event': 'terminal', 'error': terminal, 'provider_calls': len(calls)})
            result['journal_sha256'] = hashlib.sha256(journal.read_bytes()).hexdigest()
            report.write(canonical(result) + b'\n')
            report.flush()
            os.fsync(report.fileno())
    return result
