package io.github.rinsakamo.relaydashdev;

import java.util.UUID;
import org.bukkit.Bukkit;
import org.bukkit.Input;
import org.bukkit.NamespacedKey;
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

/** Ephemeral Paper 1.21.8 DEV: never issues S Action or touches M0/P1 state. */
public final class RelayDashDevPlugin extends JavaPlugin implements Listener {
    private final NamespacedKey modifierKey = new NamespacedKey("relaydev", "forward_dash");
    private Player subject;
    private UUID subjectId;
    private BukkitTask monitor;
    private boolean used;
    private boolean armed;
    private boolean active;
    private int powerPercent;
    private int maxTicks;
    private int elapsedTicks;
    private int appliedTicks;

    @Override
    public void onEnable() {
        Bukkit.getPluginManager().registerEvents(this, this);
        getLogger().info("RELAY_DASH_READY DEV_ONLY authority=NONE");
    }

    @Override
    public boolean onCommand(
        CommandSender sender, Command command, String label, String[] args
    ) {
        if (!(sender instanceof ConsoleCommandSender) || !Bukkit.isPrimaryThread()) {
            getLogger().warning("RELAY_DASH_DENIED console_only");
            return true;
        }
        if (args.length == 1 && args[0].equals("off")) {
            stop("OPERATOR_OFF");
            return true;
        }
        if (args.length != 4 || !args[0].equals("arm") || used || armed) {
            getLogger().warning("RELAY_DASH_DENIED invalid_or_reused");
            return true;
        }
        try {
            UUID playerId = UUID.fromString(args[1]);
            int power = Integer.parseInt(args[2]);
            int limit = Integer.parseInt(args[3]);
            Player candidate = Bukkit.getPlayer(playerId);
            if (candidate == null || !candidate.isOnline() || candidate.isDead()
                    || !candidate.getName().equals("RelaySelf")
                    || power < 1 || power > 100 || limit < 1 || limit > 400) {
                getLogger().warning("RELAY_DASH_DENIED invalid_subject_or_limits");
                return true;
            }
            AttributeInstance speed = candidate.getAttribute(Attribute.MOVEMENT_SPEED);
            if (speed == null || speed.getModifier(modifierKey) != null) {
                getLogger().warning("RELAY_DASH_DENIED foreign_modifier");
                return true;
            }
            subject = candidate;
            subjectId = playerId;
            powerPercent = power;
            maxTicks = limit;
            elapsedTicks = 0;
            appliedTicks = 0;
            used = true;  // one-shot, consumed before starting any task
            armed = true;
            active = false;
            getLogger().info("RELAY_DASH_ARM player=" + playerId
                + " power=" + power + " max_ticks=" + limit + " dev_only=true");
            monitor = Bukkit.getScheduler().runTaskTimer(this, this::step, 1L, 1L);
        } catch (IllegalArgumentException error) {
            getLogger().warning("RELAY_DASH_DENIED malformed_arguments");
        }
        return true;
    }

    private static boolean forwardSprintOnly(Player player) {
        Input input = player.getCurrentInput();
        return input != null && input.isForward() && input.isSprint()
            && !input.isBackward() && !input.isLeft() && !input.isRight()
            && !input.isSneak() && !input.isJump() && player.isSprinting();
    }

    private void step() {
        if (!armed || subject == null) {
            stop("OWNER_LOST");
            return;
        }
        elapsedTicks++;
        if (subject.isDead() || !subject.isOnline()
                || !subject.getUniqueId().equals(subjectId)
                || elapsedTicks > maxTicks) {
            stop("EXPIRED_OR_OWNER_LOST");
            return;
        }
        if (!forwardSprintOnly(subject)) {
            // BEFORE activation allow input propagation up to ten server ticks.
            if (!active && elapsedTicks <= 10) {
                return;
            }
            stop("NON_FORWARD_OR_STOP");
            return;
        }
        AttributeInstance speed = subject.getAttribute(Attribute.MOVEMENT_SPEED);
        if (speed == null) {
            stop("MISSING_SPEED_ATTRIBUTE");
            return;
        }
        if (!active) {
            // MULTIPLY_SCALAR_1 applies at the total resulting attribute value.
            // Nominal RUN velocity multiplier 1 + 0.5 * power, to be measured.
            double gain = 0.5 * powerPercent / 100.0;
            speed.addTransientModifier(new AttributeModifier(
                modifierKey, gain, AttributeModifier.Operation.MULTIPLY_SCALAR_1
            ));
            active = true;
            getLogger().info("RELAY_DASH_APPLIED tick=" + subject.getWorld().getFullTime()
                + " modifier=" + gain + " base=" + speed.getBaseValue());
        }
        appliedTicks++;
        getLogger().info("RELAY_DASH_TICK tick=" + subject.getWorld().getFullTime()
            + " x=" + subject.getLocation().getX()
            + " z=" + subject.getLocation().getZ()
            + " input_forward_sprint=true");
    }

    private void stop(String reason) {
        if (monitor != null) {
            monitor.cancel();
            monitor = null;
        }
        if (subject != null) {
            AttributeInstance speed = subject.getAttribute(Attribute.MOVEMENT_SPEED);
            if (speed != null) {
                speed.removeModifier(modifierKey);
            }
        }
        if (armed) {
            getLogger().info("RELAY_DASH_DONE reason=" + reason
                + " elapsed_ticks=" + elapsedTicks
                + " applied_ticks=" + appliedTicks
                + " modifier_removed=true");
        }
        armed = false;
        active = false;
        subject = null;
        subjectId = null;
    }

    @EventHandler
    public void onQuit(PlayerQuitEvent event) {
        if (subjectId != null && subjectId.equals(event.getPlayer().getUniqueId())) {
            stop("PLAYER_QUIT");
        }
    }

    @Override
    public void onDisable() {
        stop("PLUGIN_DISABLED");
    }
}
