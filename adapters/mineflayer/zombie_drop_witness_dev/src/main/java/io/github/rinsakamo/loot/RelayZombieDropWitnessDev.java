package io.github.rinsakamo.loot;

import java.util.UUID;
import org.bukkit.Bukkit;
import org.bukkit.Location;
import org.bukkit.Material;
import org.bukkit.World;
import org.bukkit.entity.Item;
import org.bukkit.entity.Player;
import org.bukkit.entity.Zombie;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.entity.EntityDeathEvent;
import org.bukkit.event.entity.EntityPickupItemEvent;
import org.bukkit.event.entity.ItemSpawnEvent;
import org.bukkit.inventory.ItemStack;
import org.bukkit.plugin.java.JavaPlugin;

/**
 * READ-ONLY Paper DEV source for real zombie death drop to picked Item UUID.
 * No commands, World rule changes, forced item drops or Self-side oracle.
 * The original zombie respawn plugin independently establishes managed death.
 */
public final class RelayZombieDropWitnessDev extends JavaPlugin implements Listener {
    private static final String TARGET = "RelaySelf";

    private boolean enabledForDev;
    private UUID dead;
    private UUID worldId;
    private UUID witnessedItemId;
    private Location deathPosition;
    private int expectedCount;
    private long deathTick = -1;
    private boolean ambiguousItem;
    private boolean picked;

    @Override
    public void onEnable() {
        saveDefaultConfig();
        if (!getConfig().getBoolean("dev-enabled", false)) {
            getLogger().info("RSELF_NATURAL_DROP_DISABLED_DEFAULT");
            return;
        }
        if (!"1.21.8".equals(Bukkit.getMinecraftVersion())
                || !TARGET.equals(getConfig().getString("target-player"))) {
            throw new IllegalStateException("isolated D2 source only");
        }
        enabledForDev = true;
        Bukkit.getPluginManager().registerEvents(this, this);
        getLogger().info("RSELF_NATURAL_DROP_READY operator_only=true"
                + " force_drops=false self_permissions=none");
    }

    @EventHandler(priority = EventPriority.MONITOR)
    public void onDeath(EntityDeathEvent event) {
        if (!enabledForDev || !(event.getEntity() instanceof Zombie zombie)) return;
        if (dead != null && expectedCount > 0 && !picked) {
            getLogger().severe("RSELF_NATURAL_DROP_FAULT prior_uncollected_death="
                    + dead + " new_death=" + zombie.getUniqueId());
            enabledForDev = false;
            return;
        }
        dead = zombie.getUniqueId();
        worldId = zombie.getWorld().getUID();
        deathPosition = zombie.getLocation().clone();
        deathTick = Bukkit.getCurrentTick();
        witnessedItemId = null;
        picked = false;
        ambiguousItem = false;
        expectedCount = 0;
        for (ItemStack stack : event.getDrops()) {
            if (stack.getType() == Material.ROTTEN_FLESH) {
                expectedCount += stack.getAmount();
            }
        }
        getLogger().info("RSELF_NATURAL_DROP_DEATH world=" + worldId
                + " zombie=" + dead
                + " tick=" + deathTick + " rotten_count=" + expectedCount
                + " killer=" + (zombie.getKiller() == null
                    ? "UNKNOWN" : zombie.getKiller().getUniqueId())
                + " source=ACTUAL_PAPER_ENTITY_DEATH_DROPS"
                + " killer_is_relay_self=" + (zombie.getKiller() != null
                    && TARGET.equals(zombie.getKiller().getName())));
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
    public void onItemSpawn(ItemSpawnEvent event) {
        if (!enabledForDev || dead == null || expectedCount <= 0
                || deathPosition == null) return;
        Item item = event.getEntity();
        World world = item.getWorld();
        long tick = Bukkit.getCurrentTick();
        if (!world.getUID().equals(worldId)
                || tick < deathTick || tick > deathTick + 3
                || item.getItemStack().getType() != Material.ROTTEN_FLESH
                || item.getLocation().distanceSquared(deathPosition) > 6.25) return;
        if (witnessedItemId != null) {
            ambiguousItem = true;
            getLogger().severe("RSELF_NATURAL_DROP_FAULT ambiguous_item_count=2"
                    + " death=" + dead);
            return;
        }
        witnessedItemId = item.getUniqueId();
        getLogger().info("RSELF_NATURAL_DROP_SPAWN world=" + worldId
                + " zombie=" + dead + " item=" + witnessedItemId
                + " tick=" + tick + " rotten_count="
                + item.getItemStack().getAmount()
                + " source=ACTUAL_PAPER_ITEM_SPAWN_NEAR_DEATH");
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
    public void onPickup(EntityPickupItemEvent event) {
        if (!enabledForDev || ambiguousItem || picked
                || witnessedItemId == null || dead == null
                || !(event.getEntity() instanceof Player player)
                || !TARGET.equals(player.getName())
                || !player.getWorld().getUID().equals(worldId)
                || !event.getItem().getUniqueId().equals(witnessedItemId)
                || event.getRemaining() != 0) return;
        int count = event.getItem().getItemStack().getAmount();
        if (count <= 0 || count != expectedCount) {
            getLogger().severe("RSELF_NATURAL_DROP_FAULT count_mismatch_at_pickup");
            return;
        }
        picked = true;
        getLogger().info("RSELF_NATURAL_DROP_PICKUP world=" + worldId
                + " zombie=" + dead + " item=" + witnessedItemId
                + " player=" + player.getUniqueId()
                + " tick=" + Bukkit.getCurrentTick()
                + " rotten_count=" + count
                + " source=ACTUAL_PAPER_ITEM_PICKUP");
    }

    @Override
    public void onDisable() {
        enabledForDev = false;
        getLogger().info("RSELF_NATURAL_DROP_STOP last_death=" + dead
                + " last_pickup=" + picked + " ambiguous=" + ambiguousItem);
    }
}
