package io.github.rinsakamo.respawn;

/** Pure 10000-tick World-owned horizon; no Paper process needed. Run with java -ea. */
public final class TickObservationHorizonTest {
    private static int checked;
    private static void ok(boolean x) {
        if (!x) throw new AssertionError("assertion " + checked);
        checked++;
    }

    public static void main(String[] args) {
        TickObservationHorizon h = new TickObservationHorizon(10000, 200);
        try {
            h.sample(100);
            throw new AssertionError("sample before begin");
        } catch (IllegalStateException expected) { checked++; }
        h.begin(1234);
        ok(h.startTick() == 1234 && h.endTick() == 11234);
        ok(!h.reached(11233) && h.reached(11234) && h.reached(11235));
        ok(!h.sample(1234) && !h.sample(1433) && h.sample(1434));
        ok(h.sample(11234 - 200) && !h.sample(11234));
        ok(h.elapsed(11234) == 10000);
        try {
            h.finish(11233);
            throw new AssertionError("cannot finish early");
        } catch (IllegalStateException expected) { checked++; }
        h.finish(11234);
        ok(!h.sample(11234));
        try {
            h.finish(11234);
            throw new AssertionError("cannot double finish");
        } catch (IllegalStateException expected) { checked++; }
        for (int bad : new int[]{0, 600, 9999, 10001}) {
            try {
                new TickObservationHorizon(bad, 200);
                throw new AssertionError("horizon must be exact 10000");
            } catch (IllegalArgumentException expected) { checked++; }
        }
        try {
            new TickObservationHorizon(10000, 333);
            throw new AssertionError("invalid sample interval");
        } catch (IllegalArgumentException expected) { checked++; }
        System.out.println("TICK_OBSERVATION_HORIZON_PASS assertions=" + checked);
    }
}
