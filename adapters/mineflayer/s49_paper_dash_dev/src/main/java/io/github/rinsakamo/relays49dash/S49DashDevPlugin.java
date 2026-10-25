package io.github.rinsakamo.relays49dash;

import java.util.UUID;
import org.bukkit.Bukkit;
import org.bukkit.Input;
import org.bukkit.NamespacedKey;
import org.bukkit.World;
import org.bukkit.attribute.Attribute;
import org.bukkit.attribute.AttributeInstance;
import org.bukkit.attribute.AttributeModifier;
import org.bukkit.command.Command;
import org.bukkit.command.CommandSender;
import org.bukkit.command.ConsoleCommandSender;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.player.PlayerQuitEvent;
import org.bukkit.plugin.java.JavaPlugin;
import org.bukkit.scheduler.BukkitTask;

/**
 * Isolated Paper DEV *motor modifier*, NOT S49 Action admission.
 *
 * The owning S49 runner must independently prove an issued forward MOVE
 * before requesting arm. Console text is not authenticated Action evidence.
 * While armed, retain DASH stance during lateral/back/idle movement, but
 * only ever apply the transient +speed modifier on an unambiguous forward
 * sprint input. Unknown input fails closed to vanilla speed.
 *
 * Does NOT cap other plugins' modifiers or attest server-effective input
 * timing. One-shot disposable profile, timeout, identity checks, cleanup.
 */
public final class S49DashDevPlugin extends JavaPlugin implements Listener {
    private static final long MAX_ARM_TICKS = 80L; // one 4s DEV motor window
    private boolean consumed = false;
    private boolean armed = false;
    private boolean boosted = false;
    private Player subject;
    private UUID playerId;
    private UUID worldId;
    private String actionId;
    private String sessionId;
    private long armTick;
    private long lastTick;
    private int forwardTicks;
    private int cappedTicks;
    private double requestedPower;
    private BukkitTask task;
    private AttributeModifier modifier;

    @Override
    public void onEnable() {
        getLogger().info("S49_DASH_DEV_READY enabled="
            + getConfig().getBoolean("enabled", false)
            + " authority=NONE speed_changes=OPT_IN");
        Bukkit.getPluginManager().registerEvents(this, this);
    }

    private boolean validId(String value) {
        return value != null && value.matches("[A-Za-z0-9_.:-]{1,96}");
    }

    @Override
    public boolean onCommand(CommandSender sender, Command command,
                             String label, String[] args) {
        boolean start = command.getName().equalsIgnoreCase("relays49dasharm");
        boolean stop = command.getName().equalsIgnoreCase("relays49dashoff");
        if (!start && !stop) {
            return false;
        }
        if (!(sender instanceof ConsoleCommandSender)
                || !Bukkit.isPrimaryThread()
                || !getConfig().getBoolean("enabled", false)
                || args.length != (start ? 4 : 3)
                || !validId(args[0]) || !validId(args[1])) {
            getLogger().warning("S49_DASH_DEV_DENIED console_or_input");
            return true;
        }
        UUID uuid;
        try {
            uuid = UUID.fromString(args[2]);
        } catch (IllegalArgumentException exception) {
            getLogger().warning("S49_DASH_DEV_DENIED uuid");
            return true;
        }
        if (start) {
            arm(args, uuid);
        } else {
            if (!armed || !uuid.equals(playerId)
                    || !args[0].equals(actionId) || !args[1].equals(sessionId)) {
                getLogger().warning("S49_DASH_DEV_DENIED foreign_release");
                return true;
            }
            disarm("OWNER_RELEASE");
        }
        return true;
    }

    private void arm(String[] args, UUID uuid) {
        if (consumed || armed) {
            getLogger().warning("S49_DASH_DEV_DENIED one_shot");
            return;
        }
        double power;
        try {
            power = Double.parseDouble(args[3]);
        } catch (NumberFormatException exception) {
            getLogger().warning("S49_DASH_DEV_DENIED power");
            return;
        }
        if (!Double.isFinite(power) || power <= 0 || power > 1) {
            getLogger().warning("S49_DASH_DEV_DENIED power_out_of_range");
            return;
        }
        Player player = Bukkit.getPlayer(uuid);
        if (player == null || !player.isOnline() || player.isDead()
                || !uuid.equals(player.getUniqueId())
                || !player.getName().equals(
                    getConfig().getString("expected-player-name", "RelaySelf")
                ) || player.getAttribute(Attribute.MOVEMENT_SPEED) == null) {
            getLogger().warning("S49_DASH_DEV_DENIED invalid_player");
            return;
        }
        NamespacedKey key = new NamespacedKey(this, "forward_dash_only");
        AttributeInstance speed = player.getAttribute(Attribute.MOVEMENT_SPEED);
        if (speed.getModifier(key) != null) {
            getLogger().warning("S49_DASH_DEV_DENIED colliding_modifier");
            return;
        }
        consumed = true;
        armed = true;
        boosted = false;
        subject = player;
        playerId = uuid;
        worldId = player.getWorld().getUID();
        actionId = args[0];
        sessionId = args[1];
        requestedPower = power;
        armTick = player.getWorld().getFullTime();
        lastTick = armTick;
        forwardTicks = 0;
        cappedTicks = 0;
        modifier = new AttributeModifier(
            key, 0.5 * requestedPower, AttributeModifier.Operation.MULTIPLY_SCALAR_1
        );
        task = Bukkit.getScheduler().runTaskTimer(this, this::sample, 1L, 1L);
        getLogger().info("S49_DASH_DEV_ARM action_id=" + actionId
            + " session_id=" + sessionId + " player_uuid=" + playerId
            + " world=" + worldId + " tick=" + armTick
            + " power=" + power + " authority=NONE");
    }

    private boolean safeSubject() {
        return subject != null && subject.isOnline() && !subject.isDead()
            && playerId.equals(subject.getUniqueId())
            && worldId.equals(subject.getWorld().getUID())
            && subject.getName().equals(
                getConfig().getString("expected-player-name", "RelaySelf")
            );
    }

    private void sample() {
        if (!armed) {
            return;
        }
        if (!Bukkit.isPrimaryThread() || !safeSubject()) {
            disarm("SUBJECT_OR_WORLD_CHANGED");
            return;
        }
        World world = subject.getWorld();
        long tick = world.getFullTime();
        // Paper may schedule the first callback in the same World tick
        // as arm(); that does not represent an elapsed World tick.
        if (tick == armTick && lastTick == armTick) {
            return;
        }
        if (tick <= lastTick || tick - armTick > MAX_ARM_TICKS) {
            disarm("TICK_GAP_OR_MAX_WINDOW");
            return;
        }
        lastTick = tick;
        Input input = subject.getCurrentInput();
        // Never assume Paper input and Mineflayer physics ticks align.
        // Ambiguous/unknown, side+forward, reverse or idle => NO DASH BONUS.
        boolean forwardOnly = input != null && input.isForward()
            && !input.isBackward() && !input.isLeft() && !input.isRight()
            && !input.isSneak() && !input.isJump()
            && (input.isSprint() || subject.isSprinting());
        if (!setBoost(forwardOnly)) {
            disarm("MODIFIER_SET_FAILED");
            return;
        }
        if (forwardOnly) {
            forwardTicks++;
        } else {
            cappedTicks++;
        }
        getLogger().info("S49_DASH_DEV_TICK action_id=" + actionId
            + " session_id=" + sessionId + " tick=" + tick
            + " index=" + (forwardTicks + cappedTicks)
            + " input_forward_only=" + forwardOnly
            + " modifier_applied=" + boosted
            + " dash_stance_active=true"
            + " input_edge_attested=false");
    }

    private boolean setBoost(boolean shouldBoost) {
        AttributeInstance speed = subject == null ? null
            : subject.getAttribute(Attribute.MOVEMENT_SPEED);
        if (speed == null || modifier == null) {
            return false;
        }
        try {
            if (shouldBoost && !boosted) {
                if (speed.getModifier(modifier.getKey()) != null) {
                    return false;
                }
                speed.addTransientModifier(modifier);
                boosted = true;
            } else if (!shouldBoost && boosted) {
                speed.removeModifier(modifier);
                boosted = false;
            }
            return true;
        } catch (RuntimeException exception) {
            getLogger().warning("S49_DASH_DEV_MODIFIER_FAILURE "
                + exception.getClass().getSimpleName());
            return false;
        }
    }

    private void disarm(String reason) {
        if (!armed) {
            return;
        }
        armed = false;
        if (task != null) {
            task.cancel();
            task = null;
        }
        if (subject != null && modifier != null) {
            AttributeInstance speed = subject.getAttribute(Attribute.MOVEMENT_SPEED);
            if (speed != null && speed.getModifier(modifier.getKey()) != null) {
                try {
                    speed.removeModifier(modifier);
                } catch (RuntimeException exception) {
                    getLogger().severe("S49_DASH_DEV_CLEANUP_UNCONFIRMED "
                        + exception.getClass().getSimpleName());
                }
            }
        }
        boosted = false;
        getLogger().info("S49_DASH_DEV_COMPLETE action_id=" + actionId
            + " session_id=" + sessionId + " reason=" + reason
            + " forward_boost_ticks=" + forwardTicks
            + " other_direction_or_ambiguous_ticks=" + cappedTicks
            + " modifier_applied=false"
            + " authority=NONE P1_APPLIED=false M0_POSTED=false");
    }

    @EventHandler
    public void onQuit(PlayerQuitEvent event) {
        if (armed && event.getPlayer().getUniqueId().equals(playerId)) {
            disarm("PLAYER_QUIT");
        }
    }

    @Override
    public void onDisable() {
        disarm("PLUGIN_DISABLED");
        getLogger().info("S49_DASH_DEV_STOPPED");
    }
}
