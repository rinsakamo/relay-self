"""T1k bounded owner lineage: never rewind STOP/Action generations.

A generation is a fresh explicit T1j permit, not a cleared STOP latch.
This DEV-only journal does not grant native actions or physical qualification.
"""
from __future__ import annotations

from adapters.mineflayer.t1j_resume_gate_dev import ResumeDevPermit, ResumeDevRejected


class T1kStopResumeLineage:
    def __init__(self, session_id: str, *, max_generations: int = 2):
        if not session_id or type(max_generations) is not int or max_generations != 2:
            raise ResumeDevRejected("T1k only supports two bounded generations")
        self.session_id = session_id
        self.completed = []
        self.open_generation = None
        self.all_action_ids = set()
        self.all_stop_ids = set()
        self.all_resume_ids = set()
        self.all_owner_instances = set()
        self.failed = False

    def begin(self, stopped_owner, generation: int) -> None:
        if (self.failed or self.open_generation is not None
                or type(generation) is not int
                or generation != len(self.completed) + 1
                or generation > 2
                or stopped_owner.session_id != self.session_id
                or not stopped_owner.requested or stopped_owner.allows_action
                or stopped_owner.ack is None or stopped_owner.failed
                or stopped_owner.stop_id in self.all_stop_ids
                or id(stopped_owner) in self.all_owner_instances
                or (self.completed and
                    stopped_owner is not self.completed[-1]["new_owner"])
                or stopped_owner.ack.stop_id != stopped_owner.stop_id):
            self.failed = True
            raise ResumeDevRejected("T1k invalid STOP generation or reused owner")
        self.open_generation = {
            "generation": generation, "stopped_owner": stopped_owner,
        }
        self.all_stop_ids.add(stopped_owner.stop_id)
        self.all_owner_instances.add(id(stopped_owner))

    def admit(self, permit: ResumeDevPermit, fresh_owner) -> None:
        slot = self.open_generation
        if (self.failed or slot is None or slot.get("permit") is not None
                or type(permit) is not ResumeDevPermit
                or permit.session_id != self.session_id
                or permit.stop_id != slot["stopped_owner"].stop_id
                or permit.resume_id in self.all_resume_ids
                or permit.next_action_id in self.all_action_ids
                or permit.next_action_id + "-clear" in self.all_action_ids
                or fresh_owner.session_id != self.session_id
                or fresh_owner.requested or not fresh_owner.allows_action
                or id(fresh_owner) in self.all_owner_instances):
            self.failed = True
            raise ResumeDevRejected("T1k replayed permit/Action or nonfresh owner")
        slot["permit"] = permit
        slot["new_owner"] = fresh_owner
        self.all_resume_ids.add(permit.resume_id)
        self.all_action_ids.update({
            permit.next_action_id, permit.next_action_id + "-clear",
        })

    def finish(self, *, expected_second_stop: bool, stop_ack=None) -> None:
        slot = self.open_generation
        if (self.failed or slot is None or "permit" not in slot
                or (slot["generation"] == 1) != expected_second_stop):
            self.failed = True
            raise ResumeDevRejected("T1k generation not authorized to finish")
        owner = slot["new_owner"]
        if expected_second_stop:
            if (stop_ack is None or owner.ack is None
                    or owner.ack is not stop_ack
                    or not owner.requested or owner.allows_action
                    or owner.ack.stop_id == slot["stopped_owner"].stop_id):
                self.failed = True
                raise ResumeDevRejected("T1k missing independent second STOP ACK")
        elif stop_ack is not None or owner.requested or not owner.allows_action:
            self.failed = True
            raise ResumeDevRejected("T1k final generation did not finish normally")
        self.completed.append(slot)
        self.open_generation = None

    def summary(self) -> dict:
        return {
            "generations": len(self.completed),
            "stopped_owner_ids_distinct": len(self.all_stop_ids) == len(self.completed),
            "resume_id_count": len(self.all_resume_ids),
            "retired_effect_id_count": len(self.all_action_ids),
            "old_owners_still_latched": all(
                item["stopped_owner"].requested
                and not item["stopped_owner"].allows_action
                for item in self.completed
            ),
            "has_open_generation": self.open_generation is not None,
            "failed": self.failed,
            "classification": "T1K_BOUNDED_TWO_GENERATION_DEV",
        }
