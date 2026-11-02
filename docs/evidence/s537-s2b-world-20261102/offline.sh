set -eu
export PYTHONPATH=src:.:tests PYTHONDONTWRITEBYTECODE=1
export S0_PINNED_M_SOURCE=/home/rinsa/work/s2a-m-owner-20261102/experiments/metabolism_s49_owner_admission.py
export S0_PINNED_WB_SOURCE=/home/rinsa/work/s2a-wb-owner-20261102/src/relay_self/wb_l2_read_port.py
export S1_PINNED_WB_SOURCE=/home/rinsa/work/s2a-wb-owner-20261102/src/relay_self/self_cognition_slice.py
P=/home/rinsa/relay-self-s60b1-venv/bin/python
$P -m pytest -q tests/test_s49_completed_decision_bridge.py tests/test_s49_owner_cognition_join.py tests/test_feature_s49_normal_runtime.py tests/test_postmain_s42_world_contrast.py tests/test_s49_owner_cognition_crosslane.py tests/test_s537_s1_live_wb_m_dev.py tests/test_s537_s2a_source_bound_read_port.py tests/test_s537_s2b_gated_l2_shadow.py tests/test_s537_s2b_original_owner_epoch.py tests/test_s537_s2b_original_owner_audit.py
$P -m ruff check adapters/mineflayer/s49_normal_session_real_ci.py adapters/mineflayer/s537* tools/s537* tests/test_s537* tests/test_s49*
$P -m compileall -q adapters/mineflayer/s49_normal_session_real_ci.py adapters/mineflayer/s537_s2b_original_owner_epoch.py adapters/mineflayer/s537_s2a_l2_read_port.py tools/s537_s2b_original_owner_witness_dev.py tools/s537_s2b_original_owner_audit.py
$P tools/check_repository.py
