"""Historical guard negatives only; this grants no protected-source adoption."""
import subprocess
from pathlib import Path

import pytest

import test_self_world_stage_w4_lease as historical


def test_historical_protected_inventory_still_accepts_originals(monkeypatch):
    def original(argv, **kwargs):
        return historical.PROTECTED_BLOBS[str(Path(argv[-1]).relative_to(Path(historical.__file__).resolve().parents[1]))] + '\n'
    monkeypatch.setattr(subprocess, 'check_output', original)
    historical.test_s18_and_original_default_routes_are_blob_identical()


@pytest.mark.parametrize('changed', tuple(historical.PROTECTED_BLOBS))
def test_historical_protected_inventory_rejects_each_unauthorized_blob(monkeypatch, changed):
    def substituted(argv, **kwargs):
        path = str(Path(argv[-1]).relative_to(Path(historical.__file__).resolve().parents[1]))
        return ('0' * 40 if path == changed else historical.PROTECTED_BLOBS[path]) + '\n'
    monkeypatch.setattr(subprocess, 'check_output', substituted)
    with pytest.raises(AssertionError, match=changed):
        historical.test_s18_and_original_default_routes_are_blob_identical()
