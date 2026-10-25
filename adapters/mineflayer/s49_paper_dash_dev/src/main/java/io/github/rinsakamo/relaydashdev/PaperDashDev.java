package io.github.rinsakamo.relaydashdev;

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
import org.bukkit.event.player.PlayerMoveEvent;
import org.bukkit.event.player.PlayerQuitEvent;
import org.bukkit.plugin.java.JavaPlugin;
import org.bukkit.scheduler.BukkitTask;

/**
 * Isolated, disposable Paper 1.21.8 motor *candidate* (NOT an S49 issuer).
 * Only the forward+sprint direction receives a transient 0..50% speed boost.
 * When moving sideways/backwards the DASH stance remains active while the
 * added booster is zero. Pre-existing attribute modifiers are never edited.
 * Input may be stale; observed PlayerMoveEvent can veto boost but does NOT
 * yet establish a mathematically hard per-tick World displacement ceiling.
 */
public final class PaperDashDev extends JavaPlugin implements Listener {
    private static final int MAX_ACTIVE_TICKS = 40; // bounded 2s pilot, NOT the P1 20s limit
    private boolean used = false;
    private boolean active = false;
    private boolean boostOn = false;
    private UUID subjectId;
    private UUID worldId;
    private String sessionId;
    private double requestedPower;
    private NamespacedKey speedKey;
    private BukkitTask task;
    private int activeTicks;
    private int forwardBoostTicks;
    private int cappedTicks;
    private int movementVetoes;

    @Override
    public void onEnable() {
        speedKey = new NamespacedKey(this, "forward_dash_boost_dev");
        Bukkit.getPluginManager().registerEvents(this, this);
        getLogger().info("PAPER_DASH_DEV_READY enabled="
            + getConfig().getBoolean("enabled", false) + " authority=NONE");
    }

    @Override
    public boolean onCommand(
        CommandSender sender, Command command, String label, String[] args
    ) {
        boolean start = command.getName().equalsIgnoreCase("relaydasharm");
        boolean stop = command.getName().equalsIgnoreCase("relaydashstop");
        if (!start && !stop) return false;
        if (!(sender instanceof ConsoleCommandSender) || !Bukkit.isPrimaryThread()
                || !getConfig().getBoolean("enabled", false)
                || args.length != (start ? 3 : 2) || !validId(args[0])) {
            getLogger().warning("PAPER_DASH_DEV_DENIED invalid_console_or_claim");
            return true;
        }
        UUID id;
        try {
            id = UUID.fromString(args[1]);
        } catch (IllegalArgumentException ex) {
            getLogger().warning("PAPER_DASH_DEV_DENIED invalid_uuid");
            return true;
        }
        if (!start) {
            if (!active || !id.equals(subjectId) || !args[0].equals(sessionId)) {
                getLogger().warning("PAPER_DASH_DEV_DENIED foreign_stop");
            } else {
                release("OWNER_STOP");
            }
            return true;
        }
        if (active || used) {
            getLogger().warning("PAPER_DASH_DEV_DENIED already_used");
            return true;
        }
        double power;
        try {
            power = Double.parseDouble(args[2]);
        } catch (NumberFormatException ex) {
            getLogger().warning("PAPER_DASH_DEV_DENIED invalid_power");
            return true;
        }
        Player player = Bukkit.getPlayer(id);
        if (!(power > 0.0 && power <= 1.0) || !Double.isFinite(power)
                || player == null || !player.isOnline() || player.isDead()
                || !player.getName().equals(
                    getConfig().getString("expected-player-name", "RelaySelf"))
                || !player.getUniqueId().equals(id)) {
            getLogger().warning("PAPER_DASH_DEV_DENIED invalid_power_or_player");
            return true;
        }
        AttributeInstance speed = player.getAttribute(Attribute.MOVEMENT_SPEED);
        if (speed == null || speed.getModifier(speedKey) != null) {
            getLogger().warning("PAPER_DASH_DEV_DENIED existing_or_unavailable_attribute");
            return true;
        }
        used = true;
        active = true;
        boostOn = false;
        subjectId = id;
        worldId = player.getWorld().getUID();
        sessionId = args[0];
        requestedPower = power;
        activeTicks = forwardBoostTicks = cappedTicks = movementVetoes = 0;
        getLogger().info("PAPER_DASH_DEV_ARM session_id=" + sessionId
            + " player_uuid=" + subjectId + " power=" + power
            + " authority=CONSOLE_CLAIM_ONLY");
        task = Bukkit.getScheduler().runTaskTimer(this, this::observeAndApply, 1L, 1L);
        return true;
    }

    private static boolean validId(String s) {
        return s != null && s.matches("[A-Za-z0-9][A-Za-z0-9._:-]{0,127}");
    }

    private boolean validSubject(Player player) {
        return active && player != null && player.isOnline() && !player.isDead()
            && player.getUniqueId().equals(subjectId)
            && player.getWorld().getUID().equals(worldId);
    }

    private void setBoost(Player player, boolean enabled) {
        AttributeInstance attribute = player.getAttribute(Attribute.MOVEMENT_SPEED);
        if (attribute == null) {
            throw new IllegalStateException("missing MOVEMENT_SPEED attribute");
        }
        // Own exactly one namespaced transient modifier. Never change base speed.
        AttributeModifier existing = attribute.getModifier(speedKey);
        if (existing != null) attribute.removeModifier(existing);
        if (enabled) {
            attribute.addTransientModifier(new AttributeModifier(
                speedKey, requestedPower * 0.50,
                AttributeModifier.Operation.MULTIPLY_SCALAR_1
            ));
        }
        boostOn = enabled;
    }

    private void observeAndApply() {
        Player player = Bukkit.getPlayer(subjectId);
        if (!validSubject(player) || activeTicks++ >= MAX_ACTIVE_TICKS) {
            release("OWNER_LOST_OR_MAX_TICKS");
            return;
        }
        try {
            Input input = player.getCurrentInput();
            // An absent/stale input means NO extra forward boost. On lateral,
            // back, diagonal, sneak or unknown: stay armed, use low base cap.
            boolean forwardOnly = input != null && input.isForward()
                && input.isSprint() && player.isSprinting()
                && !input.isBackward() && !input.isLeft() && !input.isRight()
                && !input.isSneak();
            setBoost(player, forwardOnly);
            if (forwardOnly) forwardBoostTicks++;
            else cappedTicks++;
        } catch (RuntimeException ex) {
            release("MOTOR_EXCEPTION");
            throw ex;
        }
    }

    @EventHandler
    public void onMove(PlayerMoveEvent event) {
        if (!active || !boostOn || !event.getPlayer().getUniqueId().equals(subjectId)
                || event.getTo() == null) return;
        // Negative control when Paper's input API fails to show a client change.
        // Facing-projected movement is a *veto*, not a proof of acceleration.
        double dx = event.getTo().getX() - event.getFrom().getX();
        double dz = event.getTo().getZ() - event.getFrom().getZ();
        double distance = Math.hypot(dx, dz);
        if (distance <= 1.0e-8) return;
        double yaw = Math.toRadians(event.getFrom().getYaw());
        double forwardProjection = (-Math.sin(yaw) * dx + Math.cos(yaw) * dz) / distance;
        if (forwardProjection < 0.85) {
            setBoost(event.getPlayer(), false);
            movementVetoes++;
            getLogger().info("PAPER_DASH_DEV_DIRECTION_VETO session_id=" + sessionId
                + " reason=side_or_back tick=" + event.getPlayer().getWorld().getFullTime());
        }
    }

    @EventHandler
    public void onQuit(PlayerQuitEvent event) {
        if (active && event.getPlayer().getUniqueId().equals(subjectId)) {
            release("PLAYER_QUIT");
        }
    }

    private void release(String reason) {
        if (!active) return;
        if (task != null) {
            task.cancel();
            task = null;
        }
        Player player = Bukkit.getPlayer(subjectId);
        if (player != null) {
            AttributeInstance attribute = player.getAttribute(Attribute.MOVEMENT_SPEED);
            if (attribute != null) {
                AttributeModifier owned = attribute.getModifier(speedKey);
                if (owned != null) attribute.removeModifier(owned);
            }
        }
        boostOn = false;
        active = false;
        getLogger().info("PAPER_DASH_DEV_RELEASE session_id=" + sessionId
            + " reason=" + reason + " sample_ticks=" + activeTicks
            + " forward_boost_ticks=" + forwardBoostTicks
            + " low_cap_ticks=" + cappedTicks + " direction_vetoes=" + movementVetoes
            + " effective_server_tick_alignment_attested=false"
            + " qualified=false");
    }

    @Override
    public void onDisable() {
        release("PLUGIN_DISABLE");
    }
}
