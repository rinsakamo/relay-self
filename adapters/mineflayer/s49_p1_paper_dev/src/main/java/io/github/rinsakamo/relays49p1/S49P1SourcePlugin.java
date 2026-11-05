package io.github.rinsakamo.relays49p1;

import org.bukkit.Bukkit;
import org.bukkit.Location;
import org.bukkit.command.Command;
import org.bukkit.command.CommandSender;
import org.bukkit.command.ConsoleCommandSender;
import org.bukkit.entity.Player;
import org.bukkit.entity.Zombie;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.entity.EntityDamageByEntityEvent;
import org.bukkit.event.entity.EntityDamageEvent;
import org.bukkit.event.player.PlayerAnimationEvent;
import org.bukkit.event.player.PlayerInteractEvent;
import org.bukkit.event.player.PlayerMoveEvent;
import org.bukkit.event.player.PlayerTeleportEvent;
import org.bukkit.event.player.PlayerVelocityEvent;
import org.bukkit.plugin.java.JavaPlugin;

/** Isolated read-only Paper source for one original S49 action and REST intent.
 *  Records a CALLBACK-BOUNDED census, not independently certified full ticks.
 *  No P1 state write, fatigue recovery, hunger modification or Action authority.
 */
public final class S49P1SourcePlugin extends JavaPlugin implements Listener {
    private static final String TARGET = "RelaySelf";
    private static final String TAG = "RelaySelfAttackTarget";
    private boolean dev = false;
    private boolean armed = false;
    private boolean started = false;
    private boolean stopped = false;
    private String nonce = "NONE";
    private String world = "NONE";
    private long priorTick = -1;
    private long total = 0;
    private long fightCount = 0;
    private long moveCount = 0;
    private double moveDistance = 0;
    private long swingCount = 0;
    private long interactCount = 0;
    private long velocityCount = 0;
    private long teleportCount = 0;
    private long playerDamageCount = 0;
    private long sourceFaults = 0;
    private int tickBudget = 480;
    private String pendingAction = null;

    @Override
    public void onEnable() {
        saveDefaultConfig();
        if (!getConfig().getBoolean("dev-enabled", false)) {
            getLogger().info("S49P1_DISABLED_DEFAULT");
            return;
        }
        int configuredTicks = getConfig().getInt("max-ticks", -1);
        if (!TARGET.equals(getConfig().getString("target-player"))
                || (configuredTicks != 480 && configuredTicks != 1200)
                || !Bukkit.getMinecraftVersion().equals("1.21.8")) {
            throw new IllegalStateException("wrong source profile");
        }
        tickBudget = configuredTicks;
        Bukkit.getPluginManager().registerEvents(this, this);
        dev = true;
        Bukkit.getScheduler().runTaskTimer(this, this::tickRead, 1L, 1L);
        getLogger().info("S49P1_READY source=CALLBACK_BOUNDED_READ_ONLY");
    }

    private Player player() {
        Player p = Bukkit.getPlayerExact(TARGET);
        return p != null && p.isOnline() && !p.isDead() ? p : null;
    }

    private boolean matches(Player p) {
        return armed && p != null && TARGET.equals(p.getName())
            && p.getWorld().getUID().toString().equals(world);
    }

    @Override
    public boolean onCommand(CommandSender sender, Command command, String alias, String[] args) {
        if (!dev || !(sender instanceof ConsoleCommandSender)
                || args.length < 1 || args.length > 3
                || !args[0].matches("[a-z0-9]{12,32}")) {
            return false;
        }
        String cmd = command.getName().toLowerCase(java.util.Locale.ROOT);
        Player p = player();
        if (p == null) return false;
        if (cmd.equals("s49p1start")) {
            if (args.length != 1) return false;
            if (started || stopped || armed) return false;
            started = true;
            armed = true;
            nonce = args[0];
            world = p.getWorld().getUID().toString();
            priorTick = Bukkit.getCurrentTick();
            getLogger().info("S49P1_START nonce=" + nonce
                + " world=" + world + " tick=" + priorTick
                + " player=" + p.getUniqueId()
                + " coverage=SERVER_TICK_CALLBACK_NOT_FULL_TICK");
            return true;
        }
        if (!armed || !nonce.equals(args[0]) || !matches(p)) return false;
        if (cmd.equals("s49p1action")) {
            // Read-only S49 lifecycle marker. It cannot issue/authorize MOVE,
            // assert physical input release, or provide a P1 WAIT witness.
            if (args.length != 3 || !args[2].matches("[a-z0-9-]{1,64}")) {
                return false;
            }
            if (args[1].equals("begin")) {
                if (pendingAction != null) return false;
                pendingAction = args[2];
            } else if (args[1].equals("closed")) {
                if (!args[2].equals(pendingAction)) return false;
                pendingAction = null;
            } else {
                return false;
            }
            getLogger().info("S49P1_ACTION nonce=" + nonce
                + " world=" + world + " tick=" + Bukkit.getCurrentTick()
                + " index=" + total + " phase=" + args[1]
                + " action=" + args[2]);
            return true;
        }
        if (cmd.equals("s49p1choice")) {
            if (args.length != 2
                    || !(args[1].equals("WAIT") || args[1].equals("REST"))) return false;
            getLogger().info("S49P1_CHOICE nonce=" + nonce
                + " world=" + world + " tick=" + Bukkit.getCurrentTick()
                + " index=" + total + " selected=" + args[1]);
            return true;
        }
        if (args.length != 1) return false;
        if (cmd.equals("s49p1rest")) {
            getLogger().info("S49P1_REST nonce=" + nonce
                + " world=" + world + " tick=" + Bukkit.getCurrentTick()
                + " index=" + total);
            return true;
        }
        if (cmd.equals("s49p1stop")) {
            if (pendingAction != null) return false;
            armed = false;
            stopped = true;
            getLogger().info("S49P1_STOP nonce=" + nonce
                + " world=" + world + " tick=" + Bukkit.getCurrentTick()
                + " index=" + total + " faults=" + sourceFaults
                + " coverage=SERVER_TICK_CALLBACK_NOT_FULL_TICK");
            return true;
        }
        return false;
    }

    private void tickRead() {
        if (!armed) return;
        Player p = player();
        if (p == null || !matches(p)) {
            sourceFaults++;
            armed = false;
            getLogger().severe("S49P1_SOURCE_FAULT reason=NO_PLAYER_OR_WORLD");
            return;
        }
        long tick = Bukkit.getCurrentTick();
        if (tick <= priorTick) return;
        if (tick != priorTick + 1 || total >= tickBudget) {
            sourceFaults++;
            armed = false;
            getLogger().severe("S49P1_SOURCE_FAULT reason=GAPPED_OR_OVERFLOW");
            return;
        }
        Location pos = p.getLocation();
        total++;
        getLogger().info("S49P1_TICK nonce=" + nonce
            + " world=" + world + " tick=" + tick + " index=" + total
            + " x=" + pos.getX() + " y=" + pos.getY() + " z=" + pos.getZ()
            + " move_events=" + moveCount + " move_distance=" + moveDistance
            + " fight_events=" + fightCount + " swing_events=" + swingCount
            + " interact_events=" + interactCount
            + " velocity_events=" + velocityCount
            + " teleport_events=" + teleportCount
            + " player_damage_events=" + playerDamageCount
            + " sprint=" + p.isSprinting() + " sneak=" + p.isSneaking()
            + " swimming=" + p.isSwimming());
        moveCount = 0;
        moveDistance = 0;
        fightCount = 0;
        swingCount = 0;
        interactCount = 0;
        velocityCount = 0;
        teleportCount = 0;
        playerDamageCount = 0;
        priorTick = tick;
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
    public void onMove(PlayerMoveEvent e) {
        if (!matches(e.getPlayer()) || e.getTo() == null) return;
        Location from = e.getFrom(), to = e.getTo();
        if (!from.getWorld().equals(to.getWorld())) {
            teleportCount++;
            return;
        }
        double d = from.distance(to);
        if (Double.isFinite(d) && d > 0.000001) {
            moveCount++;
            moveDistance += d;
        }
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
    public void onAttack(EntityDamageByEntityEvent e) {
        if (!(e.getDamager() instanceof Player p)
                || !matches(p)
                || !(e.getEntity() instanceof Zombie z)
                || !z.getScoreboardTags().contains(TAG)) return;
        fightCount++;
        getLogger().info("S49P1_FIGHT nonce=" + nonce
            + " world=" + world + " tick=" + Bukkit.getCurrentTick()
            + " attacker=" + p.getUniqueId() + " target=" + z.getUniqueId()
            + " damage=" + e.getFinalDamage());
    }

    @EventHandler(priority = EventPriority.MONITOR)
    public void onSwing(PlayerAnimationEvent e) {
        if (matches(e.getPlayer())) swingCount++;
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
    public void onInteract(PlayerInteractEvent e) {
        if (matches(e.getPlayer())) interactCount++;
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
    public void onVelocity(PlayerVelocityEvent e) {
        if (matches(e.getPlayer())) velocityCount++;
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
    public void onTeleport(PlayerTeleportEvent e) {
        if (matches(e.getPlayer())) teleportCount++;
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
    public void onPlayerDamage(EntityDamageEvent e) {
        if (e.getEntity() instanceof Player p && matches(p)) playerDamageCount++;
    }
}
