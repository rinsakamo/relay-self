"""Preregistered W4 metadata x request_id counterfactual DEV probe only.

These transient requests confer no observation, Memory or Action qualification.
Reuse the original renderer, RelayEngine and provider; never edit source replay.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import asdict, replace
from pathlib import Path

from adapters.llama_cpp.relay_engine import render_llama_cpp_request
from experiments.self_world_model_ab import (
    W4ModelABBlocked,
    _check_new_path,
    _request_digest,
    _synthetic_cases,
    _write_new_report,
    build_real_case,
)
from relay_self.relay_engine import (
    BoundedChoiceRequest,
    CognitionMode,
    RelayEngine,
)

ARMS = ('A', 'B', 'C', 'D')
ORDER = (('A', 'B', 'C', 'D'), ('A', 'B', 'C', 'D'),
         ('B', 'D', 'A', 'C'), ('D', 'C', 'B', 'A'), ('C', 'A', 'D', 'B'))
METADATA = ('self_id', 'session_id', 'epoch_id', 'source_ref')
ORIGINAL_DIGESTS = (
    '9958bce4b00a60b535a744ac1e6e37d90111af60a60dc0eef7c660eeb73a85e1',
    '4460fefa235a4957ba981af15444382e8c6426dc0d6510691283bfc0d39dc580',
)
PREREGISTRATION = 'https://github.com/rinsakamo/relay-self/issues/633#issuecomment-6363138292'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def _surface(request):
    if type(request) is not BoundedChoiceRequest:
        raise W4ModelABBlocked('BOUNDED only')
    value = asdict(request)
    for datum in value['context']:
        datum['value'] = json.loads(datum.pop('value_json'))
    return value


def _nonmetadata(request):
    value = _surface(request)
    value.pop('request_id')
    if tuple(d['key'] for d in value['context']) != (
        'self_world_observer', 'self_world_observed',
    ):
        raise W4ModelABBlocked('exact two context keys/order required')
    observer, observed = value['context']
    if (set(observer['value']) != {*METADATA, 'status', 'coverage_truncated'}
            or observer['value']['status'] != 'observed'
            or observer['value']['coverage_truncated'] is not False
            or observed['value'] != []
            or any(d['provenance']['source'] != 'mineflayer' for d in value['context'])):
        raise W4ModelABBlocked('fixed empty observed surface required')
    metadata = observer['value']
    refs = tuple(d['provenance']['reference'] for d in value['context'])
    if (refs[0] != refs[1] or not refs[0].startswith(metadata['session_id'] + ':')
            or not metadata['source_ref'].startswith('present:' + refs[0] + ':')
            or not metadata['epoch_id'].endswith('-after-' + refs[0].rsplit(':', 1)[1])):
        raise W4ModelABBlocked('incoherent metadata bundle')
    for key in METADATA:
        metadata.pop(key)
    for datum in value['context']:
        datum['provenance'].pop('reference')
    return value


def build_arms(real, synthetic):
    # Pinned original renderer digests also freeze instruction, choices, order,
    # optional fields and the complete coherent bundles, not just their shape.
    if tuple(_request_digest(r) for r in (real, synthetic)) != ORIGINAL_DIGESTS:
        raise W4ModelABBlocked('source request changed from original measured following')
    if _nonmetadata(real) != _nonmetadata(synthetic):
        raise W4ModelABBlocked('PREMODEL_BLOCKED: unexpected nonmetadata difference')
    arms = {'A': real, 'B': replace(real, request_id=synthetic.request_id),
            'C': replace(synthetic, request_id=real.request_id), 'D': synthetic}
    validate_arms(arms)
    return arms


def validate_arms(arms):
    if tuple(arms) != ARMS:
        raise W4ModelABBlocked('exact four arms/order required')
    if (_request_digest(arms['A']), _request_digest(arms['D'])) != ORIGINAL_DIGESTS:
        raise W4ModelABBlocked('diagonal original source changed')
    expected = (arms['A'], replace(arms['A'], request_id=arms['D'].request_id),
                replace(arms['D'], request_id=arms['A'].request_id), arms['D'])
    if tuple(arms.values()) != expected:
        raise W4ModelABBlocked('metadata/request_id allowlist violated')
    if any(_nonmetadata(r) != _nonmetadata(arms['A']) for r in arms.values()):
        raise W4ModelABBlocked('nonmetadata mismatch')


def prepare_arms(source_root: Path):
    real = build_real_case(source_root).prepared.following_bounded
    synthetic = next(c for c in _synthetic_cases() if c.case_id == 'synthetic-empty')
    return build_arms(real, synthetic.prepared.following_bounded)


def _external_new(path):
    _check_new_path(path)
    forbidden = (Path(__file__).resolve().parents[1],
                 Path('/home/rinsa/work/rsee-model-only-evidence-20261023'),
                 Path('/home/rinsa/work/w4-observation-dev-20261023'),
                 Path('/home/rinsa/work/w4-original-readback-20261023'))
    if any(path.is_relative_to(root) for root in forbidden):
        raise W4ModelABBlocked('immutable source or checkout output forbidden')


def freeze_requests(arms, *, model: str, output: Path):
    validate_arms(arms)
    _external_new(output)
    rendered = {a: {m.value: render_llama_cpp_request(r, mode=m, model=model)
                    for m in (CognitionMode.BOUNDED, CognitionMode.THINK)}
                for a, r in arms.items()}
    surfaces = {a: _surface(r) for a, r in arms.items()}
    changes = {}
    def diff(a, b, path=''):
        if isinstance(a, dict) and isinstance(b, dict) and a.keys() == b.keys():
            return sum((diff(a[k], b[k], path + '/' + k) for k in a), [])
        if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)) and len(a) == len(b):
            return sum((diff(x, y, path + '/' + str(i))
                        for i, (x, y) in enumerate(zip(a, b))), [])
        return [] if a == b else [path]
    for a in ARMS:
        changes[a] = diff(surfaces['A'], surfaces[a])
    manifest = {'preregistration': PREREGISTRATION, 'scope': 'COUNTERFACTUAL_MODEL_INPUT_ONLY',
                'order': ORDER, 'bounded_requests': 20, 'max_provider_calls': 40,
                'expected_choice': 'DEFER_RECHECK', 'model': model,
                'surfaces': surfaces, 'differences_from_A': changes,
                'rendered': rendered,
                'request_sha256': {a: {m: digest(b) for m, b in modes.items()}
                                   for a, modes in rendered.items()},
                'legacy_request_sha256': {a: _request_digest(r) for a, r in arms.items()}}
    _write_new_report(output, manifest)
    return hashlib.sha256(output.read_bytes()).hexdigest()


def execute_factorial(arms, *, provider, frozen: Path, frozen_sha256: str,
                      output: Path):
    """Exactly one finite block. Any exception retains journal and partial report.

    The recorder delegates each call to the existing provider unchanged. It is
    instrumentation, not a new inference engine or process owner. No retries.
    """
    validate_arms(arms)
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
            result = {'classification': 'W4_SELF_WORLD_METADATA_FACTORIAL_DEV_RESULT'
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
