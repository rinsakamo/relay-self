"""DEV-only host custody reader. No model-facing projection or execution.

Only the pinned strict saved replay / original synthetic factories establish
origin. A caller-provided replay or digest alone cannot establish authenticity.
Digests bind records for comparison; they are not external attestations.
"""
import json
from dataclasses import asdict

from adapters.mineflayer.self_world_observation_only_cognition import (
    prepare_w4_offline_cognition_inputs,
)
from experiments import self_world_host_semantic_probe as probe
from experiments.self_world_metadata_ablation import digest

SCOPE = 'DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN'


def read_epoch(source_root, *, case_id, epoch, expected_source_digest):
    """Read a fixed source afresh, verify ATT/PRD, require receipt identity.

    Opaque identities remain in this host-only custody record. No model request,
    inspection decision, forecast reliance decision or reward is produced.
    """
    if epoch not in ('prior', 'following') or case_id not in probe.CASE_IDS:
        raise probe.Blocked('foreign case or epoch')
    sources = probe.load_sources(source_root)
    case, replay = next((c, r) for c, r in sources if c.case_id == case_id)
    receipt_digest = digest(asdict(replay))
    if receipt_digest != expected_source_digest:
        raise probe.Blocked('source receipt digest differs')
    prepared = prepare_w4_offline_cognition_inputs(replay)
    view = getattr(replay, epoch)
    attention = getattr(replay, epoch + '_attention')
    # Use the existing verified positive projection, never forecast-as-observed.
    request = getattr(prepared, epoch + '_bounded')
    context = {d.key: json.loads(d.value_json) for d in request.context}
    selected = context['self_world_observed']
    if any(e['origin'] != 'observed' for e in selected):
        raise probe.Blocked('prediction cannot become observation')
    source = asdict(view.observation)
    binding = {'source_receipt_sha256': receipt_digest, 'case_id': case.case_id,
               'source_class': case.source_class, 'epoch': epoch,
               'self_id': view.self_id, 'session_id': view.session_id,
               'epoch_id': view.epoch_id}
    observation = {
        'source_verification_status': 'VERIFIED_FIXED_DEV_SOURCE',
        'source_verified': True,
        'positive_selected_count': len(selected),
        'selected_positive_observations': selected,
        'observation_provenance': source['provenance'],
        'observation_source': source,
        'attention': asdict(attention),
        'coverage_truncated': view.observation.coverage_truncated,
        'world_absence_established': False,
        'world_safety_established': False,
    }
    review = replay.prediction_review if epoch == 'following' else None
    prediction = {
        'forecast_present_in_view': bool(view.forecasts),
        'prior_forecast_present': bool(replay.prior.forecasts),
        'review_status': review.status.value.upper() if review else 'NO_REVIEW',
        'predicted_value': review.predicted_value if review else None,
        'observed_value': review.observed_value if review else None,
        'compared_property': review.variable_key if review else None,
        'review': asdict(review) if review else None,
        'prior_forecasts': [asdict(f) for f in replay.prior.forecasts],
        'prior_observation': asdict(replay.prior.observation),
        'action_success': None,
        'reward': None,
    }
    observation['source_bound_digest'] = digest({'binding': binding, 'observation': observation})
    prediction['source_bound_review_digest'] = digest({'binding': binding, 'prediction': prediction})
    return {'scope': SCOPE, 'binding': binding,
            'observation': observation, 'prediction': prediction}


def read_ten_epochs(source_root, expected_source_digests):
    """Require all five externally pinned receipt digests, preserving ten rows."""
    if set(expected_source_digests) != set(probe.CASE_IDS):
        raise probe.Blocked('five fixed source pins required')
    return [read_epoch(source_root, case_id=c, epoch=e,
                       expected_source_digest=expected_source_digests[c])
            for c in probe.CASE_IDS for e in ('prior', 'following')]
