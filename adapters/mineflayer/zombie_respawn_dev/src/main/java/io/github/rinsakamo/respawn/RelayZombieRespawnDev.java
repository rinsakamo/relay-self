package io.github.rinsakamo.respawn;

import java.util.UUID;
import org.bukkit.Bukkit;
import org.bukkit.GameRule;
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
    private boolean naturalWorldMode;
    private boolean halted;
    private long deathWallNanos;
    private TickObservationHorizon horizon;
    private R10StoneSwordSource r10StoneSwordSource;
    private R11NaturalLootSource r11NaturalLootSource;

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
        naturalWorldMode = getConfig().getBoolean("dev-natural-world-mode", false);
        boolean r10InitialSword = getConfig().getBoolean(
                "dev-r10-initial-stone-sword", false);
        boolean r11NaturalDay = getConfig().getBoolean(
                "dev-r11-natural-day", false);
        int requestedTicks = getConfig().getInt("dev-tick-endurance-ticks", 0);
        if (r11NaturalDay && (
                !naturalWorldMode || !r10InitialSword
                || !getConfig().getBoolean("dev-tick-endurance-enabled", false)
                || requestedTicks != 24000
                || getConfig().getInt("dev-tick-sample-interval", 200) != 200)) {
            throw new IllegalStateException(
                    "R11 natural day requires 24000 Paper ticks, R10 sword and 200-tick samples");
        }
        if (r10InitialSword && (
                !naturalWorldMode
                || !getConfig().getBoolean("dev-tick-endurance-enabled", false)
                || requestedTicks != (r11NaturalDay ? 24000 : 10000))) {
            throw new IllegalStateException(
                    "R10 initial sword requires natural 10000-tick or R11 24000-tick DEV World");
        }
        if (naturalWorldMode && !getConfig().getBoolean("dev-tick-endurance-enabled", false)) {
            throw new IllegalStateException("natural World requires 10000 tick horizon");
        }
        if (getConfig().getBoolean("dev-tick-endurance-enabled", false)) {
            horizon = new TickObservationHorizon(
                getConfig().getInt("dev-tick-endurance-ticks", 0),
                getConfig().getInt("dev-tick-sample-interval", 200));
        } else if (getConfig().getInt("dev-tick-endurance-ticks", 0) != 0) {
            throw new IllegalStateException("D14 horizon ticks require explicit DEV opt-in");
        }
        managedKey = new NamespacedKey(this, "managed_zombie");
        devEnabled = true;
        Bukkit.getPluginManager().registerEvents(this, this);
        if (r10InitialSword) {
            r10StoneSwordSource = new R10StoneSwordSource(this, TARGET_PLAYER, managedKey);
            r10StoneSwordSource.start();
        }
        if (r11NaturalDay) {
            r11NaturalLootSource = new R11NaturalLootSource(this, TARGET_PLAYER);
            r11NaturalLootSource.start();
        }
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
        // R3's fixed same-Y +6 anchor can land inside hillside air/stone
        // on ordinary generated terrain. In natural mode, inspect nearby
        // *unchanged* terrain and pick the first valid site; never flatten,
        // teleport Self, weaken the zombie or silently reroll this World.
        anchor = naturalWorldMode
            ? naturalAnchor(player)
            : player.getLocation().clone().add(SPAWN_OFFSET_X, 0, 0);
        if (!safeAnchor(anchor) || managedCount(anchor.getWorld()) != 0) {
            fail("INITIAL_ANCHOR_OR_MANAGED_ENTITY");
            return;
        }
        if (r11NaturalLootSource != null && !Boolean.TRUE.equals(
                player.getWorld().getGameRuleValue(GameRule.DO_DAYLIGHT_CYCLE))) {
            fail("R11_NATURAL_DAYLIGHT_CYCLE_DISABLED");
            return;
        }
        if (r10StoneSwordSource != null) {
            try {
                // One actual vanilla ItemStack, before any zombie/Action;
                // does not equip via S49 or change AI, health, drops or combat.
                r10StoneSwordSource.equipFirstJoin(player);
            } catch (IllegalStateException exception) {
                fail("R10_INITIAL_EQUIPMENT_" + exception.getMessage());
                return;
            }
        }
        if (naturalWorldMode) {
            getLogger().info("RSELF_NATURAL_ANCHOR source=PAPER_WORLD_GEOMETRY"
                + " self_x=" + player.getLocation().getBlockX()
                + " self_y=" + player.getLocation().getBlockY()
                + " self_z=" + player.getLocation().getBlockZ()
                + " zombie_x=" + anchor.getBlockX()
                + " zombie_y=" + anchor.getBlockY()
                + " zombie_z=" + anchor.getBlockZ()
                + " blocks_changed=false player_moved=false");
        }
        spawn(false, Bukkit.getCurrentTick());
        if (!halted && horizon != null) {
            horizon.begin(Bukkit.getCurrentTick());
            getLogger().info("RSELF_ENDURANCE_START world=" + cycle.world()
                + " start_tick=" + horizon.startTick()
                + " stop_tick=" + horizon.endTick()
                + " horizon_ticks=" + horizon.ticks()
                + " natural_600tick_respawns_unchanged=true"
                + daySourceSuffix(player.getWorld()));
        }
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
        if (r11NaturalLootSource != null) {
            r11NaturalLootSource.recordManagedZombieDeath(event, tick);
        }
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
            recordEarlyTerminal(player == null || !player.isOnline()
                ? "SELF_DISCONNECTED"
                : player.isDead() ? "SELF_DIED" : "WORLD_SCOPE_LOST");
            cleanup();
            return;
        }
        long now = Bukkit.getCurrentTick();
        if (horizon != null) {
            if (horizon.reached(now)) {
                horizon.finish(now);
                halted = true; // stop new spawns, do not alter vanilla drops or Self
                getLogger().info("RSELF_ENDURANCE_LIMIT world=" + cycle.world()
                    + " start_tick=" + horizon.startTick()
                    + " end_tick=" + horizon.endTick() + " observed_tick=" + now
                    + " elapsed_ticks=" + horizon.elapsed(now)
                    + " generation=" + cycle.generation()
                    + " living=" + (cycle.living() == null ? "NONE" : cycle.living())
                    + " stop_new_spawns=true no_forced_death=true"
                    + daySourceSuffix(player.getWorld()));
                return;
            }
            if (horizon.sample(now)) {
                getLogger().info("RSELF_ENDURANCE_SAMPLE world=" + cycle.world()
                    + " tick=" + now + " elapsed_ticks=" + horizon.elapsed(now)
                    + " generation=" + cycle.generation()
                    + " living=" + (cycle.living() == null ? "NONE" : cycle.living())
                    + " pending_due_tick=" + cycle.dueTick()
                    + daySourceSuffix(player.getWorld()));
            }
        }
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

    private String daySourceSuffix(World world) {
        return r11NaturalLootSource == null ? ""
            : " world_time=" + world.getTime()
            + " world_full_time=" + world.getFullTime()
            + " daylight_cycle=true";
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
            fresh.setShouldBurnInDay(naturalWorldMode); // vanilla daytime burning only in natural D14
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
            + " ai=true invulnerable=false day_burn=" + naturalWorldMode
            + " natural_world=" + naturalWorldMode);
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

    private static Location naturalAnchor(Player player) {
        Location original = player.getLocation();
        World world = original.getWorld();
        if (world == null) return null;
        int sx = original.getBlockX();
        int sy = original.getBlockY();
        int sz = original.getBlockZ();
        for (int[] offset : NaturalAnchorCandidates.offsets()) {
            // Bounded spatial search in the same World and loaded spawn area.
            // Use actual block passability and natural supporting ground.
            Location candidate = new Location(
                world, sx + offset[0] + 0.5, sy + offset[1],
                sz + offset[2] + 0.5);
            if (safeAnchor(candidate)) return candidate;
        }
        return null;
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
        if (playerId != null && playerId.equals(event.getPlayer().getUniqueId())) {
            recordEarlyTerminal("SELF_DISCONNECTED");
            cleanup();
        }
    }

    @EventHandler
    public void onPlayerDeath(PlayerDeathEvent event) {
        if (playerId != null && playerId.equals(event.getEntity().getUniqueId())) {
            recordEarlyTerminal("SELF_DIED");
            cleanup();
        }
    }

    private void recordEarlyTerminal(String reason) {
        if (horizon == null || halted || cycle.world() == null) return;
        long tick = Bukkit.getCurrentTick();
        getLogger().info("RSELF_ENDURANCE_TERMINAL world=" + cycle.world()
            + " start_tick=" + horizon.startTick()
            + " scheduled_stop_tick=" + horizon.endTick()
            + " observed_tick=" + tick
            + " elapsed_ticks=" + horizon.elapsed(tick)
            + " reason=" + reason
            + " horizon_reached=false"
            + " native_actions_inferred=none");
    }

    private void cleanup() {
        if (living != null && living.isValid() && !living.isDead()) living.remove();
        living = null;
        anchor = null;
        playerId = null;
        cycle.clear();
        horizon = null;
        getLogger().info("RSELF_RESPAWN_RESET pending_discarded=true");
    }

    @Override
    public void onDisable() {
        devEnabled = false;
        cleanup();
    }
}
