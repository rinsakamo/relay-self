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
 * The legacy console command claims a closed S49 Action. A distinct
 * pre-action command arms observation before any server-seen BACK input.
 * All console IDs remain untrusted: Paper has no authenticated S16 receipt.
 * Synchronous ticks are callback observations, not whole-tick inactivity.
 * This observer NEVER changes controls, World, energy, or Action authority.
 */
public final class S49WaitObserverPlugin extends JavaPlugin implements Listener {
    private static final int SAMPLE_COUNT = 8;
    private static final long MAX_PRE_ARM_TICKS = 240L;
    private boolean used = false;
    private boolean active = false;
    private boolean preAction = false;
    private int prePhase = 0; // 1 armed, 2 back ON, 3 back OFF/sampling
    private long preArmTick;
    private long backOnTick;
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
        boolean pre = command.getName().equalsIgnoreCase("relays49preobserve");
        if (!pre && !command.getName().equalsIgnoreCase("relays49observe")) {
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
        preAction = pre;
        prePhase = pre ? 1 : 0;
        action = args[0];
        session = args[1];
        observerRunId = UUID.randomUUID().toString();
        marker = action + "-" + session;
        playerId = parsedPlayer;
        worldId = world.getUID();
        beginTick = world.getFullTime();
        preArmTick = beginTick;
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
            if (preAction) {
                getLogger().info("S49_OBSERVER_PRE_ARM " + baseFields()
                    + " tick=" + preArmTick + " input_idle=true");
                task = Bukkit.getScheduler().runTaskTimer(
                    this, () -> observePre(subject), 1L, 1L
                );
                return true;
            }
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

    private static boolean backwardOnly(Input input) {
        return input != null && input.isBackward()
            && !input.isForward() && !input.isLeft() && !input.isRight()
            && !input.isJump() && !input.isSprint() && !input.isSneak();
    }

    private void observePre(Player subject) {
        if (!active || !preAction) {
            return;
        }
        try {
            if (!Bukkit.isPrimaryThread() || !subject.isOnline()
                    || subject.isDead() || !subject.getUniqueId().equals(playerId)
                    || !subject.getWorld().getUID().equals(worldId)) {
                abort("PRE_ACTION_OWNER_OR_WORLD_CHANGED");
                return;
            }
            long now = subject.getWorld().getFullTime();
            if (now < preArmTick || now - preArmTick > MAX_PRE_ARM_TICKS) {
                abort("PRE_ACTION_TIMEOUT_OR_CLOCK_RESET");
                return;
            }
            if (prePhase == 1) {
                if (!idleInput(subject.getCurrentInput())) {
                    abort("PRE_ACTION_UNOBSERVED_BACK_ON");
                }
                return;
            }
            if (prePhase == 2) {
                if (!backwardOnly(subject.getCurrentInput())) {
                    abort("PRE_ACTION_UNOBSERVED_BACK_OFF");
                }
                return;
            }
            if (prePhase != 3) {
                abort("PRE_ACTION_PHASE_INVALID");
                return;
            }
            // An input event may have released BACK earlier in this same
            // tick; the first stable callback must occur on a later tick.
            if (now == beginTick) {
                return;
            }
            observe(subject);
        } catch (RuntimeException ex) {
            abort("PRE_ACTION_OBSERVER_EXCEPTION");
            throw ex;
        }
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
            if (!Bukkit.isPrimaryThread()) {
                abort("INPUT_EVENT_OFF_PRIMARY_THREAD");
                return;
            }
            if (preAction && prePhase == 1) {
                if (backwardOnly(event.getInput())) {
                    backOnTick = event.getPlayer().getWorld().getFullTime();
                    if (backOnTick < preArmTick) {
                        abort("PRE_ACTION_BACK_ON_BEFORE_ARM");
                        return;
                    }
                    prePhase = 2;
                    getLogger().info("S49_OBSERVER_BACK_TRUE " + baseFields()
                        + " tick=" + backOnTick + " back=true");
                } else if (!idleInput(event.getInput())) {
                    abort("PRE_ACTION_FOREIGN_INPUT");
                }
                return;
            }
            if (preAction && prePhase == 2) {
                if (idleInput(event.getInput())) {
                    long releaseTick = event.getPlayer().getWorld().getFullTime();
                    if (releaseTick <= backOnTick) {
                        abort("PRE_ACTION_BACK_EDGE_SAME_TICK_OR_REWIND");
                        return;
                    }
                    prePhase = 3;
                    beginTick = releaseTick;
                    index = 0;
                    startingLocation = event.getPlayer().getLocation();
                    getLogger().info("S49_OBSERVER_BACK_FALSE " + baseFields()
                        + " tick=" + releaseTick + " back=false");
                    getLogger().info("S49_OBSERVER_SERVER_INPUT action_id="
                        + action + " session_id=" + session
                        + " player_uuid=" + playerId + " world=" + worldId
                        + " run_id=" + observerRunId + " tick=" + releaseTick
                        + " input_idle=true s49_release_causality=NOT_ATTESTED");
                    getLogger().info("S49_DEV_BACK_WAIT_BEGIN " + baseFields()
                        + " tick=" + beginTick + " index=0 input_idle=true");
                } else if (!backwardOnly(event.getInput())) {
                    abort("PRE_ACTION_FOREIGN_INPUT");
                }
                return;
            }
            if (!idleInput(event.getInput())) {
                abort("SERVER_INPUT_ACTIVE_DURING_OBSERVATION");
            }
        }
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = false)
    public void onPlayerMove(PlayerMoveEvent event) {
        if (active && event.getPlayer().getUniqueId().equals(playerId)) {
            // The initial S49 backward Action legitimately moves the Self.
            if (preAction && prePhase < 3) {
                return;
            }
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
