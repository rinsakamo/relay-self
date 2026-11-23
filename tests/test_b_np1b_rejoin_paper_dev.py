"""Rejoin Paper stream checks do not qualify the composite source by themselves."""
import hashlib
from dataclasses import replace

import pytest

from relay_self.b_np1b_rejoin_paper_dev import verify_rejoin_paper
from relay_self.owned_paper_world_dev import PaperTickReceipt
from relay_self.resident_paper_presence_join_dev import ResidentPaperJoinError
from test_p0d_resident_paper_presence_join_dev import BOOT, PAPER, WORLD, A, B, _line, _proofs


def source():
    old = (f'P0D_RESIDENT_READY boot={BOOT} source=PAPER_MAIN_THREAD version=1\n'
           + _line('JOIN', 1, A, 'RelayA') + '\n'
           + _line('PRESENT', 2, A, 'RelayA') + '\n'
           + _line('JOIN', 3, B, 'RelayB') + '\n'
           + _line('PRESENT', 4, B, 'RelayB') + '\n').encode()
    tail = ('\n'.join([_line('QUIT', 5, A, 'RelayA'),
                       _line('PRESENT', 6, B, 'RelayB'),
                       _line('JOIN', 7, A, 'RelayA'),
                       _line('PRESENT', 8, A, 'RelayA'),
                       f'P0D_TICK_ACK nonce=abc boot={BOOT} session={PAPER} '
                       f'world={WORLD} tick=9 source=PAPER_MAIN_THREAD']) + '\n').encode()
    world, logout, login = _proofs()
    tick = PaperTickReceipt(PAPER, 9, f'paper-main-thread:p0d:{BOOT}:abc:sha256:' + 'a' * 64)
    return dict(log=old + tail, world=world, tick=tick, paper_boot_id=BOOT,
                presence_boot_id=BOOT, a_name='RelayA', b_name='RelayB', a_actor=A,
                b_actor=B, a_logout=logout, a_relogin=login, original_b_native='native-B',
                surviving_b_native='native-B', historical_log_sha256=hashlib.sha256(old).hexdigest(),
                historical_tick=4)


def test_stationary_b_and_post_rejoin_present():
    evidence = verify_rejoin_paper(**source())
    assert evidence.a_quit_line < evidence.b_present_line < evidence.a_join_line < evidence.a_present_line


@pytest.mark.parametrize('fault', ['quit', 'double_quit', 'double_join', 'present', 'b_quit',
                                   'actor', 'boot', 'session', 'nonce', 'ack', 'late_event'])
def test_rejoin_paper_rejects_bad_streams(fault):
    data = source()
    log = data['log']
    if fault == 'quit':
        log = log.replace((_line('QUIT', 5, A, 'RelayA') + '\n').encode(), b'')
    elif fault == 'double_quit':
        log = log.replace(_line('QUIT', 5, A, 'RelayA').encode(),
                          (_line('QUIT', 5, A, 'RelayA') + '\n' + _line('QUIT', 5, A, 'RelayA')).encode())
    elif fault == 'double_join':
        log = log.replace(_line('JOIN', 7, A, 'RelayA').encode(),
                          (_line('JOIN', 7, A, 'RelayA') + '\n' + _line('JOIN', 7, A, 'RelayA')).encode())
    elif fault == 'present':
        log = log.replace((_line('PRESENT', 8, A, 'RelayA') + '\n').encode(), b'')
    elif fault == 'b_quit':
        log = log.replace(_line('PRESENT', 6, B, 'RelayB').encode(), _line('QUIT', 6, B, 'RelayB').encode())
    elif fault == 'actor':
        log = log.replace(_line('JOIN', 7, A, 'RelayA').encode(), _line('JOIN', 7, B, 'RelayA').encode())
    elif fault == 'boot':
        data['paper_boot_id'] = 'foreign'
    elif fault == 'session':
        data['tick'] = replace(data['tick'], server_session_id='foreign')
    elif fault == 'nonce':
        data['tick'] = replace(data['tick'], source_ref=data['tick'].source_ref.replace(':abc:', ':xyz:'))
    elif fault == 'ack':
        log = log.replace(b'P0D_TICK_ACK', b'NO_ACK')
    else:
        log += (_line('PRESENT', 9, B, 'RelayB') + '\n').encode()
    data['log'] = log
    with pytest.raises(ResidentPaperJoinError):
        verify_rejoin_paper(**data)
