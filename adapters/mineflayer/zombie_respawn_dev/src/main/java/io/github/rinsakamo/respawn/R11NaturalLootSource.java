package io.github.rinsakamo.respawn;

import java.util.ArrayDeque;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import org.bukkit.Bukkit;
import org.bukkit.Location;
import org.bukkit.Material;
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
 * R11 read-only natural sunlight/loot/pickup witnesses for one managed zombie.
 *
 * ItemSpawnEvent has no authoritative cause/parent death UUID. Any location-
 * and-tick association is labeled PROXIMITY_ONLY, never a causal proof. An
 * EntityPickupItemEvent is NOT evidence of an inventory increment; only native
 * follow-up inventory can establish that. Nothing here changes the World or
 * issues a Self Action.
 */
final class R11NaturalLootSource implements Listener {
    private record Death(UUID world, UUID zombie, long tick,
            Location position, int rottenCount) {}
    private record NearbyItem(UUID world, UUID zombie, UUID item, int count) {}

    private final JavaPlugin plugin;
    private final String selfName;
    private final ArrayDeque<Death> deaths = new ArrayDeque<>();
    private final Map<UUID, NearbyItem> candidateItems = new HashMap<>();

    R11NaturalLootSource(JavaPlugin plugin, String selfName) {
        this.plugin = plugin;
        this.selfName = selfName;
    }

    void start() {
        Bukkit.getPluginManager().registerEvents(this, plugin);
        plugin.getLogger().info("RSELF_R11_LOOT_SOURCE_READY"
                + " source=PAPER_PASSIVE_MANAGED_DEATH_AND_ITEM_EVENTS"
                + " world_mutation=NONE pickup_action=NONE");
    }

    void recordManagedZombieDeath(EntityDeathEvent event, long tick) {
        Zombie zombie = (Zombie) event.getEntity();
        UUID world = zombie.getWorld().getUID();
        UUID id = zombie.getUniqueId();
        int rotten = 0;
        for (ItemStack stack : event.getDrops()) {
            if (stack.getType() == Material.ROTTEN_FLESH) {
                rotten += stack.getAmount();
            }
        }
        String lastCause = zombie.getLastDamageCause() == null
                ? "UNKNOWN" : zombie.getLastDamageCause().getCause().name();
        plugin.getLogger().info("RSELF_R11_MANAGED_DEATH"
                + " source=PAPER_ENTITY_DEATH_MONITOR"
                + " world=" + world + " zombie=" + id
                + " tick=" + tick + " time=" + zombie.getWorld().getTime()
                + " last_damage_cause=" + lastCause
                + " killer=" + (zombie.getKiller() == null
                    ? "UNKNOWN" : zombie.getKiller().getUniqueId())
                + " rotten_flesh_drop_count=" + rotten
                + " drop_source=PAPER_DEATH_DROPS_NOT_ITEM_SPAWN");
        deaths.addLast(new Death(world, id, tick, zombie.getLocation().clone(), rotten));
        // Bounded, read-only source cache; does not affect vanilla spawned items.
        while (deaths.size() > 16) deaths.removeFirst();
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
    public void onItemSpawn(ItemSpawnEvent event) {
        Item item = event.getEntity();
        if (item.getItemStack().getType() != Material.ROTTEN_FLESH) return;
        long tick = Bukkit.getCurrentTick();
        for (Death source : deaths) {
            if (source.rottenCount() <= 0
                    || !source.world().equals(item.getWorld().getUID())
                    || tick < source.tick() || tick > source.tick() + 2
                    || source.position().distanceSquared(item.getLocation()) > 9.0) {
                continue;
            }
            UUID id = item.getUniqueId();
            int count = item.getItemStack().getAmount();
            // No item-UUID cross-action authority or forced item movement.
            candidateItems.put(id, new NearbyItem(
                    source.world(), source.zombie(), id, count));
            plugin.getLogger().info("RSELF_R11_ROTTEN_ITEM_SPAWN"
                    + " source=PAPER_ITEM_SPAWN"
                    + " world=" + source.world() + " zombie=" + source.zombie()
                    + " item=" + id + " tick=" + tick + " count=" + count
                    + " death_link=PROXIMITY_AND_TICK_ONLY"
                    + " inventory_delta=NOT_ATTESTED");
            break;
        }
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
    public void onSelfPickup(EntityPickupItemEvent event) {
        if (!(event.getEntity() instanceof Player self)
                || !selfName.equals(self.getName())) return;
        NearbyItem source = candidateItems.get(event.getItem().getUniqueId());
        if (source == null
                || !source.world().equals(self.getWorld().getUID())) return;
        plugin.getLogger().info("RSELF_R11_ROTTEN_PICKUP_EVENT"
                + " source=PAPER_ENTITY_PICKUP_EVENT"
                + " world=" + source.world() + " zombie=" + source.zombie()
                + " item=" + source.item() + " player=" + self.getUniqueId()
                + " tick=" + Bukkit.getCurrentTick()
                + " item_count_at_event=" + event.getItem().getItemStack().getAmount()
                + " inventory_delta=NOT_ATTESTED"
                + " self_action=NOT_ISSUED_BY_WITNESS");
        // A future independent native inventory delta must certify uptake.
        candidateItems.remove(source.item());
    }
}
