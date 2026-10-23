"""Source-verified, ID-blinded SelfWorld experiment. DEV only, no source issuer.

Pseudo provenance has no Mineflayer, World, Action or Memory source authority.
Only load_sources establishes the pinned saved/fixture source boundary.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from dataclasses import asdict, replace
from pathlib import Path
from unittest.mock import patch

from adapters.llama_cpp.relay_engine import render_llama_cpp_request
from adapters.mineflayer.self_world_observation_only_cognition import (
    prepare_w4_offline_cognition_inputs,
)
from experiments import self_world_model_ab as original
from experiments.self_world_metadata_ablation import canonical, digest
from relay_self.provenance import Provenance
from relay_self.relay_engine import CognitionDatum, CognitionMode, RelayEngine

ORDER = (('RAW', 'SEM'), ('RAW', 'SEM'), ('SEM', 'RAW'),
         ('RAW', 'SEM'), ('SEM', 'RAW'))
CASE_IDS = ('w4-original-empty', 'match', 'mismatch', 'unknown', 'synthetic-empty')
PSEUDO = Provenance('DEV-only-semantic-projection-NOT-Mineflayer-source',
                    'fixed-no-source-authority')
REQUEST_ID = 'DEV-fixed-semantic-probe'
PREREGISTRATION = 'https://github.com/rinsakamo/relay-self/issues/633#issuecomment-6364340813'
MODES = (CognitionMode.BOUNDED, CognitionMode.THINK)
Blocked = original.W4ModelABBlocked


def load_sources(source_root):
    """Use unchanged real strict replay and unchanged four synthetic factories.

    Capture the replay handed to the existing verifier, including ATT/PRD,
    without copying or replacing its verification algorithm.
    """
    captured = []

    def checked(replay):
        result = prepare_w4_offline_cognition_inputs(replay)
        captured.append(replay)
        return result

    with patch.object(original, 'prepare_w4_offline_cognition_inputs', checked):
        cases = (original.build_real_case(source_root), *original._synthetic_cases())
    if tuple(c.case_id for c in cases) != CASE_IDS or len(captured) != 5:
        raise Blocked('fixed five verified sources required')
    return tuple(zip(cases, captured, strict=True))


def project(replay, epoch):
    """Reverify ATT/PRD, then allowlist only observed semantics and review values."""
    if epoch not in ('prior', 'following'):
        raise Blocked('invalid epoch')
    prepared = prepare_w4_offline_cognition_inputs(replay)
    raw = getattr(prepared, epoch + '_bounded')
    values = {d.key: json.loads(d.value_json) for d in raw.context}
    observer = values['self_world_observer']
    selected = values['self_world_observed']
    observed = [{k: e[k] for k in ('label', 'position', 'distance_m',
                                 'visible_action', 'origin')} for e in selected]
    if any(e['origin'] != 'observed' for e in observed):
        raise Blocked('only positive observations allowed')
    payload = {
        'probe_status': observer['status'],
        'coverage_truncated': observer['coverage_truncated'],
        'positive_observed_count': len(observed),
        'positive_observed_entities': observed,
        'uncertainty': 'Unlisted or unobserved entities are UNKNOWN; zero selected '
                       'does not establish World absence or safety.',
        'action_success': None,
    }
    if 'self_world_prediction_review' in values:
        review = values['self_world_prediction_review']
        payload['prediction_review'] = {k: review[k] for k in (
            'status', 'reason', 'variable_key', 'predicted_value',
            'observed_value', 'action_success')}
    return replace(raw, request_id=REQUEST_ID, context=(
        CognitionDatum.from_value('dev_semantic_view', payload, PSEUDO),))


def make_plan(sources, model):
    if tuple(c.case_id for c, _ in sources) != CASE_IDS:
        raise Blocked('source case order differs')
    epochs = []
    for case, replay in sources:
        verified = prepare_w4_offline_cognition_inputs(replay)
        if case.prepared != verified:
            raise Blocked('source-bound case differs from verified replay')
        for epoch in ('prior', 'following'):
            raw = getattr(verified, epoch + '_bounded')
            sem = project(replay, epoch)
            # Entire nonallowlisted surface is invariant, not just wording.
            if replace(sem, request_id=raw.request_id, context=raw.context) != raw:
                raise Blocked('nonallowlisted request mutation')
            requests = {'RAW': raw, 'SEM': sem}
            rendered = {a: {m.value: render_llama_cpp_request(r, mode=m, model=model)
                            for m in MODES} for a, r in requests.items()}
            epochs.append({
                'case_id': case.case_id, 'epoch': epoch,
                'source_class': case.source_class,
                'expected_choice': getattr(case, 'expected_' + epoch),
                'source_receipt': asdict(replay),
                'requests': {a: asdict(r) for a, r in requests.items()},
                'typed_request_sha256': {a: digest(asdict(r)) for a, r in requests.items()},
                'source_receipt_sha256': digest(asdict(replay)),
                'rendered': rendered,
                'request_sha256': {a: {m: digest(v) for m, v in body.items()}
                                   for a, body in rendered.items()},
                'allowlisted_changes': ['request_id', 'context'],
            })
    schedule = [{'epoch_index': e, 'repeat': repeat, 'position': pos,
                 'arm': arm, 'warmup': repeat == 0}
                for e in range(10) for repeat, order in enumerate(ORDER)
                for pos, arm in enumerate(order)]
    return {'preregistration': PREREGISTRATION, 'model': model,
            'scope': 'DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN',
            'pseudo_provenance': asdict(PSEUDO),
            'prohibition': 'SEM is never a World, Action or Memory source',
            'bounded_requests': 100, 'max_provider_calls': 200, 'open_requests': 0,
            'epochs': epochs, 'schedule': schedule}


def new_external(path, source_root):
    original._check_new_path(path)
    # Only an external sibling experiment root can receive outputs. Reject all
    # existing evidence roots and any checkout, including primary/old worktrees.
    repo = Path(__file__).resolve().parents[1]
    forbidden = (repo, source_root.resolve(),
                 Path('/home/rinsa/relay-self'),
                 Path('/home/rinsa/work/w4-observation-dev-20261023'),
                 Path('/home/rinsa/work/rsee-model-only-evidence-20261023'),
                 Path('/home/rinsa/work/w4-model-ab-evidence-20261023'),
                 Path('/home/rinsa/work/w4-selfworld-metadata-ablation-evidence-20261023'),
                 Path('/home/rinsa/work/w4-selfworld-neutral-metadata-length-evidence-20261023'))
    if any(path.is_relative_to(p) for p in forbidden):
        raise Blocked('source evidence or checkout collision')
    if any((p / '.git').exists() for p in path.parents):
        raise Blocked('checkout output forbidden')


def freeze(source_root, *, model, output):
    new_external(output, source_root)
    plan = make_plan(load_sources(source_root), model)
    original._write_new_report(output, plan)
    return hashlib.sha256(output.read_bytes()).hexdigest()


def validate_frozen(source_root, frozen, frozen_sha256):
    if hashlib.sha256(frozen.read_bytes()).hexdigest() != frozen_sha256:
        raise Blocked('frozen bytes changed')
    plan = json.loads(frozen.read_bytes())
    expected = make_plan(load_sources(source_root), plan['model'])
    if canonical(plan) != canonical(expected):
        raise Blocked('source/manifest/semantic payload/order/budget mismatch')
    return plan


def execute(source_root, *, provider, frozen, frozen_sha256, output):
    plan = validate_frozen(source_root, frozen, frozen_sha256)
    sources = load_sources(source_root)
    requests = []
    for case, replay in sources:
        for epoch in ('prior', 'following'):
            requests.append({'RAW': getattr(case.prepared, epoch + '_bounded'),
                             'SEM': project(replay, epoch)})
    journal = output.with_name(output.name + '.journal.jsonl')
    new_external(output, source_root)
    new_external(journal, source_root)
    if output.parent != frozen.parent:
        raise Blocked('one exclusive external root required')
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
            e, arm = active['epoch_index'], active['arm']
            preceding = [c for c in calls if c['index'] == active['index']]
            if (len(calls) >= 200 or mode not in MODES
                    or len(preceding) >= 2
                    or mode != MODES[len(preceding)]):
                raise Blocked('provider order/mode/budget exceeded')
            request_sha = digest(render_llama_cpp_request(
                request, mode=mode, model=plan['model']))
            if request_sha != plan['epochs'][e]['request_sha256'][arm][mode.value]:
                raise Blocked('provider-bound request changed')
            call = {**active, 'call': len(calls) + 1, 'mode': mode.value,
                    'request_sha256': request_sha}
            calls.append(call)
            record({**call, 'event': 'provider_start'})
            start = time.perf_counter_ns()
            try:
                result = provider(request, mode=mode)
                response = asdict(result)
                call.update(status=result.status.value, choice_id=result.choice_id,
                            response=response, response_sha256=digest(response))
                return result
            except BaseException as exc:
                call.update(error_type=type(exc).__name__, error=str(exc))
                raise
            finally:
                call['wall_ns'] = time.perf_counter_ns() - start
                record({**call, 'event': 'provider_end'})

        engine = RelayEngine(counted)
        record({'event': 'begin', 'frozen_sha256': frozen_sha256,
                'schedule_sha256': digest(plan['schedule'])})
        try:
            for index, step in enumerate(plan['schedule']):
                active = {**step, 'index': index}
                e, arm = step['epoch_index'], step['arm']
                epoch = plan['epochs'][e]
                row = {**active, 'case_id': epoch['case_id'], 'epoch': epoch['epoch'],
                       'expected_choice': epoch['expected_choice'],
                       'request_sha256': epoch['request_sha256'][arm]['bounded']}
                first = len(calls)
                start = time.perf_counter_ns()
                record({**row, 'event': 'request_start'})
                try:
                    result = engine(requests[e][arm])
                    row.update(status=result.status.value, choice_id=result.choice_id,
                               escalated=result.escalated,
                               correct_rubric=(result.status.value == 'resolved'
                                               and result.choice_id == epoch['expected_choice']),
                               prompt_tokens=result.observed_prompt_tokens,
                               completion_tokens=result.observed_completion_tokens,
                               response_sha256=digest(asdict(result)))
                except BaseException as exc:
                    row.update(error_type=type(exc).__name__, error=str(exc))
                    raise
                finally:
                    row.update(provider_calls=len(calls) - first,
                               think_calls=sum(c['mode'] == 'think' for c in calls[first:]),
                               wall_ns=time.perf_counter_ns() - start)
                    rows.append(row)
                    record({**row, 'event': 'request_end'})
                if index % 10 == 9:
                    print('EPOCH_COMPLETE', e, epoch['case_id'], epoch['epoch'], flush=True)
        except BaseException as exc:
            terminal = {'error_type': type(exc).__name__, 'error': str(exc)}
            raise
        finally:
            result = {'classification': 'W4_SELF_WORLD_HOST_BOUND_SEMANTIC_PROJECTION_DEV_RESULT'
                      if terminal is None else 'DEV_FAIL',
                      'scope': plan['scope'], 'frozen_sha256': frozen_sha256,
                      'rows': rows, 'calls': calls, 'terminal': terminal,
                      'bounded_requests': len(rows), 'provider_calls': len(calls)}
            record({'event': 'terminal', 'error': terminal, 'provider_calls': len(calls)})
            result['journal_sha256'] = hashlib.sha256(journal.read_bytes()).hexdigest()
            report.write(canonical(result) + b'\n')
            report.flush()
            os.fsync(report.fileno())
    return result


def offline_args(argv=None):
    parser = argparse.ArgumentParser(description='Freeze source-verified DEV requests; no model calls')
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--model', required=True)
    parser.add_argument('--output', type=Path, required=True)
    return parser.parse_args(argv)


if __name__ == '__main__':
    import sys

    args = offline_args()
    if sys.version_info[:2] != (3, 12):
        raise Blocked('RSEE Python3.12 required')
    print(freeze(args.source_root, model=args.model, output=args.output))
