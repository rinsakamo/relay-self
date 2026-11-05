package io.github.rinsakamo.loot;

import java.util.UUID;
import org.bukkit.Bukkit;
import org.bukkit.Material;
import org.bukkit.NamespacedKey;
import org.bukkit.command.Command;
import org.bukkit.command.CommandExecutor;
import org.bukkit.command.CommandSender;
import org.bukkit.command.ConsoleCommandSender;
import org.bukkit.entity.Item;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.entity.EntityPickupItemEvent;
import org.bukkit.inventory.ItemStack;
import org.bukkit.persistence.PersistentDataType;
import org.bukkit.plugin.java.JavaPlugin;

/**
 * Independent DEV-only World fixture for a single operator-supplied item.
 * Does NOT grant Self item creation, food, movement or physical Action rights.
 */
public final class RelayPickupFixtureDev extends JavaPlugin
        implements Listener, CommandExecutor {
    private static final String TARGET = "RelaySelf";
    private NamespacedKey itemKey;
    private UUID stagedEntity;
    private UUID owner;
    private UUID world;
    private boolean enabledForDev;
    private boolean picked;

    @Override
    public void onEnable() {
        saveDefaultConfig();
        if (!getConfig().getBoolean("dev-enabled", false)) {
            getLogger().info("RSELF_LOOT_DISABLED_DEFAULT");
            return;
        }
        if (!"1.21.8".equals(Bukkit.getMinecraftVersion())
                || !TARGET.equals(getConfig().getString("target-player"))) {
            throw new IllegalStateException("unqualified isolated loot DEV World");
        }
        enabledForDev = true;
        itemKey = new NamespacedKey(this, "source_staged_item");
        getServer().getPluginManager().registerEvents(this, this);
        var command = getCommand("rselfstagefood");
        if (command == null) {
            throw new IllegalStateException("missing operator-only command");
        }
        command.setExecutor(this);
        getLogger().info("RSELF_LOOT_READY item=rotten_flesh operator_console_only=true");
    }

    @Override
    public boolean onCommand(CommandSender sender, Command command, String label, String[] args) {
        if (!enabledForDev || !(sender instanceof ConsoleCommandSender)
                || !command.getName().equalsIgnoreCase("rselfstagefood")
                || args.length != 0 || stagedEntity != null) {
            return false;
        }
        Player p = Bukkit.getPlayerExact(TARGET);
        if (p == null || !p.isOnline() || p.isDead()) return false;
        ItemStack meat = new ItemStack(Material.ROTTEN_FLESH, 1);
        Item item = p.getWorld().dropItem(p.getLocation().clone(), meat);
        item.setPickupDelay(0);
        item.getPersistentDataContainer().set(itemKey, PersistentDataType.BYTE, (byte) 1);
        stagedEntity = item.getUniqueId();
        owner = p.getUniqueId();
        world = p.getWorld().getUID();
        getLogger().info("RSELF_LOOT_STAGED world=" + world
            + " owner=" + owner + " entity=" + stagedEntity
            + " item=rotten_flesh count=1 tick=" + Bukkit.getCurrentTick()
            + " source=OPERATOR_FIXTURE_NOT_ZOMBIE_DROP");
        return true;
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
    public void onPlayerCollect(EntityPickupItemEvent event) {
        if (!enabledForDev || picked || stagedEntity == null
                || !(event.getEntity() instanceof Player player)
                || !player.getUniqueId().equals(owner)
                || !player.getWorld().getUID().equals(world)
                || !event.getItem().getUniqueId().equals(stagedEntity)
                || event.getItem().getItemStack().getType() != Material.ROTTEN_FLESH
                || !event.getItem().getPersistentDataContainer().has(
                    itemKey, PersistentDataType.BYTE)) return;
        picked = true;
        getLogger().info("RSELF_LOOT_PICKED world=" + world
            + " owner=" + owner + " entity=" + stagedEntity
            + " item=rotten_flesh count=1 tick=" + Bukkit.getCurrentTick()
            + " source=ACTUAL_PAPER_PICKUP_EVENT");
    }

    @Override
    public void onDisable() {
        enabledForDev = false;
        if (stagedEntity != null && world != null) {
            var w = Bukkit.getWorld(world);
            if (w != null) {
                var entity = Bukkit.getEntity(stagedEntity);
                if (entity != null && entity.isValid()) entity.remove();
            }
        }
        getLogger().info("RSELF_LOOT_DISABLED staged=" + (stagedEntity != null)
            + " pickup_observed=" + picked);
    }
}
