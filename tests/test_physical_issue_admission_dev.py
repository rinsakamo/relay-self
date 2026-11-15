"""#860 physical issue admission: lease lifecycle and actual DEV issuer dispatch."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from relay_self.physical_issue_admission_dev import (
    PhysicalIssueAdmission,
    PhysicalIssueFenceError,
)


def test_physical_lease_close_blocks_new_issue_and_requires_all_rebinds():
    cohort = PhysicalIssueAdmission({"A": "native-A-old", "B": "native-B-old"})
    with cohort.lease(
        self_id="A", native_session_id="native-A-old", action_id="eat-1",
    ):
        assert cohort.active_action_ids == ("eat-1",)
        with pytest.raises(PhysicalIssueFenceError, match="already in flight"):
            with cohort.lease(
                self_id="A", native_session_id="native-A-old", action_id="attack-2",
            ):
                pytest.fail("must not enter second native issue")
    fence = cohort.close()
    assert fence.physically_blocked
    assert fence.physical_inflight_action_ids == ()
    assert cohort.closed
    with pytest.raises(PhysicalIssueFenceError, match="closed"):
        with cohort.lease(
            self_id="B", native_session_id="native-B-old", action_id="attack-1",
        ):
            pytest.fail("fenced action escaped")
    cohort.rotate_native_session(
        fence_ref=fence.fence_ref, self_id="A",
        old_session_id="native-A-old", new_session_id="native-A-new",
    )
    with pytest.raises(PhysicalIssueFenceError, match="complete"):
        cohort.release(fence.fence_ref)
    with pytest.raises(PhysicalIssueFenceError, match="physical native session"):
        cohort.rotate_native_session(
            fence_ref=fence.fence_ref, self_id="B",
            old_session_id="native-B-old", new_session_id="native-A-new",
        )
    cohort.rotate_native_session(
        fence_ref=fence.fence_ref, self_id="B",
        old_session_id="native-B-old", new_session_id="native-B-new",
    )
    with pytest.raises(PhysicalIssueFenceError, match="current physical fence"):
        cohort.rotate_native_session(
            fence_ref="fence-forged", self_id="A",
            old_session_id="native-A-new", new_session_id="native-A-newer",
        )
    cohort.release(fence.fence_ref)
    assert not cohort.closed
    with pytest.raises(PhysicalIssueFenceError, match="stale"):
        with cohort.lease(
            self_id="A", native_session_id="native-A-old", action_id="old-issue",
        ):
            pytest.fail("old epoch reissued")
    with cohort.lease(
        self_id="A", native_session_id="native-A-new", action_id="fresh-issue",
    ):
        assert cohort.active_action_ids == ("fresh-issue",)


def test_close_during_real_async_issue_holds_and_never_creates_clean_cut():
    async def run():
        cohort = PhysicalIssueAdmission({"A": "native-A", "B": "native-B"})
        entered, finish = asyncio.Event(), asyncio.Event()

        async def physical_io():
            entered.set()
            await finish.wait()
            return "native-ack-observed"

        action_task = asyncio.create_task(cohort.run_guarded(
            self_id="A", native_session_id="native-A",
            action_id="attack-inflight", perform=physical_io,
        ))
        await entered.wait()
        assert cohort.active_action_ids == ("attack-inflight",)
        with pytest.raises(PhysicalIssueFenceError, match="in-flight"):
            cohort.close()
        assert cohort.closed
        # The old action is allowed to settle, but this cut stays failed/held.
        finish.set()
        assert await action_task == "native-ack-observed"
        assert cohort.active_action_ids == ()
        with pytest.raises(PhysicalIssueFenceError, match="closed"):
            await cohort.run_guarded(
                self_id="B", native_session_id="native-B",
                action_id="eat-after-close", perform=physical_io,
            )
    asyncio.run(run())


def test_cancelled_native_issue_releases_lease_but_keeps_wal_uncertainty_external():
    async def run():
        cohort = PhysicalIssueAdmission({"A": "native-A"})
        entered = asyncio.Event()

        async def wait_forever():
            entered.set()
            await asyncio.Future()

        job = asyncio.create_task(cohort.run_guarded(
            self_id="A", native_session_id="native-A",
            action_id="eat-cancelled", perform=wait_forever,
        ))
        await entered.wait()
        job.cancel()
        with pytest.raises(asyncio.CancelledError):
            await job
        assert cohort.active_action_ids == ()
        fence = cohort.close()
        assert fence.physically_blocked
        assert cohort.closed
        # This lease only tracks in-flight IO; the real WAL must still require_clear().
    asyncio.run(run())


def test_existing_eat_attack_issuers_are_invoked_inside_physical_lease(monkeypatch):
    import experiments.cognitive_physical_attack_issue_dev as attack
    import experiments.cognitive_physical_eat_issue_dev as eat

    async def run():
        cohort = PhysicalIssueAdmission({"A": "native-A"})
        session = SimpleNamespace(started=SimpleNamespace(session_id="native-A"))
        proposal = SimpleNamespace(
            binding=SimpleNamespace(
                scope=SimpleNamespace(self_id="A"), action_id="id-1",
            ),
        )
        recorded = []

        async def real_eat(_session, **kwargs):
            recorded.append(("EAT", cohort.active_action_ids, kwargs["proposal"]))
            await asyncio.sleep(0)
            return "eat-result"

        async def real_attack(_session, **kwargs):
            recorded.append(("ATTACK", cohort.active_action_ids, kwargs["proposal"]))
            await asyncio.sleep(0)
            return "attack-result"

        monkeypatch.setattr(eat, "issue_selected_eat_dev", real_eat)
        monkeypatch.setattr(attack, "issue_selected_attack_dev", real_attack)
        assert await cohort.issue_eat(session, proposal=proposal) == "eat-result"
        assert await cohort.issue_attack(session, proposal=proposal) == "attack-result"
        assert recorded == [
            ("EAT", ("id-1",), proposal),
            ("ATTACK", ("id-1",), proposal),
        ]
        assert cohort.active_action_ids == ()
        fence = cohort.close()
        with pytest.raises(PhysicalIssueFenceError, match="closed"):
            await cohort.issue_eat(session, proposal=proposal)
        assert len(recorded) == 2
        cohort.rotate_native_session(
            fence_ref=fence.fence_ref, self_id="A",
            old_session_id="native-A", new_session_id="native-B",
        )
        cohort.release(fence.fence_ref)
        with pytest.raises(PhysicalIssueFenceError, match="stale"):
            await cohort.issue_attack(session, proposal=proposal)
    asyncio.run(run())


def test_repeated_close_and_wrong_token_never_release():
    cohort = PhysicalIssueAdmission({"A": "session-A"})
    receipt = cohort.close()
    with pytest.raises(PhysicalIssueFenceError, match="already held"):
        cohort.close()
    with pytest.raises(PhysicalIssueFenceError, match="complete"):
        cohort.release("bad-token")
    cohort.rotate_native_session(
        fence_ref=receipt.fence_ref, self_id="A",
        old_session_id="session-A", new_session_id="session-B",
    )
    with pytest.raises(PhysicalIssueFenceError, match="complete"):
        cohort.release("bad-token")
    assert cohort.closed
