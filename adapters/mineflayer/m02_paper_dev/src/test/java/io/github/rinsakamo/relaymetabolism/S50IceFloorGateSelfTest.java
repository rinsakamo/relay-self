package io.github.rinsakamo.relaymetabolism;

/** Offline JDK21 one-shot environment modification checks. No Minecraft World. */
public final class S50IceFloorGateSelfTest {
    private static int checks;
    private static void check(boolean yes, String why) {
        checks++;
        if (!yes) throw new AssertionError(why);
    }

    public static void main(String[] args) {
        String marker = "s49-native-action-id";
        String world = "original-world-uuid";
        String subject = "original-subject-uuid";
        S50IceFloorGate gate = new S50IceFloorGate();
        check(!gate.mayArm(marker, world, subject, 200, false, true, false, false),
              "no pre-forward");
        check(!gate.mayArm(marker, world, subject, 200, true, false, false, false),
              "model must be prearmed");
        check(!gate.mayArm(marker, world, subject, 200, true, true, true, false),
              "native action already issued");
        check(!gate.mayArm(marker, world, subject, 200, true, true, false, true),
              "no simultaneous MP6 body potion");
        check(!gate.mayArm("bad\nstop", world, subject, 200, true, true, false, false),
              "reject injection");
        check(!gate.mayArm(marker, world, subject, -1, true, true, false, false),
              "invalid World time");
        check(gate.mayArm(marker, world, subject, 200, true, true, false, false),
              "single scope accepted");
        boolean incompleteFailed = false;
        try {
            gate.commit(marker, world, subject, 200, 24);
        } catch (IllegalStateException expected) {
            incompleteFailed = true;
        }
        check(incompleteFailed, "partial 5x5 cannot be committed");
        gate.commit(marker, world, subject, 200, 25);
        check(gate.receipt() != null, "receipt frozen");
        check(gate.receipt().blocksChanged() == 25, "exact 25 physical blocks");
        check(gate.receipt().mode().equals("PACKED_ICE_5X5"), "mode immutable");
        check(gate.receipt().world().equals(world), "authentic World binding");
        check(!gate.mayArm(marker, world, subject, 201, true, true, false, false),
              "duplicate prevented");
        gate.seal();
        check(!gate.mayArm(marker, world, subject, 201, true, true, false, false),
              "sealed after Action");
        gate = new S50IceFloorGate();
        gate.seal();
        check(!gate.mayArm(marker, world, subject, 200, true, true, false, false),
              "no late arming");
        System.out.println("S50_ICE_FLOOR_GATE_OFFLINE_PASS checks=" + checks
                           + " real_worlds_started=0");
    }
}
