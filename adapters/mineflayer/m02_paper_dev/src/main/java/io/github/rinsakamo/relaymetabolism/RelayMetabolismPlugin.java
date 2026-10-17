package io.github.rinsakamo.relaymetabolism;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.EnumMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import com.destroystokyo.paper.event.entity.EntityAddToWorldEvent;
import com.destroystokyo.paper.event.entity.EntityRemoveFromWorldEvent;
import org.bukkit.Bukkit;
import org.bukkit.Chunk;
import org.bukkit.GameMode;
import org.bukkit.Location;
import org.bukkit.World;
import org.bukkit.block.Block;
import org.bukkit.command.Command;
import org.bukkit.command.CommandSender;
import org.bukkit.command.ConsoleCommandSender;
import org.bukkit.configuration.ConfigurationSection;
import org.bukkit.entity.Entity;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.entity.EntityExhaustionEvent;
import org.bukkit.event.entity.EntityDamageByEntityEvent;
import org.bukkit.event.entity.EntityDamageEvent;
import org.bukkit.event.player.PlayerAnimationEvent;
import org.bukkit.event.player.PlayerInteractEvent;
import org.bukkit.event.player.PlayerVelocityEvent;
import org.bukkit.event.player.PlayerMoveEvent;
import org.bukkit.event.player.PlayerTeleportEvent;
import org.bukkit.event.world.ChunkLoadEvent;
import org.bukkit.event.world.ChunkUnloadEvent;
import org.bukkit.plugin.java.JavaPlugin;

/**
 * DEV-only Paper 1.21.8 M0.2 body-physics candidate.
 *
 * Source of physical truth remains Minecraft food/saturation/HP/exhaustion.
 * Never attaches to an existing Vanilla RSEE World or infers Self Action IDs.
 */
public final class RelayMetabolismPlugin extends JavaPlugin implements Listener {
    private static final Set<String> PER_CM = Set.of(
        "WALK", "CROUCH", "SPRINT", "SWIM",
        "WALK_ON_WATER", "WALK_UNDERWATER"
    );
    private static final Set<String> NATIVE = Set.of(
        "WALK_ON_WATER", "WALK_UNDERWATER", "REGEN",
        "HUNGER_EFFECT", "UNKNOWN"
    );
    private static final Set<String> SYNTHETIC = Set.of("BASAL", "COGNITION");

    private final Map<EntityExhaustionEvent.ExhaustionReason, Rule> rules =
        new EnumMap<>(EntityExhaustionEvent.ExhaustionReason.class);
    private Rule basal;
    private boolean devActive = false;
    // Bukkit delayed task runs one full-time earlier than its delay argument
    // in this actual Paper 1.21.8 DEV profile; bracket target by source.
    private static final long S50_CLOCK_GATE_SCHEDULER_DELAY = 7L;
    private static final long S50_CLOCK_GATE_TARGET_WORLD_DELTA = 6L;
    private final Set<String> scheduledS50ClockGates = new HashSet<>();
    private String target;
    private String s50Marker = "NONE";
    private long s50ObserveUntil = -1;
    private long appliedTicks = 0;
    private long modifiedEvents = 0;
    private long observedWalkEvents = 0;
    private long observedSprintEvents = 0;
    private long observedMotionPackets = 0;
    private double observedMotionBlocks = 0;
    private double chargedMotionExhaustion = 0;
    private double requestedBasalExhaustion = 0;
    // Separate prospective S50 fixed-pose DEV: World-tick position billing.
    // False on all historical Paper profiles and non-controlled World runs.
    private boolean s50TickMeterCandidate = false;
    private boolean s50TickMeterArmed = false;
    private Location s50TickMeterLast;
    private long s50TickMeterRows = 0;
    private double s50TickMeterBlocks = 0;
    private double s50TickMeterCharged = 0;
    private boolean s50ClearObserved = false;
    private boolean s50WaitObserveActive = false;
    private int s50WaitSourceRows = 0;
    private long s50WaitStartWorldTick = -1;
    private Location s50WaitLast;
    private long s50WaitCombatEvents = 0;
    private long s50WaitSwingEvents = 0;
    private long s50WaitAllMovementEvents = 0;
    private long s50WaitTeleportEvents = 0;
    private long s50WaitVelocityEvents = 0;
    private long s50WaitDamageEvents = 0;
    private long s50WaitInteractEvents = 0;
    // DEV-only prospective callback-bounded entity/chunk lifecycle witness.
    // Explicitly NOT a proof of all packets or of an entire World tick.
    private static final long S50_WAIT_LIFECYCLE_MAX_EVENTS = 256;
    private long s50WaitLifecycleEvents = 0;
    private boolean s50WaitLifecycleOverflow = false;
    private volatile boolean s50WaitLifecycleAsync = false;

    /** Bounded +X first-tick corridor, not proof of collision or paired start. */
    private static String devCorridor(World world, Location center) {
        int x = center.getBlockX(), y = center.getBlockY(), z = center.getBlockZ();
        StringBuilder result = new StringBuilder();
        for (int dx = 0; dx < 4; dx++) {
            Block ground = world.getBlockAt(x + dx, y - 1, z);
            Block feet = world.getBlockAt(x + dx, y, z);
            Block head = world.getBlockAt(x + dx, y + 1, z);
            if (dx != 0) {
                result.append(';');
            }
            result.append(dx).append(':')
                .append(ground.getType().name()).append(':')
                .append(ground.getType().isSolid() ? '1' : '0').append(':')
                .append(feet.getType().name()).append(':')
                .append(feet.isPassable() ? '1' : '0').append(':')
                .append(head.getType().name()).append(':')
                .append(head.isPassable() ? '1' : '0');
        }
        return result.toString();
    }

    private record Rule(String unit, double standard, boolean nativeValue,
                        double multiplier, double additional, boolean enabled) {
        double perEvent(double nativeExhaustion) {
            // Source exhaustion event values are NOT evidence of distance.
            // Numeric land-motion rules use true packet displacement instead;
            // this method only handles other original native events.
            double q = unit.equals("block") ? 0.01 : 1.0;
            double baseline = nativeValue ? nativeExhaustion : standard * q;
            double extra = additional * q;
            double value = enabled ? baseline * multiplier + extra : 0;
            if (!Double.isFinite(value) || value < 0 || value > Float.MAX_VALUE) {
                throw new IllegalStateException("nonfinite or negative exhaustion");
            }
            return value;
        }
    }

    private static double nonnegative(Object value, String context) {
        if (!(value instanceof Number number)) {
            throw new IllegalStateException(context + " must be a numeric literal");
        }
        double n = number.doubleValue();
        if (!Double.isFinite(n) || n < 0) {
            throw new IllegalStateException(context + " must be finite nonnegative");
        }
        return n;
    }

    private static Rule readRule(ConfigurationSection section, String reason) {
        if (section == null || !section.getKeys(false).equals(
                Set.of("unit", "standard", "multiplier", "additional", "enabled"))) {
            throw new IllegalStateException("missing/extra M0.2 keys: " + reason);
        }
        Object u = section.get("unit");
        String unit = u instanceof String s ? s : "";
        String expected = reason.equals("BASAL") ? "tick" :
            reason.equals("COGNITION") ? "work" :
            PER_CM.contains(reason) ? "block" : "event";
        if (!unit.equals(expected)) {
            throw new IllegalStateException("incorrect exhaustion unit: " + reason);
        }
        Object s = section.get("standard");
        boolean nativeValue = "native".equals(s);
        if (nativeValue != NATIVE.contains(reason)) {
            throw new IllegalStateException("native baseline mismatch: " + reason);
        }
        double standard = nativeValue ? 0 : nonnegative(s, reason + ".standard");
        double multiplier = nonnegative(section.get("multiplier"), reason + ".multiplier");
        double additional = nonnegative(section.get("additional"), reason + ".additional");
        if (!(section.get("enabled") instanceof Boolean enabled)) {
            throw new IllegalStateException("enabled must be boolean: " + reason);
        }
        if (!reason.equals("COGNITION") && !enabled) {
            throw new IllegalStateException("only cognition may be disabled");
        }
        if (reason.equals("COGNITION") && enabled) {
            // Physical cognition source/usage is not admitted by M0.2.
            throw new IllegalStateException("cognition enablement not qualified in DEV");
        }
        return new Rule(unit, standard, nativeValue, multiplier, additional, enabled);
    }

    @Override
    public void onEnable() {
        saveDefaultConfig();
        if (!getConfig().isBoolean("dev-enabled") || !getConfig().getBoolean("dev-enabled")) {
            getLogger().info("M02_DEV_DISABLED (default); no World mutations");
            return;
        }
        try {
            if (!"1.21.8".equals(getConfig().getString("minecraft-version"))) {
                throw new IllegalStateException("Paper 1.21.8 required");
            }
            if (!"M0.2".equals(getConfig().getString("version"))
                    || !"cooked_beef".equals(getConfig().getString("standard-food"))
                    || !"candidate_uncalibrated".equals(
                        getConfig().getString("calibration-status"))) {
                throw new IllegalStateException("unknown or uncalibrated profile shape");
            }
            if (getConfig().contains("s50-tick-meter-dev")
                    && !getConfig().isBoolean("s50-tick-meter-dev")) {
                throw new IllegalStateException("invalid S50 tick meter DEV flag");
            }
            s50TickMeterCandidate = getConfig().getBoolean("s50-tick-meter-dev", false);
            target = getConfig().getString("target-player", "");
            if (!target.equals("RelaySelf")) {
                throw new IllegalStateException("only the owned RelaySelf dev bot is supported");
            }
            ConfigurationSection sections = getConfig().getConfigurationSection("actions");
            if (sections == null) {
                throw new IllegalStateException("missing actions");
            }
            Set<String> known = new HashSet<>(SYNTHETIC);
            for (EntityExhaustionEvent.ExhaustionReason reason :
                    EntityExhaustionEvent.ExhaustionReason.values()) {
                known.add(reason.name());
            }
            if (!sections.getKeys(false).equals(known)) {
                throw new IllegalStateException("exhaustion reason set mismatch");
            }
            basal = readRule(sections.getConfigurationSection("BASAL"), "BASAL");
            readRule(sections.getConfigurationSection("COGNITION"), "COGNITION");
            rules.clear();
            for (EntityExhaustionEvent.ExhaustionReason reason :
                    EntityExhaustionEvent.ExhaustionReason.values()) {
                rules.put(reason, readRule(
                    sections.getConfigurationSection(reason.name()), reason.name()));
            }
            if (!Arrays.equals(
                    EntityExhaustionEvent.ExhaustionReason.values(),
                    rules.keySet().stream().toArray(EntityExhaustionEvent.ExhaustionReason[]::new))) {
                // Do not depend on enum iteration or plugin package ordering:
                // the exact set check above is the actual admission condition.
                if (rules.size() != EntityExhaustionEvent.ExhaustionReason.values().length) {
                    throw new IllegalStateException("incomplete reason map");
                }
            }
            Bukkit.getPluginManager().registerEvents(this, this);
            devActive = true;
            Bukkit.getScheduler().runTaskTimer(this, () -> {
                Player p = Bukkit.getPlayerExact(target);
                if (p == null || !p.isOnline() || p.isDead()) {
                    return;
                }
                if (s50TickMeterArmed) {
                    meterS50Tick(p);
                    if (!devActive) {
                        return;
                    }
                }
                if (s50WaitObserveActive && s50WaitSourceRows < 8) {
                    Location where = p.getLocation();
                    long tick = p.getWorld().getFullTime();
                    // The first callback may occur in the same World tick as
                    // command acknowledgement. That incomplete tick is not WAIT.
                    if (tick > s50WaitStartWorldTick) {
                        Location from = s50WaitLast;
                        getLogger().info("S50_DEV_WAIT_TICK marker_id=" + s50Marker
                            + " world=" + p.getWorld().getUID()
                            + " tick=" + tick + " index=" + (s50WaitSourceRows + 1)
                            + " from_x=" + from.getX() + " from_y=" + from.getY()
                            + " from_z=" + from.getZ()
                            + " x=" + where.getX() + " y=" + where.getY()
                            + " z=" + where.getZ()
                            + " motion_packets=" + observedMotionPackets
                            + " motion_blocks=" + observedMotionBlocks
                            + " tick_meter_blocks=" + s50TickMeterBlocks
                            + " combat_events=" + s50WaitCombatEvents
                            + " swing_events=" + s50WaitSwingEvents
                            + " sprint=" + p.isSprinting() + " sneak=" + p.isSneaking()
                            + " swimming=" + p.isSwimming()
                            + " basal_ticks=" + appliedTicks);
                        try {
                            logS50WaitScope(p, tick, s50WaitSourceRows + 1);
                            getLogger().info("S50_DEV_WAIT_LIFECYCLE_SAMPLE marker_id="
                                + s50Marker + " world=" + p.getWorld().getUID()
                                + " tick=" + tick + " index=" + (s50WaitSourceRows + 1)
                                + " event_count=" + s50WaitLifecycleEvents
                                + " overflow=" + s50WaitLifecycleOverflow
                                + " async_seen=" + s50WaitLifecycleAsync
                                + " coverage=CALLBACK_PREFIX_TO_SAMPLE_ONLY");
                        } catch (RuntimeException exc) {
                            getLogger().severe("S50_DEV_WAIT_SCOPE_REJECT reason="
                                + exc.getClass().getSimpleName());
                            devActive = false;
                            Bukkit.getPluginManager().disablePlugin(this);
                            return;
                        }
                        s50WaitSourceRows++;
                        s50WaitLast = where.clone();
                        if (s50WaitSourceRows == 8) {
                            s50WaitObserveActive = false;
                        }
                    }
                }
                if (p.getWorld().getFullTime() <= s50ObserveUntil) {
                    Location loc = p.getLocation();
                    getLogger().info("S50_DEV_TICK marker_id=" + s50Marker
                        + " world=" + p.getWorld().getUID()
                        + " tick=" + p.getWorld().getFullTime()
                        + " packets=" + observedMotionPackets
                        + " blocks=" + observedMotionBlocks
                        + " billed=" + chargedMotionExhaustion
                        + " tick_meter_blocks=" + s50TickMeterBlocks
                        + " tick_meter_billed=" + s50TickMeterCharged
                        + " x=" + loc.getX() + " y=" + loc.getY() + " z=" + loc.getZ());
                }
                double delta = basal.perEvent(0);
                double before = p.getExhaustion();
                double next = before + delta;
                // Minecraft exhaustion is internally bounded. The player API
                // clamps when necessary; never decrease native exhaustion.
                if (Double.isFinite(next) && next <= Float.MAX_VALUE) {
                    p.setExhaustion((float) next);
                    appliedTicks++;
                    requestedBasalExhaustion += delta;
                    // Original source at the actual Paper setExhaustion write.
                    // observed_after is a readback, not a promise that hunger
                    // processing never subsequently transfers exhaustion.
                    // Bound log volume; a missing tick before 200 fails DEV.
                    if (appliedTicks <= 500) {
                        Location pose = p.getLocation();
                        if (appliedTicks == 1) {
                            getLogger().info("M02_DEV_WORLD_V7_FIRST_TICK seed="
                                + p.getWorld().getSeed()
                                + " full_time=" + p.getWorld().getFullTime()
                                + " x=" + pose.getX() + " y=" + pose.getY()
                                + " z=" + pose.getZ() + " yaw=" + pose.getYaw()
                                + " pitch=" + pose.getPitch()
                                + " corridor=" + devCorridor(p.getWorld(), pose));
                        }
                        getLogger().info("M02_DEV_BASAL_WRITE id=" + appliedTicks
                            + " world_full_time=" + p.getWorld().getFullTime()
                            + " before=" + before + " requested=" + delta
                            + " write_target=" + next
                            + " observed_after=" + p.getExhaustion()
                            + " cumulative_requested=" + requestedBasalExhaustion
                            + " x=" + pose.getX() + " y=" + pose.getY()
                            + " z=" + pose.getZ() + " yaw=" + pose.getYaw()
                            + " pitch=" + pose.getPitch());
                    }
                } else {
                    getLogger().severe("invalid basal exhaustion; disabling plugin");
                    Bukkit.getPluginManager().disablePlugin(this);
                }
                if (appliedTicks == 1 || appliedTicks == 20 || appliedTicks % 100 == 0) {
                    getLogger().info("M02_DEV_BODY sampled_tick=" + appliedTicks
                        + " player=" + target + " food=" + p.getFoodLevel()
                        + " saturation=" + p.getSaturation()
                        + " health=" + p.getHealth()
                        + " exhaustion=" + p.getExhaustion()
                        + " events=" + modifiedEvents
                        + " walk_events=" + observedWalkEvents
                        + " sprint_events=" + observedSprintEvents
                        + " motion_packets=" + observedMotionPackets
                        + " motion_blocks=" + observedMotionBlocks
                        + " motion_charge=" + chargedMotionExhaustion);
                }
            }, 1L, 1L);
            getLogger().warning("M02_DEV_ONLY: candidate physics, not qualified by R/V");
        } catch (RuntimeException ex) {
            getLogger().severe("M02_DEV_DISABLED: " + ex.getMessage());
            Bukkit.getPluginManager().disablePlugin(this);
        }
    }



    /**
     * DEV-only prospective accepted World-state tick displacement lower-bound.
     * Charged once at the actual native Paper player exhaustion writer.
     * The segment between two sampled poses cannot establish any sub-tick
     * turn/loop: it is a lower bound, not a certified exact continuous path.
     */
    private void meterS50Tick(Player player) {
        Location from = s50TickMeterLast;
        Location to = player.getLocation();
        if (from == null || from.getWorld() != to.getWorld()
                || player.isDead() || player.isInWater() || player.isSprinting()
                || player.isSneaking()) {
            getLogger().severe("S50_DEV_TICK_METER_REJECT foreign state");
            devActive = false;
            Bukkit.getPluginManager().disablePlugin(this);
            return;
        }
        double dx = to.getX() - from.getX(), dz = to.getZ() - from.getZ();
        double blocks = Math.hypot(dx, dz);
        if (!Double.isFinite(blocks) || blocks < 0 || blocks > 1.0
                || !Double.isFinite(to.getY()) || !Double.isFinite(from.getY())
                || Math.abs(to.getY() - from.getY()) > 0.5) {
            getLogger().severe("S50_DEV_TICK_METER_REJECT invalid displacement");
            devActive = false;
            Bukkit.getPluginManager().disablePlugin(this);
            return;
        }
        Rule rule = rules.get(EntityExhaustionEvent.ExhaustionReason.WALK);
        if (rule == null) {
            getLogger().severe("S50_DEV_TICK_METER_REJECT no WALK rule");
            devActive = false;
            Bukkit.getPluginManager().disablePlugin(this);
            return;
        }
        double charged = blocks * (rule.standard * rule.multiplier + rule.additional);
        double before = player.getExhaustion(), next = before + charged;
        if (!Double.isFinite(charged) || charged < 0 || !Double.isFinite(next)
                || next > Float.MAX_VALUE) {
            getLogger().severe("S50_DEV_TICK_METER_REJECT invalid exhaustion");
            devActive = false;
            Bukkit.getPluginManager().disablePlugin(this);
            return;
        }
        player.setExhaustion((float) next);
        s50TickMeterRows++;
        s50TickMeterBlocks += blocks;
        s50TickMeterCharged += charged;
        if (s50TickMeterRows <= 500) {
            getLogger().info("S50_DEV_TICK_MOTION id=" + s50TickMeterRows
                + " marker_id=" + s50Marker
                + " world=" + player.getWorld().getUID()
                + " world_full_time=" + player.getWorld().getFullTime()
                + " from_x=" + from.getX() + " from_y=" + from.getY()
                + " from_z=" + from.getZ()
                + " to_x=" + to.getX() + " to_y=" + to.getY()
                + " to_z=" + to.getZ()
                + " blocks=" + blocks + " billed=" + charged
                + " cumulative_blocks=" + s50TickMeterBlocks
                + " cumulative_billed=" + s50TickMeterCharged
                + " write_before=" + before
                + " write_target=" + next
                + " write_after=" + player.getExhaustion());
        }
        s50TickMeterLast = to.clone();
    }


    /** Server-side timestamp for DEV S50 control-command boundaries only.
     *  No player, R grant, Action authorization or physiology mutation.
     *  Console-only command: the marker cannot assert when server inputs
     *  actually changed, only when a phase boundary was observed on Paper.
     */
    @Override
    public boolean onCommand(CommandSender sender, Command command,
                             String label, String[] args) {
        if (command.getName().equalsIgnoreCase("relaydevsnapshot")) {
            if (!devActive || !(sender instanceof ConsoleCommandSender)
                    || args.length != 1 || !args[0].matches("[A-Za-z0-9_-]{1,128}")) {
                return false;
            }
            Player p = Bukkit.getPlayerExact(target);
            if (p == null || !p.isOnline() || p.isDead()) return false;
            Location loc = p.getLocation();
            getLogger().info("S_V8_DEV_SNAPSHOT marker_id=" + args[0]
                + " world=" + p.getWorld().getUID() + " seed=" + p.getWorld().getSeed()
                + " full_time=" + p.getWorld().getFullTime()
                + " player_tick=" + appliedTicks
                + " x=" + loc.getX() + " y=" + loc.getY() + " z=" + loc.getZ()
                + " yaw=" + loc.getYaw() + " pitch=" + loc.getPitch()
                + " food=" + p.getFoodLevel() + " saturation=" + p.getSaturation()
                + " health=" + p.getHealth() + " exhaustion=" + p.getExhaustion()
                + " basal_requested=" + requestedBasalExhaustion
                + " motion_blocks=" + observedMotionBlocks
                + " motion_billed=" + chargedMotionExhaustion);
            return true;
        }
        if (command.getName().equalsIgnoreCase("relaydevwait")) {
            if (!devActive || !s50TickMeterCandidate
                    || !(sender instanceof ConsoleCommandSender)
                    || args.length != 1 || !args[0].matches("[A-Za-z0-9_-]{1,128}")
                    || !s50ClearObserved || s50WaitObserveActive
                    || s50WaitSourceRows != 0 || !s50Marker.equals(args[0])) {
                return false;
            }
            Player waiting = Bukkit.getPlayerExact(target);
            if (waiting == null || !waiting.isOnline() || waiting.isDead()) {
                return false;
            }
            Location where = waiting.getLocation();
            s50WaitStartWorldTick = waiting.getWorld().getFullTime();
            s50WaitLast = where.clone();
            s50WaitObserveActive = true;
            s50WaitLifecycleEvents = 0;
            s50WaitLifecycleOverflow = false;
            s50WaitLifecycleAsync = false;
            getLogger().info("S50_DEV_WAIT_LIFECYCLE_BEGIN marker_id=" + s50Marker
                + " world=" + waiting.getWorld().getUID()
                + " tick=" + s50WaitStartWorldTick
                + " subject_uuid=" + waiting.getUniqueId()
                + " event_count=0 coverage=CALLBACK_PREFIX_TO_SAMPLE_ONLY");
            getLogger().info("S50_DEV_WAIT_BEGIN marker_id=" + s50Marker
                + " world=" + waiting.getWorld().getUID()
                + " tick=" + s50WaitStartWorldTick
                + " packets=" + observedMotionPackets
                + " blocks=" + observedMotionBlocks
                + " tick_meter_blocks=" + s50TickMeterBlocks
                + " combat_events=" + s50WaitCombatEvents
                + " swing_events=" + s50WaitSwingEvents
                + " basal_ticks=" + appliedTicks
                + " x=" + where.getX() + " y=" + where.getY()
                + " z=" + where.getZ());
            return true;
        }
        if (!command.getName().equalsIgnoreCase("relaydevphase")
                || !devActive || !(sender instanceof ConsoleCommandSender)
                || args.length != 2
                || !args[0].matches("[A-Za-z0-9_-]{1,128}")
                || !Set.of("PRE_FORWARD", "POST_FORWARD", "PRE_CLEAR", "POST_CLEAR")
                    .contains(args[1])) {
            return false;
        }
        Player p = Bukkit.getPlayerExact(target);
        if (p == null || !p.isOnline() || p.isDead()) {
            return false;
        }
        if (args[1].equals("PRE_FORWARD")) {
            if (!s50Marker.equals("NONE")) {
                return false;
            }
            s50Marker = args[0];
            s50ObserveUntil = p.getWorld().getFullTime() + 100;
            if (s50TickMeterCandidate) {
                // PRE_FORWARD is a source observation BEFORE the existing
                // native client forward command, not a new movement issuer.
                s50TickMeterLast = p.getLocation().clone();
                s50TickMeterArmed = true;
                getLogger().info("S50_DEV_TICK_METER_ARM marker_id=" + s50Marker
                    + " world=" + p.getWorld().getUID()
                    + " world_full_time=" + p.getWorld().getFullTime()
                    + " x=" + s50TickMeterLast.getX()
                    + " y=" + s50TickMeterLast.getY()
                    + " z=" + s50TickMeterLast.getZ());
            }
        } else if (!s50Marker.equals(args[0])) {
            return false;
        }
        if (args[1].equals("POST_CLEAR")) {
            s50ClearObserved = true;
        }
        Location pose = p.getLocation();
        long phaseWorldTime = p.getWorld().getFullTime();
        getLogger().info("M02_DEV_S50_PHASE marker_id=" + args[0]
            + " phase=" + args[1] + " world_full_time="
            + phaseWorldTime + " player_tick=" + appliedTicks
            + " world=" + p.getWorld().getUID()
            + " packets=" + observedMotionPackets + " blocks=" + observedMotionBlocks
            + " billed=" + chargedMotionExhaustion
            + " x=" + pose.getX() + " y=" + pose.getY() + " z=" + pose.getZ());
        if (args[1].equals("POST_FORWARD")) {
            // Pure time gate, not a player movement command or Action issuer.
            // The existing S50 native client clear remains the exclusive clear.
            // Duplicated marker IDs cannot reschedule a second clock gate.
            if (!scheduledS50ClockGates.add(args[0])) {
                return false;
            }
            final String markerId = args[0];
            final World originalWorld = p.getWorld();
            Bukkit.getScheduler().runTaskLater(this, () -> {
                Player current = Bukkit.getPlayerExact(target);
                if (current == null || !current.isOnline() || current.isDead()
                        || current.getWorld() != originalWorld) {
                    getLogger().warning("M02_DEV_S50_CLOCK_GATE_INVALID marker_id="
                        + markerId + " reason=MISSING_OR_FOREIGN_WORLD");
                    return;
                }
                Location now = current.getLocation();
                getLogger().info("M02_DEV_S50_CLOCK_GATE marker_id=" + markerId
                    + " scheduler_delay=" + S50_CLOCK_GATE_SCHEDULER_DELAY
                    + " target_world_delta=" + S50_CLOCK_GATE_TARGET_WORLD_DELTA
                    + " base_full_time=" + phaseWorldTime
                    + " reached_full_time=" + originalWorld.getFullTime()
                    + " player_tick=" + appliedTicks
                    + " x=" + now.getX() + " y=" + now.getY()
                    + " z=" + now.getZ());
            }, S50_CLOCK_GATE_SCHEDULER_DELAY);
        }
        return true;
    }


    /**
     * DEV ONLY: enumerate all CURRENTLY loaded chunks across all Paper Worlds.
     * This is not an entity lifecycle history, a complete World snapshot, or
     * proof that a mob did not spawn/despawn between consecutive callbacks.
     */
    private void logS50WaitScope(Player subject, long tick, int index) {
        List<String> entries = new ArrayList<>();
        long loadedChunks = 0;
        long entityCount = 0;
        long others = 0;
        for (World world : Bukkit.getWorlds()) {
            Chunk[] chunks = world.getLoadedChunks();
            loadedChunks += chunks.length;
            if (loadedChunks > 4096) {
                throw new IllegalStateException("WAIT census loaded-chunk cap exceeded");
            }
            for (Chunk chunk : chunks) {
                for (Entity entity : chunk.getEntities()) {
                    entityCount++;
                    if (entityCount > 32768) {
                        throw new IllegalStateException("WAIT census entity cap exceeded");
                    }
                    if (!entity.getUniqueId().equals(subject.getUniqueId())) {
                        others++;
                    }
                    entries.add(world.getUID() + ":" + chunk.getX() + ":"
                        + chunk.getZ() + ":" + entity.getUniqueId() + ":"
                        + entity.getType().name());
                }
            }
        }
        Collections.sort(entries);
        if (entries.size() > 512) {
            throw new IllegalStateException("WAIT roster explicit source cap exceeded");
        }
        // Authoritative for the *sampled loaded chunk set* only.
        // Preserve one native row per entity rather than only a producer hash.
        for (int itemIndex = 0; itemIndex < entries.size(); itemIndex++) {
            String[] fields = entries.get(itemIndex).split(":", -1);
            if (fields.length != 5) {
                throw new IllegalStateException("invalid source roster tuple");
            }
            getLogger().info("S50_DEV_WAIT_ENTITY marker_id=" + s50Marker
                + " world=" + subject.getWorld().getUID()
                + " tick=" + tick + " index=" + index
                + " roster_index=" + (itemIndex + 1)
                + " entity_world=" + fields[0]
                + " chunk_x=" + fields[1] + " chunk_z=" + fields[2]
                + " uuid=" + fields[3] + " type=" + fields[4]);
        }
        StringBuilder canonical = new StringBuilder();
        for (String item : entries) {
            canonical.append(item).append('\n');
        }
        String digest;
        try {
            byte[] bits = MessageDigest.getInstance("SHA-256").digest(
                canonical.toString().getBytes(StandardCharsets.UTF_8));
            StringBuilder hex = new StringBuilder();
            for (byte bit : bits) {
                hex.append(String.format("%02x", bit & 0xff));
            }
            digest = hex.toString();
        } catch (NoSuchAlgorithmException exc) {
            throw new IllegalStateException("SHA256 unavailable", exc);
        }
        long otherOnline = Bukkit.getOnlinePlayers().stream()
            .filter(p -> !p.getUniqueId().equals(subject.getUniqueId())).count();
        getLogger().info("S50_DEV_WAIT_SCOPE marker_id=" + s50Marker
            + " world=" + subject.getWorld().getUID()
            + " tick=" + tick + " index=" + index
            + " loaded_worlds=" + Bukkit.getWorlds().size()
            + " loaded_chunks=" + loadedChunks
            + " loaded_entities=" + entityCount
            + " subject_uuid=" + subject.getUniqueId()
            + " other_loaded_entities=" + others
            + " other_online_players=" + otherOnline
            + " census_sha256=" + digest
            + " movement_events=" + s50WaitAllMovementEvents
            + " teleport_events=" + s50WaitTeleportEvents
            + " velocity_events=" + s50WaitVelocityEvents
            + " damage_events=" + s50WaitDamageEvents
            + " interact_events=" + s50WaitInteractEvents
            + " combat_events=" + s50WaitCombatEvents
            + " swing_events=" + s50WaitSwingEvents
            + " coverage=LOADED_CHUNK_SAMPLER_ONLY"
            + " client_held_controls=NOT_OBSERVED"
            + " entity_lifecycle=NOT_ATTESTED");
    }

    /** Prospective Paper callback ledger; never confers P1 WAIT admission. */
    private void logS50WaitLifecycle(String kind, World eventWorld, String entityId,
                                     String type, int chunkX, int chunkZ) {
        if (!s50WaitObserveActive || s50WaitSourceRows >= 8) {
            return;
        }
        if (!Bukkit.isPrimaryThread()) {
            s50WaitLifecycleAsync = true;
            return;
        }
        Player subject = Bukkit.getPlayerExact(target);
        if (subject == null || !subject.isOnline() || subject.isDead()) {
            s50WaitLifecycleOverflow = true;
            return;
        }
        s50WaitLifecycleEvents++;
        if (s50WaitLifecycleEvents > S50_WAIT_LIFECYCLE_MAX_EVENTS) {
            s50WaitLifecycleOverflow = true;
            return;
        }
        getLogger().info("S50_DEV_WAIT_LIFECYCLE_EVENT marker_id=" + s50Marker
            + " world=" + subject.getWorld().getUID()
            + " tick=" + subject.getWorld().getFullTime()
            + " seq=" + s50WaitLifecycleEvents
            + " kind=" + kind
            + " entity_world=" + eventWorld.getUID()
            + " entity_tick=" + eventWorld.getFullTime()
            + " uuid=" + entityId + " type=" + type
            + " chunk_x=" + chunkX + " chunk_z=" + chunkZ
            + " coverage=PAPER_CALLBACK_ONLY");
    }

    @EventHandler(priority = EventPriority.MONITOR)
    public void onDevWaitEntityAdded(EntityAddToWorldEvent event) {
        Entity entity = event.getEntity();
        Location where = entity.getLocation();
        logS50WaitLifecycle("ENTITY_ADD", event.getWorld(),
            entity.getUniqueId().toString(), entity.getType().name(),
            where.getBlockX() >> 4, where.getBlockZ() >> 4);
    }

    @EventHandler(priority = EventPriority.MONITOR)
    public void onDevWaitEntityRemoved(EntityRemoveFromWorldEvent event) {
        Entity entity = event.getEntity();
        Location where = entity.getLocation();
        // Removal must use event.getWorld(), not entity.getWorld(): Paper
        // may already have updated the entity's world on removal.
        logS50WaitLifecycle("ENTITY_REMOVE", event.getWorld(),
            entity.getUniqueId().toString(), entity.getType().name(),
            where.getBlockX() >> 4, where.getBlockZ() >> 4);
    }

    @EventHandler(priority = EventPriority.MONITOR)
    public void onDevWaitChunkLoad(ChunkLoadEvent event) {
        logS50WaitLifecycle("CHUNK_LOAD", event.getWorld(), "NONE", "CHUNK",
            event.getChunk().getX(), event.getChunk().getZ());
    }

    @EventHandler(priority = EventPriority.MONITOR)
    public void onDevWaitChunkUnload(ChunkUnloadEvent event) {
        logS50WaitLifecycle("CHUNK_UNLOAD", event.getWorld(), "NONE", "CHUNK",
            event.getChunk().getX(), event.getChunk().getZ());
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = false)
    public void onDevWaitAnyMove(PlayerMoveEvent event) {
        if (s50TickMeterCandidate && event.getPlayer().getName().equals(target)) {
            s50WaitAllMovementEvents++;
            if (event instanceof PlayerTeleportEvent) {
                s50WaitTeleportEvents++;
            }
        }
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = false)
    public void onDevWaitVelocity(PlayerVelocityEvent event) {
        if (s50TickMeterCandidate && event.getPlayer().getName().equals(target)) {
            s50WaitVelocityEvents++;
        }
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = false)
    public void onDevWaitAnyDamage(EntityDamageEvent event) {
        if (s50TickMeterCandidate && event.getEntity() instanceof Player player
                && player.getName().equals(target)) {
            s50WaitDamageEvents++;
        }
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = false)
    public void onDevWaitInteract(PlayerInteractEvent event) {
        if (s50TickMeterCandidate && event.getPlayer().getName().equals(target)) {
            s50WaitInteractEvents++;
        }
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
    public void onDevWaitCombat(EntityDamageByEntityEvent event) {
        if (s50TickMeterCandidate && event.getDamager() instanceof Player p
                && p.getName().equals(target)) {
            s50WaitCombatEvents++;
        }
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
    public void onDevWaitSwing(PlayerAnimationEvent event) {
        if (s50TickMeterCandidate && event.getPlayer().getName().equals(target)) {
            s50WaitSwingEvents++;
        }
    }

    @EventHandler(priority = EventPriority.HIGHEST, ignoreCancelled = true)
    public void onLandMotion(PlayerMoveEvent event) {
        if (event instanceof PlayerTeleportEvent || event.getTo() == null) {
            return;
        }
        Player player = event.getPlayer();
        if (!player.getName().equals(target) || player.isDead()
                || player.getGameMode() != GameMode.SURVIVAL || player.isInWater()) {
            // Water causes use source-variable native events until qualified.
            return;
        }
        Location from = event.getFrom();
        Location to = event.getTo();
        if (from.getWorld() != to.getWorld()) {
            return;
        }
        double dx = to.getX() - from.getX();
        double dz = to.getZ() - from.getZ();
        double blocks = Math.hypot(dx, dz);
        if (!Double.isFinite(blocks) || blocks == 0) {
            return;
        }
        // A single PlayerMoveEvent spanning >1 block could be teleport,
        // knockback or velocity not caused by deliberate locomotion.
        // Do NOT silently charge it as WALK.
        if (blocks > 1.0) {
            getLogger().warning("M02_DEV_MOTION_UNCLASSIFIED displacement=" + blocks);
            return;
        }
        EntityExhaustionEvent.ExhaustionReason reason =
            player.isSprinting() ? EntityExhaustionEvent.ExhaustionReason.SPRINT :
            player.isSneaking() ? EntityExhaustionEvent.ExhaustionReason.CROUCH :
            EntityExhaustionEvent.ExhaustionReason.WALK;
        Rule rule = rules.get(reason);
        if (rule == null) {
            getLogger().severe("missing movement rule; disabling plugin");
            Bukkit.getPluginManager().disablePlugin(this);
            return;
        }
        // The separate prospective tick-ledger DEV charges physical sampled
        // displacement in meterS50Tick, so event path is witness-only here.
        // Never bill a native event AND its tick chord twice.
        double charge = s50TickMeterArmed ? 0.0
            : blocks * (rule.standard * rule.multiplier + rule.additional);
        if (!Double.isFinite(charge) || charge < 0 || charge > Float.MAX_VALUE) {
            getLogger().severe("invalid movement billing; disabling plugin");
            Bukkit.getPluginManager().disablePlugin(this);
            return;
        }
        double after = player.getExhaustion() + charge;
        if (!Double.isFinite(after) || after > Float.MAX_VALUE) {
            Bukkit.getPluginManager().disablePlugin(this);
            return;
        }
        player.setExhaustion((float) after);
        observedMotionPackets++;
        observedMotionBlocks += blocks;
        chargedMotionExhaustion += charge;
        if (observedMotionPackets <= 300) {
            getLogger().info("M02_DEV_MOTION id=" + observedMotionPackets
                + " reason=" + reason + " blocks=" + blocks
                + " billed=" + charge
                + " cumulative_blocks=" + observedMotionBlocks
                + " cumulative_billed=" + chargedMotionExhaustion
                + " from_x=" + from.getX() + " from_y=" + from.getY()
                + " from_z=" + from.getZ()
                + " to_x=" + to.getX() + " to_y=" + to.getY()
                + " to_z=" + to.getZ()
                + " world_full_time=" + player.getWorld().getFullTime()
                + " world=" + player.getWorld().getUID()
                + " marker_id=" + s50Marker);
        }
    }

    @EventHandler(priority = EventPriority.HIGHEST, ignoreCancelled = true)
    public void onExhaustion(EntityExhaustionEvent event) {
        if (!(event.getEntity() instanceof Player player)
                || !player.getName().equals(target)) {
            return;
        }
        Rule rule = rules.get(event.getExhaustionReason());
        if (rule == null) {
            getLogger().severe("unregistered event; plugin disabled");
            Bukkit.getPluginManager().disablePlugin(this);
            return;
        }
        try {
            float nativeValue = event.getExhaustion();
            // Actual Paper move events do not correspond 1:1 to centimetres.
            // For land locomotion, cancel this event's vanilla charge and
            // charge measured displacement exactly once in PlayerMoveEvent.
            // Dynamic water events preserve their original native basis.
            boolean landMotion = !player.isInWater()
                && (event.getExhaustionReason() == EntityExhaustionEvent.ExhaustionReason.WALK
                || event.getExhaustionReason() == EntityExhaustionEvent.ExhaustionReason.CROUCH
                || event.getExhaustionReason() == EntityExhaustionEvent.ExhaustionReason.SPRINT);
            float applied = landMotion ? 0.0f : (float) rule.perEvent(nativeValue);
            event.setExhaustion(applied);
            modifiedEvents++;
            if (event.getExhaustionReason() == EntityExhaustionEvent.ExhaustionReason.WALK) {
                observedWalkEvents++;
            }
            if (event.getExhaustionReason() == EntityExhaustionEvent.ExhaustionReason.SPRINT) {
                observedSprintEvents++;
            }
            if (modifiedEvents <= 300) {
                getLogger().info("M02_DEV_EVENT id=" + modifiedEvents
                    + " reason=" + event.getExhaustionReason()
                    + " original=" + nativeValue + " replaced=" + applied);
            }
        } catch (RuntimeException ex) {
            getLogger().severe("invalid event; plugin disabled: " + ex.getMessage());
            Bukkit.getPluginManager().disablePlugin(this);
        }
    }
}
