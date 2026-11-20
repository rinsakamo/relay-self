"""Stage27m disposable flat fixture; operator observation, never Self perception."""
from __future__ import annotations

import asyncio
import time
import uuid
from pathlib import Path


def flat_world_properties(base: str) -> str:
    """Request vanilla superflat with no structures or natural creature spawns."""
    if not isinstance(base, str) or 'level-type=' in base:
        raise ValueError('unambiguous base server properties required')
    return (base + 'level-type=minecraft\\:flat\n'
            + 'generator-settings={"biome":"minecraft:plains","layers":'
            + '[{"block":"minecraft:bedrock","height":1},'
            + '{"block":"minecraft:dirt","height":2},'
            + '{"block":"minecraft:grass_block","height":1}],'
            + '"structure_overrides":[]}\n'
            + 'spawn-animals=false\nspawn-monsters=false\nspawn-npcs=false\n')


def fixture_command(marker: str) -> str:
    """Check support, air and nearby entities in a coarse eastward corridor."""
    if not marker.isalnum():
        raise ValueError('marker must be alphanumeric')
    parts = ['execute as RelayA at @s']
    for x in range(-1, 7):
        for z in range(-1, 2):
            parts.append(f'if block ~{x} ~-1 ~{z} minecraft:grass_block')
            for y in range(3):
                parts.append(f'if block ~{x} ~{y} ~{z} minecraft:air')
    parts.append('positioned ~-1 ~-1 ~-1 unless entity @e[dx=7,dy=4,dz=2,name=!RelayA]')
    parts.append('run say ' + marker)
    return ' '.join(parts)


async def check_flat_fixture(paper, evidence: Path) -> None:
    """Record Paper console response; refusal precedes any physical Action."""
    marker = 'STAGE27M' + uuid.uuid4().hex
    command = fixture_command(marker)
    proc = paper._assert_owned()
    session = paper.owned_session_id
    if session is None or proc.stdin is None:
        raise RuntimeError('flat fixture owned console unavailable')
    before = paper.read_owned_log(session)
    proc.stdin.write((command + '\n').encode())
    proc.stdin.flush()
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        log = paper.read_owned_log(session)
        if marker.encode() in log[len(before):]:
            (evidence / 'stage27m-flat-check.txt').write_text(
                command + '\n' + log[len(before):].decode(errors='replace'))
            return
        await asyncio.sleep(.1)
    (evidence / 'stage27m-flat-check.txt').write_text(
        command + '\n' + paper.read_owned_log(session)[len(before):].decode(errors='replace'))
    raise RuntimeError('flat fixture check not observed; no physical Action')
