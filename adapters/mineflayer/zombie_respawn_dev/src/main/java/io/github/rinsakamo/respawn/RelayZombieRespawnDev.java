package io.github.rinsakamo.respawn;

import java.util.UUID;
import org.bukkit.Bukkit;
import org.bukkit.Location;
import org.bukkit.NamespacedKey;
import org.bukkit.World;
import org.bukkit.block.Block;
import org.bukkit.block.BlockFace;
import org.bukkit.entity.Player;
import org.bukkit.entity.Zombie;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.entity.EntityDeathEvent;
import org.bukkit.event.entity.PlayerDeathEvent;
import org.bukkit.event.player.PlayerJoinEvent;
import org.bukkit.event.player.PlayerQuitEvent;
import org.bukkit.persistence.PersistentDataType;
import org.bukkit.plugin.java.JavaPlugin;

/**
 * Opt-in single-zombie DEV World fixture. Death and respawn are authoritative
 * Paper events, never Action output and never data supplied to SelfBody/L0.
 * An actual Self S49 attack/kill is a separate experiment, not certified here.
 */
public final class RelayZombieRespawnDev extends JavaPlugin implements Listener {
    private static final String TARGET_PLAYER = "RelaySelf";
    private static final int RESPAWN_TICKS = 600; // fixed World rule
    private static final double SPAWN_OFFSET_X = 6.0; // fixed arena geometry

    private final RespawnCycle cycle = new RespawnCycle();
    private NamespacedKey managedKey;
    private UUID playerId;
    private Location anchor;
    private Zombie living;
    private boolean devEnabled;
    private boolean halted;
    private long deathWallNanos;

    @Override
    public void onEnable() {
        saveDefaultConfig();
        if (!getConfig().getBoolean("dev-enabled", false)) {
            getLogger().info("RSELF_RESPAWN_DISABLED_DEFAULT");
            return;
        }
        if (!"1.21.8".equals(Bukkit.getMinecraftVersion())
                || !TARGET_PLAYER.equals(getConfig().getString("target-player"))) {
            throw new IllegalStateException("respawn DEV requires pinned Paper 1.21.8/RelaySelf");
        }
        managedKey = new NamespacedKey(this, "managed_zombie");
        devEnabled = true;
        Bukkit.getPluginManager().registerEvents(this, this);
        Bukkit.getScheduler().runTaskTimer(this, this::worldTick, 1L, 1L);
        Player existing = Bukkit.getPlayerExact(TARGET_PLAYER);
        if (existing != null) Bukkit.getScheduler().runTask(this, () -> attach(existing));
        getLogger().info("RSELF_RESPAWN_READY source=PAPER_WORLD_ONLY delay_ticks="
            + RESPAWN_TICKS + " max_living=1 self_write=NONE");
    }

    @EventHandler
    public void onJoin(PlayerJoinEvent event) {
        if (!devEnabled || !TARGET_PLAYER.equals(event.getPlayer().getName())) return;
        Bukkit.getScheduler().runTask(this, () -> attach(event.getPlayer()));
    }

    private void attach(Player player) {
        if (!devEnabled || halted || !player.isOnline() || player.isDead()) return;
        if (playerId != null) {
            if (!playerId.equals(player.getUniqueId())) fail("SECOND_PLAYER_ID");
            return;
        }
        playerId = player.getUniqueId();
        anchor = player.getLocation().clone().add(SPAWN_OFFSET_X, 0, 0);
        if (!safeAnchor(anchor) || managedCount(anchor.getWorld()) != 0) {
            fail("INITIAL_ANCHOR_OR_MANAGED_ENTITY");
            return;
        }
        spawn(false, Bukkit.getCurrentTick());
    }

    @EventHandler(priority = EventPriority.MONITOR)
    public void onZombieDeath(EntityDeathEvent event) {
        if (!devEnabled || halted || !(event.getEntity() instanceof Zombie zombie)
                || !hasManagedTag(zombie)) return;
        long tick = Bukkit.getCurrentTick();
        if (!cycle.died(zombie.getWorld().getUID(), zombie.getUniqueId(), tick)) {
            fail("FOREIGN_OR_DUPLICATE_DEATH");
            return;
        }
        deathWallNanos = System.nanoTime();
        living = null;
        // Never alter drops or force rotten flesh. No claim of who killed it.
        getLogger().info("RSELF_RESPAWN_DEATH world=" + cycle.world()
            + " entity=" + zombie.getUniqueId()
            + " generation=" + cycle.generation()
            + " tick=" + tick + " due_tick=" + cycle.dueTick()
            + " paper_drops=" + event.getDrops().size()
            + " killer=" + (zombie.getKiller() == null
                ? "UNKNOWN" : zombie.getKiller().getUniqueId()));
    }

    private void worldTick() {
        if (!devEnabled || halted || anchor == null || playerId == null) return;
        Player player = Bukkit.getPlayer(playerId);
        if (player == null || !player.isOnline() || player.isDead()
                || !player.getWorld().getUID().equals(cycle.world())) {
            cleanup();
            return;
        }
        long now = Bukkit.getCurrentTick();
        if (cycle.due(player.getWorld().getUID(), now)) {
            if (!safeAnchor(anchor) || managedCount(player.getWorld()) != 0) {
                fail("DUE_ANCHOR_OR_LIVE_MANAGED_ENTITY");
                return;
            }
            spawn(true, now);
        } else if (cycle.living() != null
                && (living == null || !living.isValid() || living.isDead())) {
            // Unexpected disappearance is not an EntityDeathEvent.
            fail("MISSING_LIVING_WITHOUT_DEATH");
        }
    }

    private void spawn(boolean isRespawn, long tick) {
        if (anchor == null || !safeAnchor(anchor)) {
            fail("INVALID_SPAWN_ANCHOR");
            return;
        }
        Zombie fresh;
        try {
            fresh = anchor.getWorld().spawn(anchor, Zombie.class);
            fresh.getPersistentDataContainer().set(managedKey, PersistentDataType.BYTE, (byte) 1);
            fresh.setBaby(false);
            fresh.setAI(true);
            fresh.setInvulnerable(false);
            fresh.setShouldBurnInDay(false); // explicit fixed arena rule
            fresh.setRemoveWhenFarAway(false);
            fresh.setPersistent(true);
        } catch (RuntimeException exception) {
            fail("SPAWN_FAILED_" + exception.getClass().getSimpleName());
            return;
        }
        boolean admitted = isRespawn
            ? cycle.reborn(fresh.getWorld().getUID(), fresh.getUniqueId(), tick)
            : cycle.begin(fresh.getWorld().getUID(), fresh.getUniqueId(), tick);
        if (!admitted) {
            fresh.remove();
            fail("GENERATION_ADMISSION_REJECTED");
            return;
        }
        living = fresh;
        long elapsedMillis = isRespawn
            ? (System.nanoTime() - deathWallNanos) / 1_000_000L : -1L;
        getLogger().info((isRespawn ? "RSELF_RESPAWN_SPAWN" : "RSELF_RESPAWN_INITIAL")
            + " world=" + cycle.world() + " entity=" + fresh.getUniqueId()
            + " generation=" + cycle.generation() + " tick=" + tick
            + " death_to_spawn_wall_ms=" + elapsedMillis
            + " ai=true invulnerable=false day_burn=false");
    }

    private boolean hasManagedTag(Zombie zombie) {
        return zombie.getPersistentDataContainer().has(managedKey, PersistentDataType.BYTE);
    }

    private int managedCount(World world) {
        if (world == null) return -1;
        int count = 0;
        for (Zombie zombie : world.getEntitiesByClass(Zombie.class)) {
            if (hasManagedTag(zombie) && zombie.isValid() && !zombie.isDead()) count++;
        }
        return count;
    }

    private static boolean safeAnchor(Location location) {
        if (location == null || location.getWorld() == null) return false;
        Block feet = location.getBlock();
        return feet.isPassable() && !feet.isLiquid()
            && feet.getRelative(BlockFace.UP).isPassable()
            && feet.getRelative(BlockFace.DOWN).getType().isSolid();
    }

    private void fail(String reason) {
        halted = true;
        getLogger().severe("RSELF_RESPAWN_FAULT reason=" + reason
            + " world=" + cycle.world() + " generation=" + cycle.generation()
            + " due_tick=" + cycle.dueTick() + " new_spawns_fenced=true");
    }

    @EventHandler
    public void onQuit(PlayerQuitEvent event) {
        if (playerId != null && playerId.equals(event.getPlayer().getUniqueId())) cleanup();
    }

    @EventHandler
    public void onPlayerDeath(PlayerDeathEvent event) {
        if (playerId != null && playerId.equals(event.getEntity().getUniqueId())) cleanup();
    }

    private void cleanup() {
        if (living != null && living.isValid() && !living.isDead()) living.remove();
        living = null;
        anchor = null;
        playerId = null;
        cycle.clear();
        getLogger().info("RSELF_RESPAWN_RESET pending_discarded=true");
    }

    @Override
    public void onDisable() {
        devEnabled = false;
        cleanup();
    }
}
