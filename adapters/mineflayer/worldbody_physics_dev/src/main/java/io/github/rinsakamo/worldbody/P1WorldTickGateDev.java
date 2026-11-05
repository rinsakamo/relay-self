package io.github.rinsakamo.worldbody;

/**
 * The immutable P1 source law's DEV-only Paper-tick adapter.
 *
 * This is NOT an independent S/R SourceBoundTick attestation. A Paper input
 * snapshot, a callback, or an operator action marker alone is not such proof.
 * The gate can produce an internally consistent bounded physical DEV trace;
 * only separately owned R authority may upgrade source authenticity.
 *
 * Zero displacement while an original MOVE is open MUST remain MOVE/blocked.
 * Absent source, mixed combat/movement or nonconsecutive clocks STOP this
 * physical DEV session instead of silently granting WAIT recovery.
 */
public final class P1WorldTickGateDev {
    public static final String ORIGINAL_P1_HEAD =
            "0ab76b4e46efd914877e543a65de58b6cfc71326";
    // Exact experiments/fatigue_p1.py FatigueProfile(enabled=True).sha256.
    public static final String ORIGINAL_ENABLED_PROFILE_SHA =
            "d23f1f595095adb1da0b3ce74a72803b85b68359dc94d2ee8b03fcd2078f68b0";

    private static final P1FatigueLaw.Profile P1_STANDARD = new P1FatigueLaw.Profile(
            true, 1.0, 0.0,
            new P1FatigueLaw.Rate(0.04, 1.0, 0.0),
            new P1FatigueLaw.Rate(0.20, 1.0, 0.0),
            new P1FatigueLaw.Rate(0.10, 1.0, 0.0),
            new P1FatigueLaw.Rate(0.70, 1.0, 0.0),
            0.20, 1.0, 0.50
    );

    /** Tick data must have come from the *same* Paper player and original
     * S49 owner marker. A Frame cannot be constructed from a still probe.
     *
     * fullBoundaryObserved is a DEV-local input observation declaration,
     * not source authentication and never a cryptographic qualifier.
     */
    public record NativeTick(
            String sessionId, long paperTick, boolean fullBoundaryObserved,
            boolean ownerMoveOpen, boolean inputWasActive,
            boolean currentInputActive, boolean otherActivity,
            boolean stationaryAtBothEdges, double acceptedMoveBlocks,
            int fightEvents) {}

    public record DevResult(
            P1FatigueLaw.Activity activity, boolean blockedMove,
            P1FatigueLaw.Transition transition,
            boolean independentlyAttestedFullTickWait,
            boolean independentlyQualifiedSource) {}

    private final String sessionId;
    private P1FatigueLaw.State state;

    public P1WorldTickGateDev(String session, long initialPaperTick) {
        this.sessionId = session;
        this.state = P1FatigueLaw.initial(
                P1_STANDARD, session, ORIGINAL_ENABLED_PROFILE_SHA, initialPaperTick
        );
    }

    public static P1FatigueLaw.Profile standard() {
        return P1_STANDARD;
    }

    public P1FatigueLaw.State state() {
        return state;
    }

    public P1FatigueLaw.Capability prospective() {
        return P1FatigueLaw.capability(P1_STANDARD, state, ORIGINAL_ENABLED_PROFILE_SHA);
    }

    public DevResult accept(NativeTick observation) {
        if (observation == null
                || !sessionId.equals(observation.sessionId())
                || observation.paperTick() != state.worldTick() + 1
                || !observation.fullBoundaryObserved()
                || !Double.isFinite(observation.acceptedMoveBlocks())
                || observation.acceptedMoveBlocks() < 0
                || observation.acceptedMoveBlocks() > 1.0
                || observation.fightEvents() < 0
                || observation.fightEvents() > 1) {
            throw new IllegalArgumentException("P1_DEV_SOURCE_GAP_OR_WRONG_WORLD_TICK");
        }

        // Do not invent activity when observed combat and motion mix, or
        // when other input/interaction/teleport/damage events contaminate a
        // supposedly idle source tick.
        boolean motive = observation.ownerMoveOpen()
                || observation.inputWasActive() || observation.currentInputActive()
                || observation.acceptedMoveBlocks() > 0.0;
        P1FatigueLaw.Activity activity;
        if (observation.fightEvents() == 1) {
            if (motive || observation.otherActivity()) {
                throw new IllegalArgumentException("P1_DEV_MIXED_FIGHT_MOTION_UNKNOWN");
            }
            activity = P1FatigueLaw.Activity.FIGHT;
        } else if (motive) {
            // A blocked original MOVE, or client input with no displacement,
            // still incurs NO WAIT recovery; displacement billing remains zero.
            if (observation.otherActivity()) {
                throw new IllegalArgumentException("P1_DEV_MOVE_CONTAMINATED_UNKNOWN");
            }
            activity = P1FatigueLaw.Activity.MOVE;
        } else {
            if (observation.otherActivity() || !observation.stationaryAtBothEdges()) {
                throw new IllegalArgumentException("P1_DEV_FULL_TICK_IDLE_UNATTESTED");
            }
            activity = P1FatigueLaw.Activity.WAIT;
        }
        P1FatigueLaw.Frame frame = new P1FatigueLaw.Frame(
                sessionId, observation.paperTick(), activity,
                activity == P1FatigueLaw.Activity.MOVE
                        ? observation.acceptedMoveBlocks() : 0.0,
                activity == P1FatigueLaw.Activity.MOVE
                        && observation.acceptedMoveBlocks() == 0,
                activity == P1FatigueLaw.Activity.FIGHT ? 1 : 0
        );
        P1FatigueLaw.Transition transition = P1FatigueLaw.advance(
                P1_STANDARD, state, ORIGINAL_ENABLED_PROFILE_SHA, frame
        );
        state = transition.after();
        return new DevResult(activity, frame.blocked(), transition,
                             false, false);
    }

    /**
     * Simple repeatable DEV regression harness: keeps server API out of the
     * standard P1 law. Run against pinned original Python numerical tests.
     */
    public static void main(String[] args) {
        P1WorldTickGateDev gate = new P1WorldTickGateDev("test-world", 100);
        gate.accept(new NativeTick("test-world", 101, true, true, true, true,
                false, false, 0.5, 0));
        double afterMove = gate.state().fatigue();
        gate.accept(new NativeTick("test-world", 102, true, true, false, false,
                false, true, 0.0, 0));
        if (gate.state().fatigue() != afterMove) {
            throw new IllegalStateException("blocked MOVE created false WAIT recovery");
        }
        gate.accept(new NativeTick("test-world", 103, true, false, false, false,
                false, true, 0.0, 0));
        if (gate.state().fatigue() != 0.0) {
            throw new IllegalStateException("genuine stationary WAIT failed to recover");
        }
        try {
            gate.accept(new NativeTick("test-world", 105, true, false, false, false,
                    false, true, 0.0, 0));
            throw new IllegalStateException("missing World tick accepted");
        } catch (IllegalArgumentException expected) {
            // Correct refusal. Never auto-advance an unknown clock.
        }
        if (gate.state().worldTick() != 103) {
            throw new IllegalStateException("refused tick mutated true World state");
        }
        System.out.println("P1_DEV_ORIGINAL_LAW_MOVE_BLOCKED_WAIT_SOURCE_GATE_PASS");
    }
}
