package io.github.rinsakamo.p0b;

import java.util.UUID;
import org.bukkit.Bukkit;
import org.bukkit.entity.Entity;
import org.bukkit.entity.Player;
import org.bukkit.entity.Zombie;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.entity.EntityDamageByEntityEvent;
import org.bukkit.event.entity.EntityDeathEvent;
import org.bukkit.event.entity.CreatureSpawnEvent;
import org.bukkit.event.player.PlayerJoinEvent;
import org.bukkit.plugin.java.JavaPlugin;

/** Passive disposable-world observation; never issues an Action or attributes one. */
public final class Recorder extends JavaPlugin implements Listener {
    private long ordinal;
    @Override public void onEnable() {
        Bukkit.getPluginManager().registerEvents(this, this);
        getLogger().info("P0B_READY source=PAPER_MONITOR");
    }
    @EventHandler(priority = EventPriority.MONITOR)
    public void spawn(CreatureSpawnEvent event) {
        if (!(event.getEntity() instanceof Zombie z)) return;
        var p = z.getLocation();
        getLogger().info("P0B_SPAWN tick=" + Bukkit.getCurrentTick() + " world="
            + z.getWorld().getUID() + " victim=" + z.getUniqueId() + " health=" + z.getHealth()
            + " x=" + p.getX() + " y=" + p.getY() + " z=" + p.getZ()
            + " difficulty=" + z.getWorld().getDifficulty() + " cancelled=" + event.isCancelled());
    }
    @EventHandler(priority = EventPriority.MONITOR)
    public void join(PlayerJoinEvent event) {
        var p = event.getPlayer();
        getLogger().info("P0B_PLAYER tick=" + Bukkit.getCurrentTick() + " world="
            + p.getWorld().getUID() + " actor=" + p.getUniqueId() + " name=" + p.getName());
    }
    @EventHandler(priority = EventPriority.MONITOR)
    public void damage(EntityDamageByEntityEvent event) {
        if (!(event.getEntity() instanceof Zombie z)) return;
        Entity attacker = event.getDamager();
        String id = "damage-" + (++ordinal);
        int tick = Bukkit.getCurrentTick();
        UUID world = z.getWorld().getUID();
        UUID victim = z.getUniqueId();
        double before = z.getHealth();
        getLogger().info("P0B_DAMAGE event=" + id + " tick=" + tick + " world=" + world
            + " victim=" + victim + " attacker=" + attacker.getUniqueId()
            + " cause=" + event.getCause() + " before=" + before
            + " final_damage=" + event.getFinalDamage() + " cancelled=" + event.isCancelled());
        Bukkit.getScheduler().runTask(this, () -> {
            String health = z.isValid() && !z.isDead() ? Double.toString(z.getHealth()) : "UNKNOWN";
            getLogger().info("P0B_AFTER event=" + id + " tick=" + Bukkit.getCurrentTick()
                + " world=" + world + " victim=" + victim + " health=" + health);
        });
    }
    @EventHandler(priority = EventPriority.MONITOR)
    public void death(EntityDeathEvent event) {
        if (!(event.getEntity() instanceof Zombie z)) return;
        Player killer = z.getKiller();
        getLogger().info("P0B_DEATH event=death-" + (++ordinal) + " tick=" + Bukkit.getCurrentTick()
            + " world=" + z.getWorld().getUID() + " victim=" + z.getUniqueId()
            + " killer=" + (killer == null ? "UNKNOWN" : killer.getUniqueId())
            + " health=" + z.getHealth() + " damage_link=UNKNOWN");
    }
}
