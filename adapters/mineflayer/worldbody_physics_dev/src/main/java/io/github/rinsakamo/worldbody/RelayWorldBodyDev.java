package io.github.rinsakamo.worldbody;

import org.bukkit.Bukkit;
import org.bukkit.Location;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.player.PlayerMoveEvent;
import org.bukkit.event.player.PlayerQuitEvent;
import org.bukkit.plugin.java.JavaPlugin;

/**
 * Isolated DEV physical WorldBody. This is server-side authority, not a
 * SelfBody signal, a P1 model, or an Action issuer. Only the Paper server
 * mutates actual fatigue and movement ability. No commands, HTTP APIs,
 * config-settable rates, or Self-facing fatigue getter exist.
 *
 * The constants below are externally specified World laws for one disposable
 * World, not assumptions that Self may choose during cognition.
 */
public final class RelayWorldBodyDev extends JavaPlugin implements Listener {
    private static final String TARGET = "RelaySelf";
    private static final double MOVE_FATIGUE_PER_METRE = 2.0;
    private static final double STILL_RECOVERY_PER_SERVER_TICK = 0.003;
    private static final double SLOW_AT = 0.25;
    private static final double NORMAL_AGAIN_AT = 0.05;
    private static final float NORMAL_WALK_SPEED = 0.20f;
    private static final float SLOW_WALK_SPEED = 0.08f;
    private static final double MOVE_EPSILON = 0.005;
    private static final double MAX_ONE_EVENT_HORIZONTAL_MOVEMENT = 1.0;

    private boolean enabledForDev = false;
    private boolean initialized = false;
    private double fatigue = 0;
    private double horizontalThisTick = 0;
    private boolean slowed = false;
    private long priorTick = -1;
    private String world = "NONE";
    private String owner = "NONE";

    @Override
    public void onEnable() {
        saveDefaultConfig();
        if (!getConfig().getBoolean("dev-enabled", false)) {
            getLogger().info("WORLDBODY_DISABLED_DEFAULT");
            return;
        }
        if (!TARGET.equals(getConfig().getString("target-player"))
                || !Bukkit.getMinecraftVersion().equals("1.21.8")) {
            throw new IllegalStateException("unqualified WorldBody DEV World");
        }
        enabledForDev = true;
        Bukkit.getPluginManager().registerEvents(this, this);
        Bukkit.getScheduler().runTaskTimer(this, this::worldTick, 1L, 1L);
        getLogger().info("WORLDBODY_READY world_rules=FIXED_IN_SERVER_CODE"
            + " self_write_surface=NONE physical_effect=WALK_SPEED");
    }

    private Player target() {
        Player p = Bukkit.getPlayerExact(TARGET);
        return p != null && p.isOnline() && !p.isDead() ? p : null;
    }

    private void worldTick() {
        if (!enabledForDev) return;
        Player p = target();
        if (p == null) {
            if (initialized) {
                getLogger().info("WORLDBODY_DETACHED tick=" + Bukkit.getCurrentTick());
                initialized = false;
                horizontalThisTick = 0;
                priorTick = -1;
            }
            return;
        }
        long now = Bukkit.getCurrentTick();
        if (!initialized) {
            world = p.getWorld().getUID().toString();
            owner = p.getUniqueId().toString();
            fatigue = 0;
            slowed = false;
            horizontalThisTick = 0;
            p.setWalkSpeed(NORMAL_WALK_SPEED);
            initialized = true;
            priorTick = now - 1;
            getLogger().info("WORLDBODY_ATTACH world=" + world
                + " player=" + owner + " tick=" + now
                + " initial_walk_speed=" + NORMAL_WALK_SPEED);
        }
        if (!p.getWorld().getUID().toString().equals(world)
                || !p.getUniqueId().toString().equals(owner)
                || now != priorTick + 1) {
            getLogger().severe("WORLDBODY_SOURCE_FAULT reason=WORLD_OR_TICK_CHANGED");
            enabledForDev = false;
            return;
        }
        double travelled = horizontalThisTick;
        horizontalThisTick = 0;
        if (travelled >= MOVE_EPSILON) {
            fatigue = Math.min(1.0, fatigue + travelled * MOVE_FATIGUE_PER_METRE);
        } else {
            fatigue = Math.max(0.0, fatigue - STILL_RECOVERY_PER_SERVER_TICK);
        }
        if (!slowed && fatigue >= SLOW_AT) {
            slowed = true;
            p.setWalkSpeed(SLOW_WALK_SPEED);
            getLogger().info("WORLDBODY_EFFECT world=" + world
                + " player=" + owner + " tick=" + now
                + " change=DEGRADED actual_walk_speed=" + p.getWalkSpeed());
        } else if (slowed && fatigue <= NORMAL_AGAIN_AT) {
            slowed = false;
            p.setWalkSpeed(NORMAL_WALK_SPEED);
            getLogger().info("WORLDBODY_EFFECT world=" + world
                + " player=" + owner + " tick=" + now
                + " change=RECOVERED actual_walk_speed=" + p.getWalkSpeed());
        }
        if (now % 5 == 0 || travelled >= MOVE_EPSILON) {
            // Operator-only server truth log, NEVER a SelfBody input.
            getLogger().info("WORLDBODY_INTERNAL world=" + world
                + " player=" + owner + " tick=" + now
                + " moved_m=" + travelled
                + " truth_fatigue=" + fatigue
                + " slowed=" + slowed
                + " actual_walk_speed=" + p.getWalkSpeed());
        }
        priorTick = now;
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
    public void onMove(PlayerMoveEvent e) {
        if (!enabledForDev || !initialized
                || !TARGET.equals(e.getPlayer().getName()) || e.getTo() == null
                || !e.getPlayer().getUniqueId().toString().equals(owner)) return;
        Location from = e.getFrom(), to = e.getTo();
        if (from.getWorld() == null || to.getWorld() == null
                || !from.getWorld().equals(to.getWorld())) return;
        double x = to.getX() - from.getX();
        double z = to.getZ() - from.getZ();
        double distance = Math.hypot(x, z);
        // Reject operator teleport-like displacements; never count them as work.
        if (Double.isFinite(distance) && distance >= MOVE_EPSILON
                && distance <= MAX_ONE_EVENT_HORIZONTAL_MOVEMENT) {
            horizontalThisTick += distance;
        }
    }

    @EventHandler
    public void onQuit(PlayerQuitEvent e) {
        if (TARGET.equals(e.getPlayer().getName())) {
            e.getPlayer().setWalkSpeed(NORMAL_WALK_SPEED);
            initialized = false;
        }
    }

    @Override
    public void onDisable() {
        Player p = target();
        if (p != null) p.setWalkSpeed(NORMAL_WALK_SPEED);
    }
}
