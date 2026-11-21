"""CPU-only association tests; the synthetic endpoint is not Gemma evidence."""
import asyncio
from dataclasses import replace

import pytest

from relay_self.bd1b_coverage_adoption_turn_dev import CHOICES
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    BoundedChoice,
    BoundedChoiceRequest,
    CognitionDatum,
    CognitionMode,
    OpenCognitionRequest,
    ProviderDecision,
    ProviderExpression,
)
from relay_self.resident_llama_inference_lane_dev import ResidentGpuLaneError
from test_p0d_resident_llama_slot_owner_dev import (
    _attach,
    _SyntheticLlamaServer,
)
from test_p0d_resident_physical_issuer_dev import ResidentFixture


def request(ref):
    return BoundedChoiceRequest(
        ref, 'Choose adoption.', None, 'inquiry', CHOICES,
        (CognitionDatum.from_value('source', {'revision': 1}, Provenance('test', 'r1')),),
        identity_context=CognitionDatum.from_value(
            'identity_specification', {'self_id': ref}, Provenance('identity', 'i1')
        ), think_allowed=False, soft_wall_time_budget_s=2.0,
    )


def test_actual_lane_submit_binding_and_hostile_readbacks(tmp_path):
    fake = _SyntheticLlamaServer()
    endpoint = fake.start()
    fixture = ResidentFixture(tmp_path, 2, cognitive_work=True)
    lane = _attach(fixture, endpoint)

    async def scenario():
        for sid in fixture.names:
            await fixture.bridge.login(sid)
        retained = {sid: fixture.owners[sid].retained for sid in fixture.names}
        files = {p: p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
        a, b = fixture.names
        ra, rb = request('request-a'), request('request-b')
        ta = lane.submit(a, work_ref='work-a', request=ra, mode=CognitionMode.BOUNDED)
        tb = lane.submit(b, work_ref='work-b', request=rb, mode=CognitionMode.BOUNDED)
        await lane.await_result(ta)
        await lane.await_result(tb)
        assert lane._jobs[(a, 'work-a')].request is ra
        assert isinstance(lane.verify_submitted_bounded_request(ta, ra), ProviderDecision)
        assert isinstance(lane.verify_submitted_bounded_request(tb, rb), ProviderDecision)
        for altered in (
            replace(ra, choices=(BoundedChoice('1', 'changed'), *ra.choices[1:])),
            replace(ra, context=(CognitionDatum.from_value('source', 2, Provenance('test', 'r1')),)),
            replace(ra, identity_context=rb.identity_context),
            replace(ra, instruction='changed'), replace(ra, focus='changed'),
            replace(ra, intent_id='changed'), replace(ra, think_allowed=True),
            replace(ra, soft_wall_time_budget_s=3.0),
            replace(ra, context=(replace(ra.context[0], provenance=Provenance('other', 'r1')),)),
            replace(ra, choices=tuple(reversed(ra.choices))),
        ):
            with pytest.raises(ResidentGpuLaneError):
                lane.verify_submitted_bounded_request(ta, altered)
        for forged in (
            replace(ta, work_ref='work-b'), replace(ta, self_id=b),
            replace(ta, backend_ref='other'), replace(ta, self_epoch=ta.self_epoch + 1),
            replace(ta, native_session_id='other'), replace(ta, world_epoch=ta.world_epoch + 1),
            replace(ta, work_ref='unregistered'),
        ):
            with pytest.raises(ResidentGpuLaneError):
                lane.verify_submitted_bounded_request(forged, ra)
        with pytest.raises(ResidentGpuLaneError):
            lane.verify_submitted_bounded_request(tb, ra)  # another job's result
        job = lane._jobs[(a, 'work-a')]
        job.request = replace(ra, instruction='tampered')
        with pytest.raises(ResidentGpuLaneError):
            lane.verify_submitted_bounded_request(ta, ra)
        job.request = ra
        object.__setattr__(ra, 'instruction', 'mutated in place')
        with pytest.raises(ResidentGpuLaneError):
            lane.verify_submitted_bounded_request(ta, ra)
        object.__setattr__(ra, 'instruction', 'Choose adoption.')
        job.request_sha256 = '0' * 64
        with pytest.raises(ResidentGpuLaneError):
            lane.verify_submitted_bounded_request(ta, ra)
        # Restore solely to exercise independent terminal and lane guards.
        from relay_self.resident_llama_inference_lane_dev import _request_sha256
        job.request_sha256 = _request_sha256(ra, ta.mode)
        job.terminal_slot_idle = False
        with pytest.raises(ResidentGpuLaneError):
            lane.verify_submitted_bounded_request(ta, ra)
        job.terminal_slot_idle = True
        lane._uncertain = True
        with pytest.raises(ResidentGpuLaneError):
            lane.verify_submitted_bounded_request(ta, ra)
        lane._uncertain = False
        lane.fence_self(a)
        with pytest.raises(ResidentGpuLaneError):
            lane.verify_submitted_bounded_request(ta, ra)
        op = OpenCognitionRequest('open', 'Observe.', None, None, ())
        ot = lane.submit(b, work_ref='open', request=op, mode=CognitionMode.OPEN)
        assert isinstance(await lane.await_result(ot), ProviderExpression)
        with pytest.raises(ResidentGpuLaneError):
            lane.verify_submitted_bounded_request(ot, rb)
        assert {sid: fixture.owners[sid].retained for sid in fixture.names} == retained
        assert {p: p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()} == files

    try:
        asyncio.run(scenario())
    finally:
        lane._pool.shutdown(wait=True)
        fixture.stop_paper()
        fake.stop()


def test_unfinished_real_lane_job_is_rejected(tmp_path):
    fake = _SyntheticLlamaServer()
    fake.release.clear()
    endpoint = fake.start()
    fixture = ResidentFixture(tmp_path, 2, cognitive_work=True)
    lane = _attach(fixture, endpoint)

    async def scenario():
        await fixture.bridge.login(fixture.names[0])
        req = request('slow')
        ticket = lane.submit(fixture.names[0], work_ref='slow', request=req,
                             mode=CognitionMode.BOUNDED)
        assert await asyncio.to_thread(fake.entered.wait, 3)
        with pytest.raises(ResidentGpuLaneError):
            lane.verify_submitted_bounded_request(ticket, req)
        fake.release.set()
        await lane.await_result(ticket)
        assert isinstance(lane.verify_submitted_bounded_request(ticket, req), ProviderDecision)

    try:
        asyncio.run(scenario())
    finally:
        fake.release.set()
        lane._pool.shutdown(wait=True)
        fixture.stop_paper()
        fake.stop()
