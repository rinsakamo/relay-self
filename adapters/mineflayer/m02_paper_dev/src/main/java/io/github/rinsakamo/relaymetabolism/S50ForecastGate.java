package io.github.rinsakamo.relaymetabolism;

import java.util.Locale;

/**
 * Pure, bounded DEV Paper main-thread tick fence. No Bukkit dependency,
 * execution authority, movement command, or learning state.
 *
 * A matching receipt establishes that Paper executed the console acceptance
 * at getFullTime() < target tick, then consumed it at the sampled target tick.
 * This is NOT proof of before-tick physics integration, player input clear,
 * network write timing, or L1 model correctness.
 */
final class S50ForecastGate {
    record Receipt(String marker, String world, String subject,
                   long priorTick, long targetTick, long acceptedWorldTick,
                   double predictedMeters, String modelTicketSha256) { }

    record Decision(boolean accepted, String reason, Receipt receipt) { }

    record Sample(String status, Receipt receipt, long sampledTick) { }

    private String marker;
    private String world;
    private String subject;
    private long startTick = -1;
    private long lastObservedTick = -1;
    private int observedRows;
    private int acceptedRows;
    private boolean active;
    private Receipt outstanding;

    void begin(String marker, String world, String subject, long startTick) {
        if (active || !token(marker) || !token(world) || !token(subject)
                || startTick < 0) {
            throw new IllegalArgumentException("invalid/duplicate bounded WAIT scope");
        }
        this.marker = marker;
        this.world = world;
        this.subject = subject;
        this.startTick = startTick;
        this.lastObservedTick = startTick;
        this.observedRows = 0;
        this.acceptedRows = 0;
        this.active = true;
        this.outstanding = null;
    }

    Decision offer(String marker, String world, String subject,
                   long currentWorldTick, long priorTick, long targetTick,
                   double predictedMeters, String modelTicketSha256) {
        if (!active) return reject("NO_WAIT_SCOPE");
        if (!this.marker.equals(marker) || !this.world.equals(world)
                || !this.subject.equals(subject)) return reject("FOREIGN_SCOPE");
        if (!digest(modelTicketSha256)) return reject("INVALID_TICKET_DIGEST");
        if (!Double.isFinite(predictedMeters) || predictedMeters < 0
                || predictedMeters > 64) return reject("INVALID_PREDICTION");
        if (observedRows < 1 || observedRows >= 8 || acceptedRows >= 7) {
            return reject("NO_PREVIOUS_CALLBACK_OR_WINDOW_COMPLETE");
        }
        if (outstanding != null) return reject("PREVIOUS_TICKET_PENDING");
        if (priorTick != lastObservedTick || priorTick != startTick + observedRows
                || priorTick == Long.MAX_VALUE || targetTick != priorTick + 1) {
            return reject("NOT_NEXT_OBSERVED_TICK");
        }
        if (currentWorldTick < priorTick) return reject("WORLD_CLOCK_REGRESSION");
        if (currentWorldTick >= targetTick) return reject("LATE_TARGET_TICK");
        Receipt receipt = new Receipt(
            marker, world, subject, priorTick, targetTick, currentWorldTick,
            predictedMeters, modelTicketSha256.toLowerCase(Locale.ROOT)
        );
        outstanding = receipt;
        acceptedRows++;
        return new Decision(true, "ACCEPTED_BEFORE_TARGET_WORLD_TICK", receipt);
    }

    Sample sample(long tick) {
        if (!active) return new Sample("NO_WAIT_SCOPE", null, tick);
        if (tick != lastObservedTick + 1 || observedRows >= 8) {
            return new Sample("NONCONTIGUOUS_OR_OVERFLOW_SAMPLE", null, tick);
        }
        lastObservedTick = tick;
        observedRows++;
        Receipt result = outstanding;
        if (result != null && result.targetTick() == tick) {
            outstanding = null;
            if (observedRows == 8) active = false;
            return new Sample("MATCHED_PAPER_ACCEPTED_PRIOR_TICK", result, tick);
        }
        if (result != null && result.targetTick() < tick) {
            outstanding = null;
            if (observedRows == 8) active = false;
            return new Sample("EXPIRED_MISSED_TARGET", result, tick);
        }
        if (observedRows == 8) active = false;
        return new Sample("NO_ACCEPTED_FORECAST", null, tick);
    }

    boolean active() {
        return active;
    }

    private static boolean token(String value) {
        return value != null && value.matches("[A-Za-z0-9_-]{1,128}");
    }

    private static boolean digest(String value) {
        return value != null && value.matches("[0-9a-fA-F]{64}");
    }

    private static Decision reject(String reason) {
        return new Decision(false, reason, null);
    }
}
