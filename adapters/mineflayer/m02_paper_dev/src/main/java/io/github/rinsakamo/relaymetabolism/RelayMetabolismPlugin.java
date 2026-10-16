package io.github.rinsakamo.relaymetabolism;

import java.util.Arrays;
import java.util.EnumMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import org.bukkit.Bukkit;
import org.bukkit.GameMode;
import org.bukkit.Location;
import org.bukkit.World;
import org.bukkit.block.Block;
import org.bukkit.command.Command;
import org.bukkit.command.CommandSender;
import org.bukkit.command.ConsoleCommandSender;
import org.bukkit.configuration.ConfigurationSection;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.entity.EntityExhaustionEvent;
import org.bukkit.event.player.PlayerMoveEvent;
import org.bukkit.event.player.PlayerTeleportEvent;
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
                if (p.getWorld().getFullTime() <= s50ObserveUntil) {
                    Location loc = p.getLocation();
                    getLogger().info("S50_DEV_TICK marker_id=" + s50Marker
                        + " world=" + p.getWorld().getUID()
                        + " tick=" + p.getWorld().getFullTime()
                        + " packets=" + observedMotionPackets
                        + " blocks=" + observedMotionBlocks
                        + " billed=" + chargedMotionExhaustion
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


    /** Server-side timestamp for DEV S50 control-command boundaries only.
     *  No player, R grant, Action authorization or physiology mutation.
     *  Console-only command: the marker cannot assert when server inputs
     *  actually changed, only when a phase boundary was observed on Paper.
     */
    @Override
    public boolean onCommand(CommandSender sender, Command command,
                             String label, String[] args) {
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
        } else if (!s50Marker.equals(args[0])) {
            return false;
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
        double charge = blocks * (rule.standard * rule.multiplier + rule.additional);
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
