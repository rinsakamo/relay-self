package io.github.rinsakamo.respawn;

import java.util.UUID;

/** No Paper or World required. Run with java -ea. */
public final class RespawnCycleTest {
    private static int passed;
    private static void check(boolean value) {
        if (!value) throw new AssertionError("failed assertion " + (passed + 1));
        passed++;
    }

    public static void main(String[] args) {
        UUID w = UUID.randomUUID(), foreignW = UUID.randomUUID();
        UUID a = UUID.randomUUID(), b = UUID.randomUUID(), c = UUID.randomUUID();
        RespawnCycle state = new RespawnCycle();
        check(RespawnCycle.DELAY_TICKS == 600);
        check(!state.due(w, 1000));
        check(state.begin(w, a, 100));
        check(state.generation() == 1 && state.living().equals(a));
        check(!state.begin(w, b, 101)); // at most one live
        check(!state.died(foreignW, a, 120)); // world mismatch
        check(!state.died(w, b, 120)); // entity mismatch
        check(state.died(w, a, 120));
        check(state.dueTick() == 720);
        check(!state.died(w, a, 121)); // duplicate death
        check(!state.due(foreignW, 720));
        check(!state.due(w, 719)); // 599 tick boundary
        check(!state.reborn(w, b, 719)); // no early spawn
        check(state.due(w, 720)); // 600 tick boundary
        check(!state.reborn(w, a, 720)); // distinct UUID
        check(state.reborn(w, b, 720));
        check(!state.due(w, 721));
        check(state.generation() == 2 && state.living().equals(b));
        check(state.died(w, b, 801));
        check(!state.due(w, 1400));
        check(state.due(w, 1401));
        check(state.reborn(w, c, 1401));
        check(state.generation() == 3);
        state.clear(); // shutdown must discard queued timers
        check(state.world() == null && state.dueTick() == -1);
        check(!state.due(w, 3000));
        check(state.begin(w, a, 3001)); // fresh disposable epoch
        check(!state.died(w, a, Long.MAX_VALUE)); // overflow cannot schedule
        check(state.living().equals(a));
        try {
            state.due(w, -1);
            throw new AssertionError("negative tick should fail");
        } catch (IllegalArgumentException expected) {
            passed++;
        }
        System.out.println("RESPAWN_CYCLE_OFFLINE_PASS assertions=" + passed);
    }
}
