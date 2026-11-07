package io.github.rinsakamo.loot;

import org.bukkit.Bukkit;
import org.bukkit.Input;
import org.bukkit.Location;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.player.PlayerInputEvent;
import org.bukkit.plugin.java.JavaPlugin;
import org.bukkit.util.Vector;

/**
 * D7-B opt-in, passive Paper MAIN THREAD observer.
 *
 * Samples Paper's last RECEIVED movement inputs and actual player position/
 * velocity once per server scheduler tick. A PlayerInputEvent marks an
 * observed input update; last-reported inputs alone are NOT packet delivery,
 * server-effective release or a proof of physical STOP. Neither this class
 * nor its logs ever grant EAT, issue an Action or change world physics.
 */
final class D7PaperServerTicks implements Listener {
    private static final int MAX_TICK_ROWS = 8192;
    private static final int MAX_EVENTS = 512;

    private final JavaPlugin plugin;
    private final String target;
    private int rows = 0;
    private int events = 0;
    private boolean capped = false;
    private boolean active = true;

    D7PaperServerTicks(JavaPlugin plugin, String target) {
        this.plugin = plugin;
        this.target = target;
    }

    void start() {
        Bukkit.getPluginManager().registerEvents(this, plugin);
        Bukkit.getScheduler().runTaskTimer(plugin, this::sample, 1L, 1L);
        plugin.getLogger().info("RSELF_D7_PAPER_READY source=PAPER_SERVER_MAIN_THREAD_V1"
                + " interval_ticks=1 max_rows=" + MAX_TICK_ROWS
                + " mode=read_only eat_authority=none");
    }

    void stop() {
        active = false;
        plugin.getLogger().info("RSELF_D7_PAPER_STOP total_ticks=" + rows
                + " input_events=" + events + " truncated=" + capped
                + " eat_authority=none");
    }

    private static String bits(Input input) {
        // Fixed lexical order; no input values invented for missing reads.
        return "forward=" + input.isForward()
                + " back=" + input.isBackward()
                + " left=" + input.isLeft()
                + " right=" + input.isRight()
                + " jump=" + input.isJump()
                + " sprint=" + input.isSprint()
                + " sneak=" + input.isSneak();
    }

    private void sample() {
        if (!active) return;
        Player player = Bukkit.getPlayerExact(target);
        if (player == null || !player.isOnline() || player.isDead()) return;
        if (rows >= MAX_TICK_ROWS) {
            if (!capped) {
                capped = true;
                plugin.getLogger().severe("RSELF_D7_PAPER_TRUNCATED"
                        + " limit=" + MAX_TICK_ROWS
                        + " source=PAPER_SERVER_MAIN_THREAD_V1");
            }
            return;
        }
        // All operations are observations on Paper's one authoritative server
        // thread. This is NOT a timestamp-correlated S49 Action completion.
        int tick = Bukkit.getCurrentTick();
        Input input = player.getCurrentInput();
        Location pos = player.getLocation();
        Vector velocity = player.getVelocity();
        rows += 1;
        plugin.getLogger().info("RSELF_D7_PAPER_TICK"
                + " source=PAPER_SERVER_MAIN_THREAD_V1"
                + " ordinal=" + rows
                + " tick=" + tick
                + " player=" + player.getUniqueId()
                + " world=" + player.getWorld().getUID()
                + " x=" + pos.getX() + " y=" + pos.getY()
                + " z=" + pos.getZ()
                + " vx=" + velocity.getX() + " vy=" + velocity.getY()
                + " vz=" + velocity.getZ()
                + " ground=" + player.isOnGround()
                + " " + bits(input));
    }

    @EventHandler(priority = EventPriority.MONITOR)
    public void onInput(PlayerInputEvent event) {
        if (!active || !target.equals(event.getPlayer().getName())) return;
        if (events >= MAX_EVENTS) {
            if (!capped) {
                capped = true;
                plugin.getLogger().severe("RSELF_D7_PAPER_TRUNCATED"
                        + " limit_events=" + MAX_EVENTS
                        + " source=PAPER_SERVER_MAIN_THREAD_V1");
            }
            return;
        }
        events += 1;
        plugin.getLogger().info("RSELF_D7_PAPER_INPUT_EVENT"
                + " source=PAPER_SERVER_MAIN_THREAD_V1"
                + " ordinal=" + events
                + " tick=" + Bukkit.getCurrentTick()
                + " player=" + event.getPlayer().getUniqueId()
                + " world=" + event.getPlayer().getWorld().getUID()
                + " " + bits(event.getInput()));
    }
}
