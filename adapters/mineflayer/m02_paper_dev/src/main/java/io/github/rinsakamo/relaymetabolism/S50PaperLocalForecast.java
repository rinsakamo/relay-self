package io.github.rinsakamo.relaymetabolism;

/**
 * DEV-only, single-World Paper-local prequential ledger. No Bukkit dependency,
 * no physical control, no model calls, no learning/refit and no Action issuance.
 *
 * A heldout coefficient is armed before the S49 Action; the live x[t] is only
 * read in the Paper WAIT callback. The next callback consumes the immutable
 * prediction for x[t+1] before creating any later one.
 *
 * This establishes ordering between Paper sampling callbacks, NOT the exact
 * moment of physics integration within a target World tick.
 */
final class S50PaperLocalForecast {
    record Armed(String marker, String world, String subject, double slope,
                 String ticketSha256) { }

    record Prediction(long priorTick, long targetTick, double predictedMeters,
                      String ticketSha256) { }

    record Score(String status, long targetTick, double actualMeters,
                 Prediction previous, double absoluteErrorMeters) { }

    record Observed(Score previousScore, Prediction nextPrediction,
                    int count, long tick) { }

    private Armed armed;
    private boolean began;
    private long lastTick;
    private int count;
    private Prediction pending;

    boolean arm(String marker, String world, String subject,
                double slope, String ticketSha256) {
        if (armed != null || began || !token(marker) || !token(world)
                || !token(subject) || !hexSha(ticketSha256)
                || !Double.isFinite(slope) || slope < 0 || slope > 64) {
            return false;
        }
        armed = new Armed(marker, world, subject, slope, ticketSha256);
        return true;
    }

    boolean begin(String marker, String world, String subject, long startTick) {
        if (armed == null || began || startTick < 0
                || !armed.marker().equals(marker) || !armed.world().equals(world)
                || !armed.subject().equals(subject)) {
            return false;
        }
        began = true;
        lastTick = startTick;
        count = 0;
        return true;
    }

    Armed model() {
        return armed;
    }

    Observed observe(long tick, double displacementMeters) {
        if (!began || count >= 8 || lastTick == Long.MAX_VALUE
                || tick != lastTick + 1 || !Double.isFinite(displacementMeters)
                || displacementMeters < 0 || displacementMeters > 64) {
            throw new IllegalStateException("MP5 nonconsecutive or invalid real Paper sample");
        }
        Prediction previous = pending;
        Score scored;
        if (count == 0) {
            if (previous != null) throw new IllegalStateException("MP5 orphan prediction");
            scored = new Score("FIRST_SAMPLE_NO_PRIOR_FORECAST",
                               tick, displacementMeters, null, Double.NaN);
        } else {
            if (previous == null || previous.targetTick() != tick) {
                throw new IllegalStateException("MP5 missing/stale future-tick prediction");
            }
            scored = new Score("SCORED_PREVIOUS_PAPER_CALLBACK_FORECAST",
                               tick, displacementMeters, previous,
                               Math.abs(previous.predictedMeters() - displacementMeters));
        }
        lastTick = tick;
        count++;
        if (count < 8) {
            double forecast = armed.slope() * displacementMeters;
            if (!Double.isFinite(forecast) || forecast < 0 || forecast > 64) {
                throw new IllegalStateException("MP5 invalid next forecast");
            }
            pending = new Prediction(tick, tick + 1, forecast, armed.ticketSha256());
        } else {
            pending = null;
        }
        return new Observed(scored, pending, count, tick);
    }

    int count() {
        return count;
    }

    private static boolean token(String v) {
        return v != null && v.matches("[A-Za-z0-9_-]{1,128}");
    }

    private static boolean hexSha(String v) {
        return v != null && v.matches("[0-9a-f]{64}");
    }
}
