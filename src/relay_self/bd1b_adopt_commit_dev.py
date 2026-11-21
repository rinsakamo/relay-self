"""Single-use, source-qualified original-owner Question commit (DEV)."""
import json

from relay_self.bd1b_issuer_readback_dev import read_issuer_result
from relay_self.bd1b_post_gpu_source_dev import verify_post_gpu_source
from relay_self.bd1b_question_store_dev import QuestionStoreHold, _store_current_inquiry
from relay_self.provenance import Provenance


def commit_issuer_adoption(*, bridge, lane, boot, world, links, turn, ticket):
    """Consume the actual registered ADOPT job, never a caller-supplied readback."""
    resident = bridge.cognitive_work
    with resident.lock:
        result = read_issuer_result(bridge=bridge, lane=lane, boot=boot, world=world,
                                    links=links, turn=turn, ticket=ticket)
        if result.selection != "ADOPT":
            return result.selection
        with lane._lock:
            job = lane._require_current_job(ticket)
            if job.ticket is not ticket or job.question_adoption_state != "unused":
                raise QuestionStoreHold("job already consumed or uncertain")
            binding = (ticket, turn.work_ref, result.verified_submitted_request_sha256,
                       turn.candidate_set_sha256, turn.owner_scope)
            job.question_adoption_binding = binding
            job.question_adoption_state = "committing"
            try:
                continuity = turn.owner.retained.exploration_continuity
                if continuity is not None and any(
                    q.question_ref == turn.inquiry.question_ref for q in continuity.questions
                ):
                    raise QuestionStoreHold("question already exists")
                origin = Provenance("issuer-adopt", json.dumps({
                    "work_ref": ticket.work_ref, "request_id": ticket.request_id,
                    "choice_id": result.provider_choice_id,
                }, sort_keys=True, separators=(",", ":")))

                def revalidate():
                    verify_post_gpu_source(bridge=bridge, lane=lane, boot=boot,
                                           world=world, links=links, turn=turn)
                    if (lane._require_current_job(ticket) is not job
                            or job.ticket is not ticket
                            or job.question_adoption_binding != binding):
                        raise QuestionStoreHold("job binding changed")
                    decision = lane.verify_submitted_bounded_request(ticket, turn.request)
                    if (decision.status != result.provider_status
                            or decision.choice_id != result.provider_choice_id
                            or decision.reason != result.provider_reason
                            or decision.call_facts != result.call_facts):
                        raise QuestionStoreHold("job result changed")

                _store_current_inquiry(resident, owner=turn.owner, self_id=turn.self_id,
                                       inquiry=turn.inquiry,
                                       expected_revision=turn.continuity_revision,
                                       origin=origin, revalidate=revalidate)
                job.question_adoption_state = "committed"
                return result.selection
            except BaseException:
                job.question_adoption_state = "failed"
                raise
