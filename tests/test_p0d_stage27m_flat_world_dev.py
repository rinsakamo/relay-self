import pytest

from experiments.p0d_stage27m_flat_world_dev import (
    fixture_command,
    flat_world_properties,
    paper_fixture_passed,
)


def test_flat_configuration_and_existing_settings():
    result = flat_world_properties('server-ip=127.0.0.1\n')
    assert 'server-ip=127.0.0.1\n' in result
    assert 'level-type=minecraft\\:flat\n' in result
    assert 'minecraft:grass_block' in result
    assert 'spawn-animals=false' in result
    with pytest.raises(ValueError):
        flat_world_properties('level-type=normal\n')


def test_corridor_check_covers_support_clearance_and_entity():
    command = fixture_command('MARK123')
    assert 'if block ~6 ~-1 ~1 minecraft:grass_block' in command
    assert 'if block ~6 ~2 ~1 minecraft:air' in command
    assert 'unless entity @e[' in command
    assert command.endswith('run say MARK123')
    with pytest.raises(ValueError):
        fixture_command('invalid marker')


def test_paper_response_must_not_be_echoed_command():
    assert not paper_fixture_passed(b'> execute run say MARK123', 'MARK123')
    assert paper_fixture_passed(b'[INFO]: [Not Secure] [RelayA] MARK123', 'MARK123')
