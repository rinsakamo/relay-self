package io.github.rinsakamo.relaymetabolism;

/** Single-shot experimenter World-floor intervention gate. No Bukkit dependency.
 * No source of authority for Self actions, no learning or future physics claims.
 */
final class S50IceFloorGate {
    record Scope(String marker, String world, String subject, long preActionTick,
                 String mode, int blocksChanged) {}
    private Scope receipt;
    private boolean sealed;

    boolean mayArm(String marker, String world, String subject, long tick,
                   boolean preForward, boolean modelArmed,
                   boolean nativeMoveIssued, boolean otherChallengeEnabled) {
        return receipt == null && !sealed && tick >= 0
            && token(marker) && token(world) && token(subject)
            && preForward && modelArmed && !nativeMoveIssued
            && !otherChallengeEnabled;
    }

    void commit(String marker, String world, String subject, long tick, int blocksChanged) {
        if (receipt != null || sealed || blocksChanged != 25) {
            throw new IllegalStateException("MP7 cannot admit incomplete/duplicate floor");
        }
        receipt = new Scope(marker, world, subject, tick, "PACKED_ICE_5X5", blocksChanged);
        sealed = true;
    }

    Scope receipt() {
        return receipt;
    }

    void seal() {
        sealed = true;
    }

    private static boolean token(String v) {
        return v != null && v.matches("[A-Za-z0-9_-]{1,128}");
    }
}
