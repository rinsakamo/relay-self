package io.github.rinsakamo.relaymetabolism;

import java.util.Arrays;
import java.util.EnumMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import org.bukkit.Bukkit;
import org.bukkit.configuration.ConfigurationSection;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.entity.EntityExhaustionEvent;
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
    private String target;
    private long appliedTicks = 0;
    private long modifiedEvents = 0;

    private record Rule(String unit, double standard, boolean nativeValue,
                        double multiplier, double additional, boolean enabled) {
        double perEvent(double nativeExhaustion) {
            // Movement reasons are per centimetre in the Paper event API.
            // A numeric standard is in exhaustion per block; native baseline
            // is already the original per-event exhaustion amount.
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
            Bukkit.getScheduler().runTaskTimer(this, () -> {
                Player p = Bukkit.getPlayerExact(target);
                if (p == null || !p.isOnline() || p.isDead()) {
                    return;
                }
                double delta = basal.perEvent(0);
                double next = p.getExhaustion() + delta;
                // Minecraft exhaustion is internally bounded. The player API
                // clamps when necessary; never decrease native exhaustion.
                if (Double.isFinite(next) && next <= Float.MAX_VALUE) {
                    p.setExhaustion((float) next);
                    appliedTicks++;
                } else {
                    getLogger().severe("invalid basal exhaustion; disabling plugin");
                    Bukkit.getPluginManager().disablePlugin(this);
                }
                if (appliedTicks % 100 == 0) {
                    getLogger().info("M02_DEV_BODY sampled_tick=" + appliedTicks
                        + " player=" + target + " food=" + p.getFoodLevel()
                        + " saturation=" + p.getSaturation()
                        + " health=" + p.getHealth()
                        + " exhaustion=" + p.getExhaustion()
                        + " events=" + modifiedEvents);
                }
            }, 1L, 1L);
            getLogger().warning("M02_DEV_ONLY: candidate physics, not qualified by R/V");
        } catch (RuntimeException ex) {
            getLogger().severe("M02_DEV_DISABLED: " + ex.getMessage());
            Bukkit.getPluginManager().disablePlugin(this);
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
            event.setExhaustion((float) rule.perEvent(event.getExhaustion()));
            modifiedEvents++;
        } catch (RuntimeException ex) {
            getLogger().severe("invalid event; plugin disabled: " + ex.getMessage());
            Bukkit.getPluginManager().disablePlugin(this);
        }
    }
}
