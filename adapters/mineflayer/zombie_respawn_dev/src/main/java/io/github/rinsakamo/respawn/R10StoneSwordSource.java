package io.github.rinsakamo.respawn;

import java.util.UUID;
import org.bukkit.Bukkit;
import org.bukkit.Material;
import org.bukkit.NamespacedKey;
import org.bukkit.entity.Entity;
import org.bukkit.entity.Player;
import org.bukkit.entity.Zombie;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.entity.EntityDamageByEntityEvent;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.PlayerInventory;
import org.bukkit.plugin.java.JavaPlugin;
import org.bukkit.persistence.PersistentDataType;

/**
 * R10-only disposable World starting equipment + passive Paper combat observer.
 *
 * The single stone sword is a declared operator-provided INITIAL EQUIPMENT
 * exception, not survival crafting or a newly learned Self Action. Existing
 * original S49 remains the only issuer of native ATTACK.
 *
 * Paper's damage event is authoritative for damage being applied by its
 * server, but its own event has no cryptographic S49 Action-ID mapping;
 * exact cross-source Action attribution remains UNATTESTED.
 */
final class R10StoneSwordSource implements Listener {
    static final String EQUIPMENT_MARK = "RSELF_R10_INITIAL_STONE_SWORD";
    static final String ZOMBIE_MARK = "RSELF_R10_ZOMBIE_DAMAGE";
    static final String SELF_MARK = "RSELF_R10_SELF_DAMAGE";
    static final String POST_MARK = "RSELF_R10_DAMAGE_AFTER";

    private final JavaPlugin plugin;
    private final String playerName;
    private final NamespacedKey managedKey;
    private UUID ownerId;
    private UUID worldId;
    private int damageOrdinal;
    private boolean equipped;

    R10StoneSwordSource(JavaPlugin plugin, String playerName, NamespacedKey managedKey) {
        this.plugin = plugin;
        this.playerName = playerName;
        this.managedKey = managedKey;
    }

    void start() {
        Bukkit.getPluginManager().registerEvents(this, plugin);
        plugin.getLogger().info("RSELF_R10_SOURCE_READY"
                + " source=PAPER_MAIN_THREAD_INITIAL_EQUIPMENT_AND_DAMAGE"
                + " sword_count=1 stage=BEFORE_INITIAL_ZOMBIE"
                + " original_S49_authority=UNCHANGED");
    }

    /** Only permitted on first real Paper player attach, prior to first spawn. */
    void equipFirstJoin(Player player) {
        PlayerInventory inventory = player.getInventory();
        boolean pristine = true;
        for (ItemStack stack : inventory.getContents()) {
            if (stack != null && !stack.getType().isAir()) pristine = false;
        }
        if (
            equipped || !pristine || player.isDead() || !player.isOnline()
            || !playerName.equals(player.getName())
            || player.getWorld() == null
        ) {
            throw new IllegalStateException("R10_INITIAL_SWORD_UNQUALIFIED");
        }
        inventory.setItemInMainHand(new ItemStack(Material.STONE_SWORD, 1));
        ItemStack hand = inventory.getItemInMainHand();
        if (hand.getType() != Material.STONE_SWORD || hand.getAmount() != 1) {
            throw new IllegalStateException("R10_INITIAL_SWORD_NOT_EQUIPPED");
        }
        ownerId = player.getUniqueId();
        worldId = player.getWorld().getUID();
        equipped = true;
        plugin.getLogger().info(EQUIPMENT_MARK
                + " world=" + worldId
                + " player=" + ownerId
                + " tick=" + Bukkit.getCurrentTick()
                + " item=STONE_SWORD count=1 hand=MAIN_HAND"
                + " source=PAPER_OPERATOR_INITIAL_ONLY"
                + " physics=VANILLA no_auto_attack=true");
    }

    private boolean target(Player player, Entity other) {
        return equipped && ownerId != null && worldId != null
            && ownerId.equals(player.getUniqueId())
            && worldId.equals(player.getWorld().getUID())
            && worldId.equals(other.getWorld().getUID());
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
    public void onDamage(EntityDamageByEntityEvent event) {
        if (!equipped || damageOrdinal >= 4096) return;
        Player self;
        Entity victim = event.getEntity();
        Entity attacker = event.getDamager();
        boolean onZombie;
        if (victim instanceof Zombie zombie && attacker instanceof Player player
                && zombie.getPersistentDataContainer().has(
                        managedKey, PersistentDataType.BYTE)
                && playerName.equals(player.getName())
                && target(player, victim)) {
            self = player;
            onZombie = true;
        } else if (victim instanceof Player player
                && playerName.equals(player.getName())
                && attacker instanceof Zombie zombie
                && zombie.getPersistentDataContainer().has(
                        managedKey, PersistentDataType.BYTE)
                && target(player, zombie)) {
            self = player;
            onZombie = false;
        } else {
            return;
        }

        int ordinal = ++damageOrdinal;
        int tick = Bukkit.getCurrentTick();
        UUID victimId = victim.getUniqueId();
        String label = onZombie ? ZOMBIE_MARK : SELF_MARK;
        double before = onZombie ? ((Zombie) victim).getHealth() : self.getHealth();
        String mainHand = self.getInventory().getItemInMainHand().getType().name();
        plugin.getLogger().info(label
                + " source=PAPER_ENTITY_DAMAGE_MONITOR"
                + " ordinal=" + ordinal
                + " world=" + worldId
                + " player=" + ownerId
                + " victim=" + victimId
                + " attacker=" + attacker.getUniqueId()
                + " tick=" + tick
                + " cause=" + event.getCause().name()
                + " main_hand=" + mainHand
                + " health_before=" + before
                + " final_damage=" + event.getFinalDamage()
                + " cancelled=false"
                + " s49_action_id=NOT_ATTESTED");
        Bukkit.getScheduler().runTask(plugin, () -> {
            String after;
            if (!victim.isValid() || victim.isDead()) {
                after = "NOT_LIVING";
            } else {
                after = Double.toString(
                    onZombie ? ((Zombie) victim).getHealth() : self.getHealth());
            }
            plugin.getLogger().info(POST_MARK
                    + " source=PAPER_NEXT_MAIN_THREAD_TICK"
                    + " ordinal=" + ordinal
                    + " world=" + worldId
                    + " victim=" + victimId
                    + " event_tick=" + tick
                    + " observed_tick=" + Bukkit.getCurrentTick()
                    + " health_after=" + after
                    + " s49_action_id=NOT_ATTESTED");
        });
    }
}
