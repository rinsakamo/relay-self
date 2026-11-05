package io.github.rinsakamo.worldbody;

/**
 * Offline-only, pure-Java parity implementation of the existing P1-A fatigue
 * transition (experiments/fatigue_p1.py at the pinned #626 source).
 *
 * This is NOT wired into the Paper plugin and cannot classify native ticks.
 * Every Frame must FIRST be independently source-qualified by the S/R owners.
 * It does not issue an Action, credit M energy, expose World truth to Self,
 * modify a player's speed, or authorize REST.
 */
public final class P1FatigueLaw {
    private P1FatigueLaw() {}

    public enum Activity { WAIT, MOVE, FIGHT }

    public record Rate(double standard, double multiplier, double additional) {
        public Rate {
            nonnegative(standard, "rate standard");
            nonnegative(multiplier, "rate multiplier");
            nonnegative(additional, "rate additional");
            if (!Double.isFinite(standard * multiplier + additional)) {
                throw new IllegalArgumentException("nonfinite effective rate");
            }
        }
        public double value() {
            return standard * multiplier + additional;
        }
    }

    public record Profile(
            boolean enabled, double capacity, double initial,
            Rate movePerBlock, Rate fightPerEvent, Rate waitRecoveryPerWorldTick,
            Rate impairmentPerFraction, double minimumEfficiency,
            double nominalMoveLimitBlocks, double minimumFightEfficiency) {
        public Profile {
            nonnegative(capacity, "capacity");
            if (capacity == 0.0) throw new IllegalArgumentException("empty capacity");
            nonnegative(initial, "initial");
            if (initial > capacity || (!enabled && initial != 0.0)) {
                throw new IllegalArgumentException("invalid initial fatigue");
            }
            if (movePerBlock == null || fightPerEvent == null
                    || waitRecoveryPerWorldTick == null || impairmentPerFraction == null) {
                throw new IllegalArgumentException("all P1 rates required");
            }
            nonnegative(minimumEfficiency, "minimum efficiency");
            nonnegative(nominalMoveLimitBlocks, "nominal move limit");
            nonnegative(minimumFightEfficiency, "minimum fight efficiency");
            if (minimumEfficiency <= 0.0 || minimumEfficiency > 1.0
                    || nominalMoveLimitBlocks <= 0.0 || minimumFightEfficiency > 1.0) {
                throw new IllegalArgumentException("invalid capability bounds");
            }
        }
    }

    public record State(String sessionId, String profileRef, long worldTick, double fatigue) {}
    public record Frame(String sessionId, long worldTick, Activity activity,
                        double observedBlocks, boolean blocked, int observedFightEvents) {}
    public record Capability(double efficiency, double maxMoveBlocksPerWorldTick,
                             boolean fightMechanicallyPossible) {}
    public record Transition(State before, State after, Frame frame,
                             double accumulated, double recovered,
                             Capability capacityBefore, Capability capacityAfter) {}
    public record Sensor(double gain, double bias, double quantum) {
        public Sensor {
            nonnegative(gain, "gain");
            if (!Double.isFinite(bias)) throw new IllegalArgumentException("bias");
            nonnegative(quantum, "quantum");
            if (quantum <= 0.0) throw new IllegalArgumentException("zero sensor quantum");
        }
    }

    private static void nonnegative(double value, String name) {
        if (!Double.isFinite(value) || value < 0.0) {
            throw new IllegalArgumentException(name + " must be finite nonnegative");
        }
    }

    public static State initial(Profile p, String session, String profileRef, long tick) {
        if (session == null || session.isBlank()
                || profileRef == null || profileRef.isBlank() || tick < 0) {
            throw new IllegalArgumentException("session/profile/tick required");
        }
        return new State(session, profileRef, tick, p.initial());
    }

    private static void check(Profile p, State s, String profileRef) {
        if (s == null || !s.profileRef().equals(profileRef)
                || s.sessionId() == null || s.sessionId().isBlank()
                || s.worldTick() < 0) {
            throw new IllegalArgumentException("wrong/stale state");
        }
        nonnegative(s.fatigue(), "fatigue");
        if (s.fatigue() > p.capacity() || (!p.enabled() && s.fatigue() != 0.0)) {
            throw new IllegalArgumentException("fatigue outside profile");
        }
    }

    public static Capability capability(Profile p, State s, String profileRef) {
        check(p, s, profileRef);
        double reduction = p.impairmentPerFraction().value() * s.fatigue() / p.capacity();
        double effective = p.enabled()
                ? Math.max(p.minimumEfficiency(), 1.0 - reduction) : 1.0;
        effective = Math.min(1.0, effective);
        return new Capability(effective, p.nominalMoveLimitBlocks() * effective,
                              effective >= p.minimumFightEfficiency());
    }

    public static Transition advance(Profile p, State s, String profileRef, Frame frame) {
        check(p, s, profileRef);
        if (frame == null || frame.activity() == null
                || !s.sessionId().equals(frame.sessionId())
                || frame.worldTick() != s.worldTick() + 1) {
            throw new IllegalArgumentException("foreign/nonconsecutive World tick");
        }
        nonnegative(frame.observedBlocks(), "observed blocks");
        if (frame.observedFightEvents() < 0 || frame.observedFightEvents() > 1
                || (frame.activity() != Activity.MOVE
                    && (frame.observedBlocks() != 0 || frame.blocked()))
                || (frame.activity() != Activity.FIGHT && frame.observedFightEvents() != 0)) {
            throw new IllegalArgumentException("invalid P1 activity shape");
        }
        Capability before = capability(p, s, profileRef);
        double gain = 0.0;
        double recovery = 0.0;
        if (p.enabled()) {
            switch (frame.activity()) {
                case MOVE -> gain = frame.observedBlocks() * p.movePerBlock().value();
                case FIGHT -> gain = frame.observedFightEvents() * p.fightPerEvent().value();
                case WAIT -> recovery = Math.min(s.fatigue(), p.waitRecoveryPerWorldTick().value());
            }
        }
        if (!Double.isFinite(gain)) throw new IllegalArgumentException("nonfinite debit");
        double gained = Math.min(p.capacity() - s.fatigue(), gain);
        State after = new State(s.sessionId(), s.profileRef(), frame.worldTick(),
                Math.max(0.0, Math.min(p.capacity(), s.fatigue() + gained - recovery)));
        return new Transition(s, after, frame, gained, recovery,
                              before, capability(p, after, profileRef));
    }

    public static double sensed(Profile p, State s, String profileRef, Sensor sensor) {
        check(p, s, profileRef);
        if (sensor == null) throw new IllegalArgumentException("sensor required");
        double projection = sensor.bias() + sensor.gain() * s.fatigue();
        if (!Double.isFinite(projection)) throw new IllegalArgumentException("projection");
        // P1 Python round() uses ties-to-even. Math.rint() matches that rule.
        double scaled = Math.rint(projection / sensor.quantum()) * sensor.quantum();
        if (!Double.isFinite(scaled)) throw new IllegalArgumentException("sensor overflow");
        return scaled;
    }

    private static Rate parseRate(String token) {
        String[] items = token.split(",", -1);
        if (items.length != 3) throw new IllegalArgumentException("rate triplet required");
        return new Rate(Double.parseDouble(items[0]),
                        Double.parseDouble(items[1]), Double.parseDouble(items[2]));
    }

    /**
     * Offline replay harness only, never called by the Paper server or Self.
     * Args: enabled,capacity,initial, move/fight/wait/impairment rate triplets,
     * minEfficiency,nominalLimit,minFightEfficiency,sensor gain/bias/quantum,
     * starting tick, then FRAME tokens activity,blocks,blocked,events[,tick].
     */
    public static void main(String[] args) {
        if (args.length < 15) throw new IllegalArgumentException("no replay frames");
        Profile p = new Profile(Boolean.parseBoolean(args[0]),
                Double.parseDouble(args[1]), Double.parseDouble(args[2]),
                parseRate(args[3]), parseRate(args[4]), parseRate(args[5]),
                parseRate(args[6]), Double.parseDouble(args[7]),
                Double.parseDouble(args[8]), Double.parseDouble(args[9]));
        Sensor sensor = new Sensor(Double.parseDouble(args[10]),
                                   Double.parseDouble(args[11]),
                                   Double.parseDouble(args[12]));
        String session = "offline-p1-pinned";
        String profileRef = "offline-only-exact-p1-owner";
        State state = initial(p, session, profileRef, Long.parseLong(args[13]));
        for (int i = 14; i < args.length; ++i) {
            String[] f = args[i].split(",", -1);
            if (f.length != 4 && f.length != 5) {
                throw new IllegalArgumentException("invalid replay frame");
            }
            long tick = f.length == 5 ? Long.parseLong(f[4]) : state.worldTick() + 1;
            Frame frame = new Frame(session, tick, Activity.valueOf(f[0]),
                    Double.parseDouble(f[1]), Boolean.parseBoolean(f[2]),
                    Integer.parseInt(f[3]));
            Transition step = advance(p, state, profileRef, frame);
            state = step.after();
            Capability cap = step.capacityAfter();
            System.out.println(state.worldTick() + "," + state.fatigue() + ","
                    + step.accumulated() + "," + step.recovered() + ","
                    + cap.efficiency() + "," + cap.maxMoveBlocksPerWorldTick()
                    + "," + cap.fightMechanicallyPossible() + ","
                    + sensed(p, state, profileRef, sensor));
        }
    }
}
