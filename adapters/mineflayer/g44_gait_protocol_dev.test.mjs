import test from 'node:test'
import assert from 'node:assert/strict'
import { parseCommand } from './protocol.mjs'

const original = process.env.S49_G44_INTRA_ACTION_GAIT_DEV_ONLY

function valid (index = 1) {
  const to = index === 1 ? 'JOG' : 'WALK'
  return {
    type: 'effect', effect: 'g44_gait_transition_dev',
    action_id: 'goal-demo-step-2-g44-' + index + '-' + to.toLowerCase(),
    parent_action_id: 'goal-demo-step-2', transition_index: index,
    from_mode: index === 1 ? 'RUN' : 'JOG', to_mode: to
  }
}

test('G4.4 admits only typed and gated same-original-action phases', () => {
  try {
    delete process.env.S49_G44_INTRA_ACTION_GAIT_DEV_ONLY
    assert.throws(() => parseCommand(valid()), /G4.4.*gate/)
    process.env.S49_G44_INTRA_ACTION_GAIT_DEV_ONLY = '1'
    assert.deepEqual(parseCommand(valid()), valid())
    assert.deepEqual(parseCommand(valid(2)), valid(2))
    for (const bad of [
      { parent_action_id: 'foreign' },
      { transition_index: 2 },
      { from_mode: 'WALK' },
      { action_id: 'goal-foreign-g44-1-jog' },
      { to_mode: 'RUN' },
      { extra_command: true }
    ]) assert.throws(() => parseCommand({ ...valid(), ...bad }))
  } finally {
    if (original === undefined) delete process.env.S49_G44_INTRA_ACTION_GAIT_DEV_ONLY
    else process.env.S49_G44_INTRA_ACTION_GAIT_DEV_ONLY = original
  }
})
