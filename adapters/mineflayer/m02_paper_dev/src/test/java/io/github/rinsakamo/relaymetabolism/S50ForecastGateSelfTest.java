package io.github.rinsakamo.relaymetabolism;

/** Standalone JDK21 offline negative-control test, no Paper or World launch. */
public final class S50ForecastGateSelfTest {
    private static int checks;

    private static void check(boolean condition, String name) {
        checks++;
        if (!condition) throw new AssertionError(name);
    }

    private static final String MARKER = "s49-native-move-20-abc123";
    private static final String WORLD = "82356070-9e3e-431a-bf1d-7af589b6c958";
    private static final String SUBJECT = "dcae346d-e66f-331a-b459-a5a5370e9738";
    private static final String DIGEST = "a".repeat(64);

    private static S50ForecastGate newGate() {
        S50ForecastGate gate = new S50ForecastGate();
        gate.begin(MARKER, WORLD, SUBJECT, 253);
        return gate;
    }

    public static void main(String[] args) {
        S50ForecastGate gate = newGate();
        check(!gate.offer(MARKER, WORLD, SUBJECT, 253, 253, 254, 0.002, DIGEST).accepted(),
            "first Paper sample required");
        check(gate.sample(254).status().equals("NO_ACCEPTED_FORECAST"), "first sample");
        for (int target = 255; target <= 261; target++) {
            long prior = target - 1;
            S50ForecastGate.Decision d = gate.offer(
                MARKER, WORLD, SUBJECT, prior, prior, target,
                target / 10000.0, DIGEST
            );
            check(d.accepted(), "one tick ahead accepted");
            check(d.receipt().acceptedWorldTick() < d.receipt().targetTick(),
                "Paper acceptance precedes target World fullTime");
            check(!gate.offer(MARKER, WORLD, SUBJECT, prior, prior, target,
                    0.001, DIGEST).accepted(), "duplicate acceptance blocked");
            S50ForecastGate.Sample sample = gate.sample(target);
            check(sample.status().equals("MATCHED_PAPER_ACCEPTED_PRIOR_TICK"),
                "receipt matched only on target callback");
            check(sample.receipt().predictedMeters() == target / 10000.0,
                "forecast value immutable");
        }
        check(!gate.active(), "bounded window closes");
        check(!gate.offer(MARKER, WORLD, SUBJECT, 261, 261, 262, 0.003, DIGEST).accepted(),
            "cannot forecast beyond 8 callbacks");
        check(!gate.sample(262).status().equals("MATCHED_PAPER_ACCEPTED_PRIOR_TICK"),
            "no replay after window closes");

        gate = newGate();
        gate.sample(254);
        check(!gate.offer("wrong", WORLD, SUBJECT, 254, 254, 255, 0.01, DIGEST).accepted(),
            "marker must match");
        check(!gate.offer(MARKER, "foreign", SUBJECT, 254, 254, 255, 0.01, DIGEST).accepted(),
            "world must match");
        check(!gate.offer(MARKER, WORLD, "foreign", 254, 254, 255, 0.01, DIGEST).accepted(),
            "subject must match");
        check(!gate.offer(MARKER, WORLD, SUBJECT, 254, 254, 255, 0.01, "x").accepted(),
            "digest required");
        check(!gate.offer(MARKER, WORLD, SUBJECT, 254, 254, 255, Double.NaN, DIGEST).accepted(),
            "NaN rejected");
        check(!gate.offer(MARKER, WORLD, SUBJECT, 254, 254, 255,
            Double.POSITIVE_INFINITY, DIGEST).accepted(), "Inf rejected");
        check(!gate.offer(MARKER, WORLD, SUBJECT, 254, 254, 255, -1, DIGEST).accepted(),
            "negative rejected");
        check(!gate.offer(MARKER, WORLD, SUBJECT, 254, 254, 255, 65, DIGEST).accepted(),
            "unbounded rejected");
        check(!gate.offer(MARKER, WORLD, SUBJECT, 255, 254, 255, 0.01, DIGEST).accepted(),
            "late same-tick callback already physically reached is rejected");
        check(!gate.offer(MARKER, WORLD, SUBJECT, 253, 254, 255, 0.01, DIGEST).accepted(),
            "clock regression rejected");
        check(!gate.offer(MARKER, WORLD, SUBJECT, 254, 253, 254, 0.01, DIGEST).accepted(),
            "wrong prior rejected");
        check(!gate.offer(MARKER, WORLD, SUBJECT, 254, 254, 257, 0.01, DIGEST).accepted(),
            "skip tick rejected");
        check(gate.sample(255).status().equals("NO_ACCEPTED_FORECAST"),
            "missing forecast not retrofilled");
        check(!gate.offer(MARKER, WORLD, SUBJECT, 256, 255, 256, 0.01, DIGEST).accepted(),
            "late subsequent callback rejected");
        check(!gate.sample(257).status().equals("MATCHED_PAPER_ACCEPTED_PRIOR_TICK"),
            "no fabricated receipt when samples skip");
        check(!gate.offer(MARKER, WORLD, SUBJECT, 257, 255, 256, 0.01, DIGEST).accepted(),
            "gap cannot be repaired after time advances");

        gate = newGate();
        gate.sample(254);
        check(gate.offer(MARKER, WORLD, SUBJECT, 254, 254, 255, 0.01, DIGEST).accepted(),
            "valid setup");
        check(gate.sample(255).receipt() != null, "receipt only once");
        check(gate.sample(255).receipt() == null, "same target replay blocked");

        boolean badBegin = false;
        try {
            newGate().begin(MARKER, WORLD, SUBJECT, 253);
        } catch (IllegalArgumentException expected) {
            badBegin = true;
        }
        check(badBegin, "cannot overwrite open marker/world scope");
        System.out.println("S50_FORECAST_TICK_GATE_OFFLINE_PASS checks=" + checks
            + " minecraft_world_runs=0");
    }
}
