package io.github.rinsakamo.respawn;

/** World-owned, bounded observation horizon. No generation count or Action policy. */
public final class TickObservationHorizon {
    private final int ticks;
    private final int sampleInterval;
    private long startTick = -1L;
    private long endTick = -1L;
    private boolean complete;

    public TickObservationHorizon(int ticks, int sampleInterval) {
        if (ticks != 10000 || sampleInterval < 20 || sampleInterval > 1000
                || ticks % sampleInterval != 0) {
            throw new IllegalArgumentException("DEV tick horizon must be 10000, sampling 20..1000");
        }
        this.ticks = ticks;
        this.sampleInterval = sampleInterval;
    }

    public void begin(long currentTick) {
        if (startTick >= 0 || currentTick < 0 || currentTick > Long.MAX_VALUE - ticks) {
            throw new IllegalStateException("horizon must start once on valid Paper tick");
        }
        startTick = currentTick;
        endTick = currentTick + ticks;
    }

    public boolean reached(long currentTick) {
        requireStarted(currentTick);
        return currentTick >= endTick;
    }

    public boolean sample(long currentTick) {
        requireStarted(currentTick);
        long elapsed = currentTick - startTick;
        return !complete && elapsed > 0 && elapsed < ticks
                && elapsed % sampleInterval == 0;
    }

    public void finish(long currentTick) {
        if (!reached(currentTick) || complete) {
            throw new IllegalStateException("cannot stop before 10000 ticks or twice");
        }
        complete = true;
    }

    public long startTick() { return startTick; }
    public long endTick() { return endTick; }
    public long elapsed(long tick) {
        requireStarted(tick);
        return tick - startTick;
    }

    private void requireStarted(long tick) {
        if (startTick < 0 || tick < startTick) {
            throw new IllegalStateException("invalid observation tick before starting");
        }
    }
}
