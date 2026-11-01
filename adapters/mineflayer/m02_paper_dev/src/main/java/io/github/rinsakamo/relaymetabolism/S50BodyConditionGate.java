package io.github.rinsakamo.relaymetabolism;

/**
 * One-shot, environment-owner physical condition for a fresh DEV World.
 *
 * This intentionally changes the Minecraft player's real movement physics,
 * but NEVER authorizes a Self Action, modifies S49's L0 decision, or trains.
 * Pure bounded gate; Bukkit applies the effect only after successful receipt.
 */
final class S50BodyConditionGate {
    record Receipt(String marker, String world, String subject, String mode,
                   long beforeActionWorldTick) { }

    private Receipt receipt;
    private boolean closed;

    Receipt arm(String marker, String world, String subject, String mode,
                long paperTick, boolean preForwardSeen, boolean paperModelArmed,
                boolean actionAlreadyIssued, boolean hasConflictingEffect) {
        if (receipt != null || closed || !preForwardSeen || !paperModelArmed
                || actionAlreadyIssued || hasConflictingEffect
                || paperTick < 0 || !token(marker) || !token(world)
                || !token(subject) || !"SLOWNESS_II".equals(mode)) {
            return null;
        }
        receipt = new Receipt(marker, world, subject, mode, paperTick);
        return receipt;
    }

    void close() {
        closed = true;
    }

    Receipt receipt() {
        return receipt;
    }

    private static boolean token(String v) {
        return v != null && v.matches("[A-Za-z0-9_-]{1,128}");
    }
}
