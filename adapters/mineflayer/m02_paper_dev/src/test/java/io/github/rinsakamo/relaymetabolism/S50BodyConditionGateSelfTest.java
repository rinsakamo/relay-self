package io.github.rinsakamo.relaymetabolism;

/** Pure Java21 fail-closed environment intervention contract; no Minecraft. */
public final class S50BodyConditionGateSelfTest {
    private static int checks;
    private static void check(boolean pass, String label) {
        checks++;
        if (!pass) throw new AssertionError(label);
    }
    private static S50BodyConditionGate fresh() {
        return new S50BodyConditionGate();
    }
    private static S50BodyConditionGate.Receipt arm(
            S50BodyConditionGate g, String marker, String world, String subject,
            String condition, long tick, boolean preForward, boolean model,
            boolean actionStarted, boolean preexistingEffect) {
        return g.arm(marker, world, subject, condition, tick, preForward, model,
                     actionStarted, preexistingEffect);
    }
    public static void main(String[] args) {
        String marker = "s49-mp6-uuid";
        String world = "original-paper-world-uuid";
        String subject = "owned-subject-uuid";
        check(arm(fresh(), marker, world, subject, "SLOWNESS_II", 244, false,
                  true, false, false) == null, "pre-forward required");
        check(arm(fresh(), marker, world, subject, "SLOWNESS_II", 244, true,
                  false, false, false) == null, "frozen model must be prearmed");
        check(arm(fresh(), marker, world, subject, "SLOWNESS_II", 244, true,
                  true, true, false) == null, "native action already started");
        check(arm(fresh(), marker, world, subject, "SLOWNESS_II", 244, true,
                  true, false, true) == null, "no pre-existing potion effect");
        check(arm(fresh(), marker, world, subject, "SLOWNESS_I", 244, true,
                  true, false, false) == null, "other physical mode forbidden");
        check(arm(fresh(), marker, world, subject, "SPEED_II", 244, true,
                  true, false, false) == null, "speed injection forbidden");
        check(arm(fresh(), "bad\ncommand", world, subject, "SLOWNESS_II", 244,
                  true, true, false, false) == null, "no command injection");
        check(arm(fresh(), marker, world, subject, "SLOWNESS_II", -1, true,
                  true, false, false) == null, "invalid time");
        S50BodyConditionGate gate = fresh();
        S50BodyConditionGate.Receipt result = arm(
            gate, marker, world, subject, "SLOWNESS_II", 244,
            true, true, false, false);
        check(result != null, "exactly one pre-action intervention accepted");
        check(result.beforeActionWorldTick() == 244, "source time immutable");
        check(result.world().equals(world), "World bound");
        check(result.subject().equals(subject), "subject bound");
        check(result.mode().equals("SLOWNESS_II"), "physical mode frozen");
        check(gate.receipt() == result, "receipt same immutable object");
        check(arm(gate, marker, world, subject, "SLOWNESS_II", 245,
                  true, true, false, false) == null, "duplicate denied");
        gate.close();
        check(arm(gate, marker, world, subject, "SLOWNESS_II", 245,
                  true, true, false, false) == null, "post action rearm denied");
        gate = fresh();
        gate.close();
        check(arm(gate, marker, world, subject, "SLOWNESS_II", 244,
                  true, true, false, false) == null, "closed gate never opens");
        System.out.println("S50_BODY_CONDITION_GATE_PASS checks=" + checks
                           + " physical_worlds_started=0");
    }
}
