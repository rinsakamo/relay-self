package io.github.rinsakamo.relays49observer;

import java.util.UUID;
import org.bukkit.Bukkit;
import org.bukkit.Input;
import org.bukkit.Location;
import org.bukkit.World;
import org.bukkit.command.Command;
import org.bukkit.command.CommandSender;
import org.bukkit.command.ConsoleCommandSender;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.player.PlayerInputEvent;
import org.bukkit.event.player.PlayerMoveEvent;
import org.bukkit.plugin.java.JavaPlugin;
import org.bukkit.scheduler.BukkitTask;

/**
 * Standalone DEV-only, console-opt-in, READ-ONLY Paper clock observer.
 *
 * The console supplies action/session IDs AFTER it believes S49 has closed.
 * These IDs are untrusted claims: Paper does NOT receive an S16 receipt.
 * Synchronous ticks are callback observations, not whole-tick inactivity.
 * This observer NEVER changes controls, World, energy, or Action authority.
 */
public final class S49WaitObserverPlugin extends JavaPlugin implements Listener {
    private static final int SAMPLE_COUNT = 8;
    private boolean used = false;
    private boolean active = false;
    private BukkitTask task;
    private String marker;
    private String action;
    private String session;
    private String observerRunId;
    private UUID playerId;
    private UUID worldId;
    private Location startingLocation;
    private long beginTick;
    private int index;

    @Override
    public void onEnable() {
        // The bundled config defaults to disabled. No scheduler on enable.
        getLogger().info("S49_DEV_OBSERVER_READY enabled="
            + getConfig().getBoolean("enabled", false)
            + " authority=NONE source=CONSOLE_CLAIM_ONLY");
    }

    @Override
    public boolean onCommand(
        CommandSender sender, Command command, String label, String[] args
    ) {
        if (!command.getName().equalsIgnoreCase("relays49observe")) {
            return false;
        }
        if (!(sender instanceof ConsoleCommandSender)
                || !Bukkit.isPrimaryThread()
                || !getConfig().getBoolean("enabled", false)
                || used || active || args.length != 3) {
            getLogger().warning("S49_OBSERVER_DENIED no_grant_or_retry");
            return true;
        }
        // Refuse spaces/control characters and log injection in claimed IDs.
        if (!validId(args[0]) || !validId(args[1])) {
            getLogger().warning("S49_OBSERVER_DENIED invalid_action_or_session");
            return true;
        }
        UUID parsedPlayer;
        try {
            parsedPlayer = UUID.fromString(args[2]);
        } catch (IllegalArgumentException ex) {
            getLogger().warning("S49_OBSERVER_DENIED invalid_player_uuid");
            return true;
        }
        Player subject = Bukkit.getPlayer(parsedPlayer);
        String expectedName = getConfig().getString(
            "expected-player-name", "RelaySelf"
        );
        if (subject == null || !subject.isOnline() || subject.isDead()
                || !subject.getUniqueId().equals(parsedPlayer)
                || !subject.getName().equals(expectedName)) {
            getLogger().warning("S49_OBSERVER_DENIED missing_or_foreign_self");
            return true;
        }
        // This is a paper-local clock. No assertion of native clear timing.
        World world = subject.getWorld();
        used = true;             // consume before publishing any source row
        active = true;
        action = args[0];
        session = args[1];
        observerRunId = UUID.randomUUID().toString();
        marker = action + "-" + session;
        playerId = parsedPlayer;
        worldId = world.getUID();
        beginTick = world.getFullTime();
        index = 0;
        startingLocation = subject.getLocation();
        try {
            // Registers passive input/motion observations before the first
            // sample; it never changes input or entity state.
            Bukkit.getPluginManager().registerEvents(this, this);
            if (!idleInput(subject.getCurrentInput())) {
                abort("SERVER_INPUT_ACTIVE_AT_START");
                return true;
            }
            getLogger().info("S49_OBSERVER_SUBJECT action_id=" + action
                + " session_id=" + session + " player_uuid=" + playerId
                + " world=" + worldId + " run_id=" + observerRunId
                + " clear_ack=UNATTESTED_CONSOLE_CLAIM");
            getLogger().info("S49_OBSERVER_SERVER_INPUT action_id=" + action
                + " session_id=" + session + " player_uuid=" + playerId
                + " world=" + worldId + " run_id=" + observerRunId
                + " tick=" + beginTick
                + " input_idle=true s49_release_causality=NOT_ATTESTED");
            getLogger().info("S49_DEV_BACK_WAIT_BEGIN " + baseFields()
                + " tick=" + beginTick + " index=0 input_idle=true");
            // Main-thread, single read-only callback per server tick.
            task = Bukkit.getScheduler().runTaskTimer(
                this, () -> observe(subject), 1L, 1L
            );
        } catch (RuntimeException ex) {
            abort("OBSERVER_START_FAILED");
            throw ex;
        }
        return true;
    }

    private static boolean idleInput(Input input) {
        // Conservative: no movement, jump, sprint, or sneak input may remain.
        return input != null && !input.isForward() && !input.isBackward()
            && !input.isLeft() && !input.isRight() && !input.isJump()
            && !input.isSprint() && !input.isSneak();
    }

    private static boolean samePosition(Location a, Location b) {
        return a != null && b != null
            && a.getWorld().getUID().equals(b.getWorld().getUID())
            && Double.compare(a.getX(), b.getX()) == 0
            && Double.compare(a.getY(), b.getY()) == 0
            && Double.compare(a.getZ(), b.getZ()) == 0;
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = false)
    public void onPlayerInput(PlayerInputEvent event) {
        if (active && event.getPlayer().getUniqueId().equals(playerId)) {
            if (!Bukkit.isPrimaryThread() || !idleInput(event.getInput())) {
                abort("SERVER_INPUT_ACTIVE_DURING_OBSERVATION");
            }
        }
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = false)
    public void onPlayerMove(PlayerMoveEvent event) {
        if (active && event.getPlayer().getUniqueId().equals(playerId)) {
            if (!Bukkit.isPrimaryThread()
                    || !samePosition(event.getFrom(), event.getTo())) {
                abort("SELF_MOVEMENT_EVENT_DURING_OBSERVATION");
            }
        }
    }

    private static boolean validId(String candidate) {
        return candidate != null
            && candidate.matches("[A-Za-z0-9_.:-]{1,96}");
    }

    private String baseFields() {
        return "marker_id=" + marker + " action_id=" + action
            + " session_id=" + session + " world=" + worldId
            + " run_id=" + observerRunId;
    }

    private void observe(Player subject) {
        try {
            if (!active || !Bukkit.isPrimaryThread()
                    || !subject.isOnline() || subject.isDead()
                    || !subject.getUniqueId().equals(playerId)
                    || !subject.getWorld().getUID().equals(worldId)) {
                abort("OWNER_OR_WORLD_CHANGED");
                return;
            }
            if (!idleInput(subject.getCurrentInput())) {
                abort("SERVER_INPUT_ACTIVE_AT_CALLBACK");
                return;
            }
            if (!samePosition(subject.getLocation(), startingLocation)) {
                abort("SELF_POSITION_CHANGED_AT_CALLBACK");
                return;
            }
            long tick = subject.getWorld().getFullTime();
            int next = index + 1;
            if (next > SAMPLE_COUNT || tick != beginTick + next) {
                abort("TICK_GAP_OR_REPLAY");
                return;
            }
            index = next;
            getLogger().info("S49_DEV_BACK_WAIT_TICK " + baseFields()
                + " tick=" + tick + " index=" + index
                + " input_idle=true");
            if (index == SAMPLE_COUNT) {
                active = false;
                cancelTask();
                getLogger().info("S49_OBSERVER_COMPLETE action_id=" + action
                    + " session_id=" + session + " player_uuid=" + playerId
                    + " world=" + worldId + " run_id=" + observerRunId
                    + " last_tick=" + tick
                    + " samples=8 authority=NONE p1_recovery=NONE");
            }
        } catch (RuntimeException ex) {
            abort("PAPER_OBSERVER_EXCEPTION");
            throw ex;
        }
    }

    private void abort(String reason) {
        if (!active) {
            return;
        }
        active = false;
        cancelTask();
        // A truncated record must never be mistaken for a sealed 8-tick set.
        getLogger().warning("S49_DEV_BACK_WAIT_ABORT " + baseFields()
            + " reason=" + reason + " samples=" + index);
    }

    private void cancelTask() {
        if (task != null) {
            task.cancel();
            task = null;
        }
    }

    @Override
    public void onDisable() {
        abort("PLUGIN_DISABLED");
        cancelTask();
        getLogger().info("S49_OBSERVER_STOPPED no_action_or_world_mutation");
    }
}
