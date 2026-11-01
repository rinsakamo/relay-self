package io.github.rinsakamo.relaymetabolism;

/** Real JDK21 executable negative-control fixture: never launches a World. */
public final class S50PaperLocalForecastSelfTest {
    private static final String MARKER = "s49-mp5-uuid";
    private static final String WORLD = "e2d84c30-7c86-4c65-8784-720246cc9f18";
    private static final String SUBJECT = "eea169cf-a0d7-3c89-ae20-3d11ecc29d8e";
    private static final String SHA = "a".repeat(64);
    private static int checks;

    private static void check(boolean good, String title) {
        checks++;
        if (!good) throw new AssertionError(title);
    }

    private static void expectInvalid(S50PaperLocalForecast model, long tick,
                                      double x, String title) {
        boolean failed = false;
        try {
            model.observe(tick, x);
        } catch (IllegalStateException expected) {
            failed = true;
        }
        check(failed, title);
    }

    public static void main(String[] args) {
        S50PaperLocalForecast model = new S50PaperLocalForecast();
        check(!model.begin(MARKER, WORLD, SUBJECT, 100), "unarmed WAIT denied");
        check(!model.arm(MARKER, WORLD, SUBJECT, Double.NaN, SHA), "nan slope");
        check(!model.arm(MARKER, WORLD, SUBJECT, Double.POSITIVE_INFINITY, SHA), "inf slope");
        check(!model.arm(MARKER, WORLD, SUBJECT, -0.1, SHA), "negative slope");
        check(!model.arm(MARKER, WORLD, SUBJECT, 65, SHA), "unbounded slope");
        check(!model.arm(MARKER, WORLD, SUBJECT, 0.2, "not-a-sha"), "invalid ticket SHA");
        check(!model.arm("bad\nstop", WORLD, SUBJECT, 0.2, SHA), "injection marker");
        check(model.arm(MARKER, WORLD, SUBJECT, 0.20331885786720635, SHA),
              "single immutable pre-arm");
        check(!model.arm(MARKER, WORLD, SUBJECT, 0.1, SHA), "no re-arm after acceptance");
        check(!model.begin(MARKER, "foreign-world", SUBJECT, 100), "foreign World denied");
        check(!model.begin("foreign-marker", WORLD, SUBJECT, 100), "foreign marker denied");
        check(!model.begin(MARKER, WORLD, "foreign-subject", 100), "foreign subject denied");
        check(model.begin(MARKER, WORLD, SUBJECT, 100), "begin only after prearm");
        check(!model.begin(MARKER, WORLD, SUBJECT, 100), "duplicate WAIT denied");
        check(!model.arm(MARKER, WORLD, SUBJECT, 0.3, SHA), "post-WAIT rearm denied");
        expectInvalid(model, 100, 0.1, "same start tick forbidden");
        expectInvalid(model, 102, 0.1, "skipped Paper tick forbidden");
        expectInvalid(model, 101, Double.NaN, "nonfinite Paper observation");
        expectInvalid(model, 101, -1, "negative observation");
        expectInvalid(model, 101, 65, "out of bound observation");
        double[] observed = {0.040, 0.008, 0.0016, 0.0003, 0, 0, 0, 0};
        for (int i = 0; i < 8; i++) {
            S50PaperLocalForecast.Observed row = model.observe(101 + i, observed[i]);
            check(row.count() == i + 1, "8 actual callbacks only");
            check(row.tick() == 101 + i, "current tick is physical callback");
            if (i == 0) {
                check(row.previousScore().previous() == null, "no first-target score");
                check(row.previousScore().status().equals("FIRST_SAMPLE_NO_PRIOR_FORECAST"),
                      "first callback not pre-scored");
            } else {
                check(row.previousScore().previous() != null, "previous prediction exists");
                check(row.previousScore().previous().targetTick() == 101 + i,
                      "score targets only currently observed tick");
                check(row.previousScore().previous().priorTick() == 100 + i,
                      "previous input strictly earlier callback");
                check(row.previousScore().previous().predictedMeters()
                      == observed[i-1] * 0.20331885786720635, "no future leakage");
                check(Double.isFinite(row.previousScore().absoluteErrorMeters()),
                      "score is finite after actual callback");
            }
            if (i < 7) {
                check(row.nextPrediction() != null, "next prediction frozen");
                check(row.nextPrediction().priorTick() == 101 + i,
                      "forecast anchored on actual callback");
                check(row.nextPrediction().targetTick() == 102 + i,
                      "future target is +1");
                check(row.nextPrediction().predictedMeters()
                      == observed[i] * 0.20331885786720635, "heldout slope only");
                check(row.nextPrediction().ticketSha256().equals(SHA), "ticket immutable");
            } else {
                check(row.nextPrediction() == null, "eight callback bound closes");
            }
        }
        check(model.count() == 8, "exact eight physical samples");
        expectInvalid(model, 109, 0, "never accept ninth callback");
        expectInvalid(model, 108, 0, "duplicate final callback");
        check(!model.arm(MARKER, WORLD, SUBJECT, 0.4, SHA), "no after-end rearm");
        System.out.println("S50_PAPER_LOCAL_FORECAST_SELFTEST_PASS checks="
                           + checks + " new_world_runs=0");
    }
}
