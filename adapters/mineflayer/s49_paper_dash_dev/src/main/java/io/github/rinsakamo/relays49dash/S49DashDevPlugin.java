package io.github.rinsakamo.relays49dash;

import java.util.UUID;
import org.bukkit.Bukkit;
import org.bukkit.Input;
import org.bukkit.NamespacedKey;
import org.bukkit.World;
import org.bukkit.attribute.Attribute;
import org.bukkit.attribute.AttributeInstance;
import org.bukkit.attribute.AttributeModifier;
import org.bukkit.command.Command;
import org.bukkit.command.CommandSender;
import org.bukkit.command.ConsoleCommandSender;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.player.PlayerQuitEvent;
import org.bukkit.plugin.java.JavaPlugin;
import org.bukkit.scheduler.BukkitTask;

/**
 * Isolated Paper DEV *motor modifier*, NOT S49 Action admission.
 *
 * The owning S49 runner must independently prove an issued forward MOVE
 * before requesting arm. Console text is not authenticated Action evidence.
 * While armed, retain DASH stance during lateral/back/idle movement, but
 * only ever apply the transient +speed modifier on an unambiguous forward
 * sprint input. Unknown input fails closed to vanilla speed.
 *
 * Does NOT cap other plugins' modifiers or attest server-effective input
 * timing. One-shot disposable profile, timeout, identity checks, cleanup.
 */
public final class S49DashDevPlugin extends JavaPlugin implements Listener {
    private static final long MAX_ARM_TICKS = 80L; // one 4s DEV motor window
    private boolean consumed = false;
    private boolean armed = false;
    private boolean boosted = false;
    private Player subject;
    private UUID playerId;
    private UUID worldId;
    private String actionId;
    private String sessionId;
    private long armTick;
    private long lastTick;
    private int forwardTicks;
    private int cappedTicks;
    private int motionProjectedBoostTicks;
    private double requestedPower;
    // P1 motor calculation applies to the single fatigue dimension.
    private boolean p1MotorDev;
    private double p1Fatigue;
    private double activeDashPower;
    private int p1WorldTicks;
    private boolean nativeAppliedMarked;
    private boolean nativeClearedMarked;
    private double lastX;
    private double lastZ;
    private BukkitTask task;
    private BukkitTask postReleaseTask;
    // Separate passive 2-Action timeline; no motor/P1/M0 or native issuer.
    private BukkitTask twoActionTrailTask;
    private long trailStartTick;
    private long trailLastTick;
    private int trailSamples;
    private String secondNativeActionId;
    private boolean secondAppliedMarked;
    private boolean secondClearedMarked;
    private int lastTrailNativeAckSeq = -1;
    private int secondCleanupTrailTick = -1;
    private boolean ownerFenceStartSeen = false;
    private boolean ownerFenceEndSeen = false;
    private long ownerFenceStartTick = -1L;
    private long postReleaseStartTick;
    private long postReleaseLastTick;
    private double postReleaseLastX;
    private double postReleaseLastZ;
    private int postReleaseCount;
    private AttributeModifier modifier;

    @Override
    public void onEnable() {
        getLogger().info("S49_DASH_DEV_READY enabled="
            + getConfig().getBoolean("enabled", false)
            + " authority=NONE speed_changes=OPT_IN");
        Bukkit.getPluginManager().registerEvents(this, this);
    }

    private boolean validId(String value) {
        return value != null && value.matches("[A-Za-z0-9_.:-]{1,96}");
    }

    @Override
    public boolean onCommand(CommandSender sender, Command command,
                             String label, String[] args) {
        boolean start = command.getName().equalsIgnoreCase("relays49dasharm");
        boolean stop = command.getName().equalsIgnoreCase("relays49dashoff");
        boolean mark = command.getName().equalsIgnoreCase("relays49dashmark");
        boolean trailMark = command.getName().equalsIgnoreCase("relays49dashtrailmark");
        boolean ownerFence = command.getName().equalsIgnoreCase("relays49dashownerfence");
        if (!start && !stop && !mark && !trailMark && !ownerFence) {
            return false;
        }
        if (!(sender instanceof ConsoleCommandSender)
                || !Bukkit.isPrimaryThread()
                || !getConfig().getBoolean("enabled", false)
                || args.length != (start ? 4 : (mark || trailMark || ownerFence) ? 5 : 3)
                || !validId(args[0]) || !validId(args[1])) {
            getLogger().warning("S49_DASH_DEV_DENIED console_or_input");
            return true;
        }
        UUID uuid;
        try {
            uuid = UUID.fromString(args[2]);
        } catch (IllegalArgumentException exception) {
            getLogger().warning("S49_DASH_DEV_DENIED uuid");
            return true;
        }
        if (start) {
            arm(args, uuid);
        } else if (mark) {
            markNativeEffect(args, uuid);
        } else if (trailMark) {
            markSecondNativeEffect(args, uuid);
        } else if (ownerFence) {
            markOriginalOwnerFence(args, uuid);
        } else {
            if (!armed || !uuid.equals(playerId)
                    || !args[0].equals(actionId) || !args[1].equals(sessionId)) {
                getLogger().warning("S49_DASH_DEV_DENIED foreign_release");
                return true;
            }
            disarm(getConfig().getBoolean("native-edge-dev", false)
                && (!nativeAppliedMarked || !nativeClearedMarked)
                ? "NATIVE_EFFECT_ACK_MARKER_MISSING" : "OWNER_RELEASE");
        }
        return true;
    }

    private void arm(String[] args, UUID uuid) {
        if (consumed || armed) {
            getLogger().warning("S49_DASH_DEV_DENIED one_shot");
            return;
        }
        double power;
        try {
            power = Double.parseDouble(args[3]);
        } catch (NumberFormatException exception) {
            getLogger().warning("S49_DASH_DEV_DENIED power");
            return;
        }
        if (!Double.isFinite(power) || power <= 0 || power > 1) {
            getLogger().warning("S49_DASH_DEV_DENIED power_out_of_range");
            return;
        }
        Player player = Bukkit.getPlayer(uuid);
        if (player == null || !player.isOnline() || player.isDead()
                || !uuid.equals(player.getUniqueId())
                || !player.getName().equals(
                    getConfig().getString("expected-player-name", "RelaySelf")
                ) || player.getAttribute(Attribute.MOVEMENT_SPEED) == null) {
            getLogger().warning("S49_DASH_DEV_DENIED invalid_player");
            return;
        }
        NamespacedKey key = new NamespacedKey(this, "forward_dash_only");
        AttributeInstance speed = player.getAttribute(Attribute.MOVEMENT_SPEED);
        if (speed.getModifier(key) != null) {
            getLogger().warning("S49_DASH_DEV_DENIED colliding_modifier");
            return;
        }
        consumed = true;
        armed = true;
        boosted = false;
        subject = player;
        playerId = uuid;
        worldId = player.getWorld().getUID();
        actionId = args[0];
        sessionId = args[1];
        requestedPower = power;
        p1MotorDev = getConfig().getBoolean("p1-live-dev", false);
        // Explicit DEV scenario preloads an earlier *counterfactual* model F
        // into a NEW disposable World. This is not an actual recovered Body.
        boolean pairPreload = getConfig().getBoolean("p1-model-pair-dev", false);
        double configuredF = getConfig().getDouble("p1-initial-fatigue", -1);
        if (pairPreload && !p1MotorDev) {
            disarm("P1_PAIR_REQUIRES_MODEL");
            return;
        }
        if (p1MotorDev && (
            !Double.isFinite(configuredF)
            || (pairPreload
                ? (Math.abs(configuredF - 0.6177122410202606) > 1e-9
                    && Math.abs(configuredF - 0.21616083122103735) > 1e-9)
                : Math.abs(configuredF - 0.6) > 1e-9)
        )) {
            disarm("P1_DEV_PROFILE_INVALID");
            return;
        }
        p1Fatigue = p1MotorDev ? configuredF : 0.0;
        activeDashPower = 0.0;
        p1WorldTicks = 0;
        nativeAppliedMarked = false;
        nativeClearedMarked = false;
        armTick = player.getWorld().getFullTime();
        lastTick = armTick;
        lastX = player.getLocation().getX();
        lastZ = player.getLocation().getZ();
        forwardTicks = 0;
        cappedTicks = 0;
        motionProjectedBoostTicks = 0;
        modifier = new AttributeModifier(
            key, 0.5 * requestedPower, AttributeModifier.Operation.MULTIPLY_SCALAR_1
        );
        task = Bukkit.getScheduler().runTaskTimer(this, this::sample, 1L, 1L);
        if (getConfig().getBoolean("two-action-trace-dev", false)) {
            trailStartTick = armTick;
            trailLastTick = armTick;
            trailSamples = 0;
            secondNativeActionId = null;
            secondAppliedMarked = false;
            secondClearedMarked = false;
            lastTrailNativeAckSeq = -1;
            secondCleanupTrailTick = -1;
            ownerFenceStartSeen = false;
            ownerFenceEndSeen = false;
            ownerFenceStartTick = -1L;
            twoActionTrailTask = Bukkit.getScheduler().runTaskTimer(
                this, this::sampleTwoActionTrail, 1L, 1L
            );
        }
        getLogger().info("S49_DASH_DEV_ARM action_id=" + actionId
            + " session_id=" + sessionId + " player_uuid=" + playerId
            + " world=" + worldId + " tick=" + armTick
            + " power=" + power + " authority=NONE"
            + " p1_motor_dev=" + p1MotorDev
            + " p1_initial_fatigue=" + p1Fatigue
            + " p1_model_pair_preloaded=" + pairPreload);
    }

    private void markNativeEffect(String[] args, UUID uuid) {
        if (!getConfig().getBoolean("native-edge-dev", false)
                || !armed || !safeSubject()
                || !uuid.equals(playerId)
                || !args[0].equals(actionId) || !args[1].equals(sessionId)) {
            getLogger().warning("S49_DASH_DEV_DENIED native_ack_foreign");
            return;
        }
        boolean applied = args[3].equals("APPLIED");
        boolean cleared = args[3].equals("CLEARED");
        if ((!applied && !cleared)
                || (applied && (nativeAppliedMarked || nativeClearedMarked))
                || (cleared && (!nativeAppliedMarked || nativeClearedMarked))) {
            getLogger().warning("S49_DASH_DEV_DENIED native_ack_replay_or_order");
            return;
        }
        int seq;
        try {
            seq = Integer.parseInt(args[4]);
        } catch (NumberFormatException exception) {
            getLogger().warning("S49_DASH_DEV_DENIED native_ack_seq");
            return;
        }
        if (seq < 0) {
            getLogger().warning("S49_DASH_DEV_DENIED native_ack_negative_seq");
            return;
        }
        if (applied) {
            nativeAppliedMarked = true;
        } else {
            nativeClearedMarked = true;
        }
        // The S49 owner received an existing native effect ACK BEFORE
        // this console command. Paper time records delivery of the marker,
        // never physical client-side effect timing or a clock-synced edge.
        getLogger().info("S49_DASH_DEV_EDGE action_id=" + actionId
            + " session_id=" + sessionId
            + " world=" + worldId + " player_uuid=" + playerId
            + " phase=" + (applied ? "APPLIED" : "CLEARED")
            + " native_seq=" + seq
            + " tick=" + subject.getWorld().getFullTime()
            + " marker_after_native_ack=true"
            + " synchronized_native_effect_tick=false");
    }

    private void markSecondNativeEffect(String[] args, UUID uuid) {
        if (!getConfig().getBoolean("two-action-trace-dev", false)
                || twoActionTrailTask == null || !safeSubject()
                || !uuid.equals(playerId)
                || !args[1].equals(sessionId)
                || !nativeAppliedMarked || !nativeClearedMarked
                || !args[0].matches("s49-native-move-[0-9]{1,16}")
                || args[0].equals(actionId)
                || (secondNativeActionId != null
                    && !secondNativeActionId.equals(args[0]))) {
            getLogger().warning("S49_DASH_DEV_TRAIL_DENIED wrong_actor_or_order");
            return;
        }
        boolean applied = args[3].equals("APPLIED");
        boolean cleared = args[3].equals("CLEARED");
        if ((!applied && !cleared)
                || (applied && secondAppliedMarked)
                || (cleared && (!secondAppliedMarked || secondClearedMarked))) {
            getLogger().warning("S49_DASH_DEV_TRAIL_DENIED replay_or_phase");
            return;
        }
        int seq;
        try {
            seq = Integer.parseInt(args[4]);
        } catch (NumberFormatException exception) {
            getLogger().warning("S49_DASH_DEV_TRAIL_DENIED invalid_seq");
            return;
        }
        if (seq <= lastTrailNativeAckSeq || seq < 0) {
            getLogger().warning("S49_DASH_DEV_TRAIL_DENIED ack_seq_replay");
            return;
        }
        secondNativeActionId = args[0];
        lastTrailNativeAckSeq = seq;
        if (applied) {
            secondAppliedMarked = true;
        } else {
            secondClearedMarked = true;
            secondCleanupTrailTick = (int) subject.getWorld().getFullTime();
        }
        getLogger().info("S49_DASH_DEV_TRAIL_EDGE action_id=" + secondNativeActionId
            + " session_id=" + sessionId
            + " world=" + worldId + " player_uuid=" + playerId
            + " phase=" + (applied ? "APPLIED" : "CLEARED")
            + " native_seq=" + seq
            + " tick=" + subject.getWorld().getFullTime()
            + " delivered_after_original_native_ack=true"
            + " exact_client_effect_tick_attested=false");
    }

    private void markOriginalOwnerFence(String[] args, UUID uuid) {
        // This is ONLY a Paper producer-local delivery witness. The
        // original S49 owner must await each logged acceptance before
        // issuing the next native Action; Paper issues no Action itself.
        if (!getConfig().getBoolean("causal-owner-fence-dev", false)
                || !getConfig().getBoolean("two-action-trace-dev", false)
                || twoActionTrailTask == null || !safeSubject()
                || !uuid.equals(playerId)
                || !args[0].equals(actionId) || !args[1].equals(sessionId)
                || !nativeAppliedMarked || !nativeClearedMarked
                || armed || boosted || secondAppliedMarked || secondClearedMarked) {
            getLogger().warning("S49_DASH_DEV_OWNER_FENCE_DENIED actor_or_state");
            return;
        }
        boolean begin = "START".equals(args[3]);
        boolean finish = "END".equals(args[3]);
        if ((!begin && !finish)
                || (begin && (ownerFenceStartSeen || ownerFenceEndSeen
                              || !"NONE".equals(args[4])))
                || (finish && (!ownerFenceStartSeen || ownerFenceEndSeen
                               || !args[4].matches("s49-native-move-[0-9]{1,16}")
                               || args[4].equals(actionId)))) {
            getLogger().warning("S49_DASH_DEV_OWNER_FENCE_DENIED replay_or_phase");
            return;
        }
        long tick = subject.getWorld().getFullTime();
        if (begin) {
            ownerFenceStartSeen = true;
            ownerFenceStartTick = tick;
        } else {
            if (tick <= ownerFenceStartTick + 8L) {
                getLogger().warning("S49_DASH_DEV_OWNER_FENCE_DENIED short_interval");
                return;
            }
            ownerFenceEndSeen = true;
        }
        getLogger().info("S49_DASH_DEV_OWNER_FENCE action_id=" + actionId
            + " session_id=" + sessionId + " world=" + worldId
            + " player_uuid=" + playerId
            + " phase=" + (begin ? "START" : "END")
            + " second_action_id=" + args[4] + " tick=" + tick
            + " original_owner_paper_delivery_only=true"
            + " native_effect_tick_attested=false"
            + " motor_write=false M0_POSTED=false P1_APPLIED=false"
            + " WAIT_ATTESTED=false");
    }

    private void sampleTwoActionTrail() {
        if (twoActionTrailTask == null) return;
        if (!Bukkit.isPrimaryThread() || !safeSubject()) {
            endTwoActionTrail("ACTOR_OR_WORLD_CHANGED");
            return;
        }
        long tick = subject.getWorld().getFullTime();
        if (tick == trailStartTick && trailSamples == 0) return;
        if (tick != trailLastTick + 1 || tick - trailStartTick > 1200L) {
            endTwoActionTrail("WORLD_TICK_GAP_OR_MAX");
            return;
        }
        AttributeInstance speed = subject.getAttribute(Attribute.MOVEMENT_SPEED);
        if (speed == null || (secondAppliedMarked && (
                armed || boosted || modifier == null
                || speed.getModifier(modifier.getKey()) != null))) {
            endTwoActionTrail("DASH_MODIFIER_RETAINED_IN_SECOND");
            return;
        }
        trailSamples++;
        trailLastTick = tick;
        getLogger().info("S49_DASH_DEV_TRAIL_TICK action_id=" + actionId
            + " session_id=" + sessionId
            + " world=" + worldId + " player_uuid=" + playerId
            + " tick=" + tick + " index=" + trailSamples
            + " second_applied_marker_seen=" + secondAppliedMarked
            + " second_cleared_marker_seen=" + secondClearedMarked
            + " first_dash_modifier_present="
            + (modifier != null && speed.getModifier(modifier.getKey()) != null)
            + " x=" + subject.getLocation().getX()
            + " z=" + subject.getLocation().getZ()
            + " motor_write=false M0_POSTED=false P1_APPLIED=false WAIT_ATTESTED=false");
        if (secondClearedMarked && tick >= secondCleanupTrailTick + 5) {
            endTwoActionTrail("SECOND_NATIVE_ACK_MARKER_PLUS_FIVE");
        }
    }

    private void endTwoActionTrail(String reason) {
        if (twoActionTrailTask == null) return;
        twoActionTrailTask.cancel();
        twoActionTrailTask = null;
        getLogger().info("S49_DASH_DEV_TRAIL_COMPLETE action_id=" + actionId
            + " session_id=" + sessionId + " second_action_id="
            + (secondNativeActionId == null ? "NONE" : secondNativeActionId)
            + " world=" + worldId + " player_uuid=" + playerId
            + " tick=" + trailLastTick + " samples=" + trailSamples
            + " reason=" + reason + " motor_write=false"
            + " M0_POSTED=false P1_APPLIED=false WAIT_ATTESTED=false");
    }

    private boolean safeSubject() {
        return subject != null && subject.isOnline() && !subject.isDead()
            && playerId.equals(subject.getUniqueId())
            && worldId.equals(subject.getWorld().getUID())
            && subject.getName().equals(
                getConfig().getString("expected-player-name", "RelaySelf")
            );
    }

    private void sample() {
        if (!armed) {
            return;
        }
        if (!Bukkit.isPrimaryThread() || !safeSubject()) {
            disarm("SUBJECT_OR_WORLD_CHANGED");
            return;
        }
        World world = subject.getWorld();
        long tick = world.getFullTime();
        // Paper may schedule the first callback in the same World tick
        // as arm(); that does not represent an elapsed World tick.
        if (tick == armTick && lastTick == armTick) {
            return;
        }
        if (tick <= lastTick || tick - armTick > MAX_ARM_TICKS) {
            disarm("TICK_GAP_OR_MAX_WINDOW");
            return;
        }
        double x = subject.getLocation().getX();
        double z = subject.getLocation().getZ();
        double dx = x - lastX;
        double dz = z - lastZ;
        double sampledSpeedMps = 20.0 * Math.hypot(dx, dz) / (tick - lastTick);
        lastX = x;
        lastZ = z;
        lastTick = tick;
        Input input = subject.getCurrentInput();
        // Never assume Paper input and Mineflayer physics ticks align.
        // Ambiguous/unknown, side+forward, reverse or idle => NO DASH BONUS.
        boolean forwardOnly = input != null && input.isForward()
            && !input.isBackward() && !input.isLeft() && !input.isRight()
            && !input.isSneak() && !input.isJump()
            && (input.isSprint() || subject.isSprinting());
        // Mineflayer 4.39.0 / Paper 1.21.8 may expose empty Input flags
        // while the native player is sprinting and visibly moving forward.
        // Distinguish this *motion inference* from a real Input forward edge.
        // An ambiguous or sideways/backwards vector NEVER receives a boost.
        double yaw = Math.toRadians(subject.getLocation().getYaw());
        double forwardDelta = -Math.sin(yaw) * dx + Math.cos(yaw) * dz;
        double sideDelta = Math.cos(yaw) * dx + Math.sin(yaw) * dz;
        boolean emptyPacket = input != null && !input.isForward()
            && !input.isBackward() && !input.isLeft() && !input.isRight()
            && !input.isSneak() && !input.isJump() && !input.isSprint();
        boolean motionForwardInferred = !forwardOnly && emptyPacket
            && subject.isSprinting() && tick - armTick > 1
            && tick - armTick <= MAX_ARM_TICKS
            && forwardDelta > 0.035
            && Math.abs(sideDelta) <= 0.10 * forwardDelta
            && sampledSpeedMps > 0.70;
        boolean shouldBoost = forwardOnly || motionForwardInferred;
        double p1Before = p1Fatigue;
        double previousPower = activeDashPower;
        if (p1MotorDev) {
            // Previous applied Paper modifier, not the requested gait,
            // determines the P1 load for this actual elapsed World tick.
            double k = previousPower > 0 ? 0.02 : 0.025;
            double fullLoad = 0.02 / (-Math.expm1(-0.02 * 20.0));
            double load = previousPower > 0
                ? 0.004 + (fullLoad - 0.004) * Math.pow(previousPower, 1.2)
                : 0.004;
            double decay = -Math.expm1(-k * 0.05);
            p1Fatigue = Math.min(1.0, Math.max(0.0,
                p1Fatigue * (1 - decay) + load / k * decay));
            p1WorldTicks++;
        }
        double allowedPower = p1MotorDev
            ? Math.min(requestedPower, Math.max(0.0,
                Math.min(1.0, 2.0 * (1.0 - p1Fatigue))))
            : requestedPower;
        if (allowedPower <= 0) shouldBoost = false;
        if (!setBoost(shouldBoost, allowedPower)) {
            disarm("MODIFIER_SET_FAILED");
            return;
        }
        if (shouldBoost) {
            forwardTicks++;
            if (motionForwardInferred) {
                motionProjectedBoostTicks++;
            }
        } else {
            cappedTicks++;
        }
        getLogger().info("S49_DASH_DEV_TICK action_id=" + actionId
            + " session_id=" + sessionId + " tick=" + tick
            + " index=" + (forwardTicks + cappedTicks)
            + " world=" + worldId + " player_uuid=" + playerId
            + " input_forward_only=" + forwardOnly
            + " motion_forward_inferred=" + motionForwardInferred
            + " boost_source=" + (forwardOnly ? "PACKET" :
                motionForwardInferred ? "MOTION_PROJECTION" : "NONE")
            + " modifier_applied=" + boosted
            + " dash_stance_active=true"
            + " input_edge_attested=false"
            + " input_present=" + (input != null)
            + " packet_forward=" + (input != null && input.isForward())
            + " packet_back=" + (input != null && input.isBackward())
            + " packet_left=" + (input != null && input.isLeft())
            + " packet_right=" + (input != null && input.isRight())
            + " packet_sprint=" + (input != null && input.isSprint())
            + " player_sprinting=" + subject.isSprinting()
            + " delta_x_m=" + dx + " delta_z_m=" + dz
            + " sampled_speed_mps=" + sampledSpeedMps
            + " projected_forward_delta_m=" + forwardDelta
            + " projected_side_delta_m=" + sideDelta
            + " yaw_degrees=" + subject.getLocation().getYaw()
            + " p1_motor_dev=" + p1MotorDev
            + " p1_world_ticks=" + p1WorldTicks
            + " p1_before=" + p1Before
            + " p1_after=" + p1Fatigue
            + " p1_prev_applied_power=" + previousPower
            + " p1_current_applied_power=" + activeDashPower);
    }

    private boolean setBoost(boolean shouldBoost, double allowedPower) {
        AttributeInstance speed = subject == null ? null
            : subject.getAttribute(Attribute.MOVEMENT_SPEED);
        if (speed == null || modifier == null) {
            return false;
        }
        try {
            if (p1MotorDev && shouldBoost && boosted) {
                speed.removeModifier(modifier);
                boosted = false;
            }
            if (shouldBoost && !boosted) {
                if (speed.getModifier(modifier.getKey()) != null) {
                    return false;
                }
                if (p1MotorDev) {
                    modifier = new AttributeModifier(
                        modifier.getKey(), 0.5 * allowedPower,
                        AttributeModifier.Operation.MULTIPLY_SCALAR_1
                    );
                }
                speed.addTransientModifier(modifier);
                boosted = true;
                getLogger().info("S49_DASH_SPEED_ATTRIBUTE_DEV "
                    + "action_id=" + actionId
                    + " tick=" + subject.getWorld().getFullTime()
                    + " base=" + speed.getBaseValue()
                    + " effective=" + speed.getValue()
                    + " modifier_added=true");
            } else if (!shouldBoost && boosted) {
                speed.removeModifier(modifier);
                boosted = false;
                getLogger().info("S49_DASH_SPEED_ATTRIBUTE_DEV "
                    + "action_id=" + actionId
                    + " tick=" + subject.getWorld().getFullTime()
                    + " base=" + speed.getBaseValue()
                    + " effective=" + speed.getValue()
                    + " modifier_added=false");
            }
            activeDashPower = shouldBoost ? allowedPower : 0.0;
            return true;
        } catch (RuntimeException exception) {
            getLogger().warning("S49_DASH_DEV_MODIFIER_FAILURE "
                + exception.getClass().getSimpleName());
            return false;
        }
    }

    private void disarm(String reason) {
        if (!armed) {
            return;
        }
        armed = false;
        if (task != null) {
            task.cancel();
            task = null;
        }
        if (subject != null && modifier != null) {
            AttributeInstance speed = subject.getAttribute(Attribute.MOVEMENT_SPEED);
            if (speed != null && speed.getModifier(modifier.getKey()) != null) {
                try {
                    speed.removeModifier(modifier);
                } catch (RuntimeException exception) {
                    getLogger().severe("S49_DASH_DEV_CLEANUP_UNCONFIRMED "
                        + exception.getClass().getSimpleName());
                }
            }
        }
        boosted = false;
        getLogger().info("S49_DASH_DEV_COMPLETE action_id=" + actionId
            + " session_id=" + sessionId + " reason=" + reason
            + " world=" + worldId + " player_uuid=" + playerId
            + " tick=" + (subject != null ? subject.getWorld().getFullTime() : -1)
            + " forward_boost_ticks=" + forwardTicks
            + " motion_estimated_boost_ticks=" + motionProjectedBoostTicks
            + " other_direction_or_ambiguous_ticks=" + cappedTicks
            + " modifier_applied=false"
            + " p1_motor_dev=" + p1MotorDev
            + " p1_final_fatigue=" + p1Fatigue
            + " p1_world_ticks=" + p1WorldTicks
            + " authority=NONE P1_APPLIED=false M0_POSTED=false");
        if ("OWNER_RELEASE".equals(reason)
                && getConfig().getBoolean("post-release-motion-dev", false)
                && safeSubject() && postReleaseTask == null) {
            // This callback can neither issue new native Action nor alter
            // motor/P1/M0. First delta may straddle clear-controls receipt
            // (MIXED); subsequent deltas are purely post-release samples.
            postReleaseStartTick = subject.getWorld().getFullTime();
            postReleaseLastTick = postReleaseStartTick;
            postReleaseLastX = subject.getLocation().getX();
            postReleaseLastZ = subject.getLocation().getZ();
            postReleaseCount = 0;
            postReleaseTask = Bukkit.getScheduler().runTaskTimer(
                this, this::samplePostRelease, 1L, 1L
            );
        }
    }

    private void samplePostRelease() {
        if (postReleaseTask == null) {
            return;
        }
        if (!Bukkit.isPrimaryThread() || !safeSubject()) {
            getLogger().warning("S49_DASH_DEV_POST_ABORT actor_or_thread_changed");
            postReleaseTask.cancel();
            postReleaseTask = null;
            return;
        }
        long tick = subject.getWorld().getFullTime();
        // Like the original ARM callback, Bukkit may invoke a scheduled
        // observer within its registration World tick. This is zero elapsed
        // World time and must NOT be reported as a post-release tick.
        if (postReleaseCount == 0 && tick == postReleaseStartTick) {
            return;
        }
        if (tick <= postReleaseLastTick || tick != postReleaseStartTick + postReleaseCount + 1) {
            getLogger().warning("S49_DASH_DEV_POST_ABORT tick_gap_or_replay"
                + " current=" + tick + " start=" + postReleaseStartTick
                + " last=" + postReleaseLastTick + " count=" + postReleaseCount);
            postReleaseTask.cancel();
            postReleaseTask = null;
            return;
        }
        AttributeInstance speed = subject.getAttribute(Attribute.MOVEMENT_SPEED);
        if (speed == null || modifier == null
                || speed.getModifier(modifier.getKey()) != null) {
            getLogger().warning("S49_DASH_DEV_POST_ABORT modifier_not_removed");
            postReleaseTask.cancel();
            postReleaseTask = null;
            return;
        }
        double x = subject.getLocation().getX();
        double z = subject.getLocation().getZ();
        double delta = Math.hypot(x - postReleaseLastX, z - postReleaseLastZ);
        postReleaseCount++;
        getLogger().info("S49_DASH_DEV_POST_RELEASE action_id=" + actionId
            + " session_id=" + sessionId + " tick=" + tick
            + " index=" + postReleaseCount
            + " world=" + worldId + " player_uuid=" + playerId
            + " horizontal_delta_m=" + delta
            + " boundary=" + (postReleaseCount == 1 ? "MIXED" : "POST_RELEASE")
            + " modifier_present=false motor_write=false"
            + " P1_APPLIED=false M0_POSTED=false WAIT_ATTESTED=false");
        postReleaseLastTick = tick;
        postReleaseLastX = x;
        postReleaseLastZ = z;
        if (postReleaseCount == 5) {
            postReleaseTask.cancel();
            postReleaseTask = null;
        }
    }

    @EventHandler
    public void onQuit(PlayerQuitEvent event) {
        if (armed && event.getPlayer().getUniqueId().equals(playerId)) {
            disarm("PLAYER_QUIT");
        }
    }

    @Override
    public void onDisable() {
        disarm("PLUGIN_DISABLED");
        if (postReleaseTask != null) {
            postReleaseTask.cancel();
            postReleaseTask = null;
        }
        endTwoActionTrail("PLUGIN_DISABLED");
        getLogger().info("S49_DASH_DEV_STOPPED");
    }
}
