package io.github.rinsakamo.p0b;

import java.util.Comparator;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import org.bukkit.Bukkit;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.player.PlayerJoinEvent;
import org.bukkit.event.player.PlayerQuitEvent;
import org.bukkit.plugin.java.JavaPlugin;

/**
 * #860 Stage22 passive MAIN-THREAD witness for independent Paper World presence.
 *
 * Does not send player commands, authorize Self Action, or know a native
 * session ID. Its records are independent of Mineflayer probe/Action streams.
 * A Paper MOVE record alone is NOT proof which native Action caused it.
 */
final class ResidentPresenceWitness implements Listener {
    private record Sample(UUID worldId, double x, double y, double z, int tick) {}
    private final JavaPlugin plugin;
    private final UUID bootId = UUID.randomUUID();
    private final Map<UUID, Sample> last = new HashMap<>();

    ResidentPresenceWitness(JavaPlugin plugin) {
        this.plugin = plugin;
    }

    void start() {
        Bukkit.getPluginManager().registerEvents(this, plugin);
        Bukkit.getScheduler().runTaskTimer(plugin, this::samplePlayers, 1L, 5L);
        plugin.getLogger().info("P0D_RESIDENT_READY boot=" + bootId
            + " source=PAPER_MAIN_THREAD version=1");
    }

    private void emit(String kind, Player player) {
        if (!Bukkit.isPrimaryThread()) {
            throw new IllegalStateException("P0D presence witness left main thread");
        }
        var loc = player.getLocation();
        int tick = Bukkit.getCurrentTick();
        plugin.getLogger().info(
            "P0D_RESIDENT event=" + kind
            + " boot=" + bootId
            + " tick=" + tick
            + " world=" + player.getWorld().getUID()
            + " actor=" + player.getUniqueId()
            + " name=" + player.getName()
            + " x=" + loc.getX()
            + " y=" + loc.getY()
            + " z=" + loc.getZ()
            + " source=PAPER_MAIN_THREAD"
        );
        last.put(player.getUniqueId(), new Sample(
            player.getWorld().getUID(), loc.getX(), loc.getY(), loc.getZ(), tick
        ));
    }

    @EventHandler(priority = EventPriority.MONITOR)
    public void joined(PlayerJoinEvent event) {
        emit("JOIN", event.getPlayer());
    }

    @EventHandler(priority = EventPriority.MONITOR)
    public void quit(PlayerQuitEvent event) {
        emit("QUIT", event.getPlayer());
        last.remove(event.getPlayer().getUniqueId());
    }

    private void samplePlayers() {
        if (!Bukkit.isPrimaryThread()) {
            throw new IllegalStateException("P0D presence sample left main thread");
        }
        Bukkit.getOnlinePlayers().stream()
            .sorted(Comparator.comparing(p -> p.getUniqueId().toString()))
            .forEach(player -> {
                Sample before = last.get(player.getUniqueId());
                var at = player.getLocation();
                int tick = Bukkit.getCurrentTick();
                if (before == null || !before.worldId().equals(player.getWorld().getUID())) {
                    emit("PRESENT", player);
                } else {
                    double dx = at.getX() - before.x();
                    double dy = at.getY() - before.y();
                    double dz = at.getZ() - before.z();
                    double movementSquared = dx * dx + dy * dy + dz * dz;
                    if (movementSquared >= 0.04) {
                        emit("MOVE", player);
                    } else if (tick - before.tick() >= 40) {
                        emit("PRESENT", player);
                    }
                }
            });
    }
}
