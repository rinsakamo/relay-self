package io.github.rinsakamo.worldbody;

import org.bukkit.Bukkit;
import org.bukkit.Input;
import org.bukkit.Location;
import org.bukkit.command.Command;
import org.bukkit.command.CommandSender;
import org.bukkit.command.ConsoleCommandSender;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.entity.EntityDamageByEntityEvent;
import org.bukkit.event.player.PlayerAnimationEvent;
import org.bukkit.event.player.PlayerInputEvent;
import org.bukkit.event.player.PlayerInteractEvent;
import org.bukkit.event.player.PlayerMoveEvent;
import org.bukkit.event.player.PlayerQuitEvent;
import org.bukkit.event.player.PlayerTeleportEvent;
import org.bukkit.plugin.java.JavaPlugin;

/**
 * Paper DEV application of *the original P1 physical cap*, not of #738's
 * experimental 2.0/m, 0.003/tick, hysteresis or 0.35 factor.
 *
 * All laws/rates are fixed in P1WorldTickGateDev (pinned Python P1 owner).
 * Server console markers are a bounded original S49 action-lifecycle witness
 * only, never a MOVE issuer, a new skill or a license to modify physical law.
 *
 * WARNING: Player.getCurrentInput() and event callbacks provide a
 * server-local DEV full-tick-candidate, NOT independently attested S/R
 * SourceBoundTick. Source gaps fail closed; this is NOT R qualification.
 */
final class P1PaperPhysicalRuntimeDev implements Listener {
    private static final String TARGET = "RelaySelf";
    private static final double EPSILON = 0.000001;
    private static final double MAX_EVENT_BLOCKS = 1.0;

    private final JavaPlugin plugin;
    private P1WorldTickGateDev engine;
    private String world = null;
    private String playerId = null;
    private String nonce = null;
    private String pendingAction = null;
    private long lastTick = -1;
    private double acceptedThisTick = 0.0;
    private boolean ownerMoveWasOpen = false;
    private boolean inputWasActive = false;
    private boolean inputAtPreviousEdge = false;
    private boolean nonMoveActivity = false;
    private boolean sourceFault = false;
    private int fightEvents = 0;
    private int committed = 0;
    private int creditedWait = 0;
    private int observedMove = 0;
    private int observedFight = 0;
    private int capApplied = 0;
    private Location previousLocation = null;
    private boolean stopped = false;

    P1PaperPhysicalRuntimeDev(JavaPlugin plugin) {
        this.plugin = plugin;
    }

    private Player target() {
        Player p = Bukkit.getPlayerExact(TARGET);
        return p != null && p.isOnline() && !p.isDead() ? p : null;
    }

    private boolean matches(Player p) {
        return engine != null && !stopped && !sourceFault
                && p != null && TARGET.equals(p.getName())
                && p.getWorld().getUID().toString().equals(world)
                && p.getUniqueId().toString().equals(playerId);
    }

    private static boolean inputActive(Input i) {
        return i == null || i.isForward() || i.isBackward()
                || i.isLeft() || i.isRight() || i.isJump()
                || i.isSneak() || i.isSprint();
    }

    private void fail(String why) {
        if (!sourceFault) {
            plugin.getLogger().severe("P1WORLD_SOURCE_FAULT reason=" + why
                    + " nonce=" + nonce + " world=" + world
                    + " paper_tick=" + Bukkit.getCurrentTick());
        }
        sourceFault = true;
    }

    boolean command(CommandSender sender, Command command, String[] args) {
        if (!(sender instanceof ConsoleCommandSender)) return false;
        String kind = command.getName().toLowerCase(java.util.Locale.ROOT);
        if (kind.equals("p1bodyarm")) {
            if (args.length != 1 || engine != null || stopped
                    || !args[0].matches("[a-z0-9]{12,32}")) return false;
            Player p = target();
            if (p == null) return false;
            nonce = args[0];
            world = p.getWorld().getUID().toString();
            playerId = p.getUniqueId().toString();
            lastTick = Bukkit.getCurrentTick();
            engine = new P1WorldTickGateDev(nonce, lastTick);
            previousLocation = p.getLocation().clone();
            inputAtPreviousEdge = inputActive(p.getCurrentInput());
            inputWasActive = inputAtPreviousEdge;
            plugin.getLogger().info("P1WORLD_ATTACH nonce=" + nonce
                    + " world=" + world + " player=" + playerId
                    + " tick=" + lastTick
                    + " original_p1=" + P1WorldTickGateDev.ORIGINAL_P1_HEAD
                    + " enabled_profile_sha=" + P1WorldTickGateDev.ORIGINAL_ENABLED_PROFILE_SHA
                    + " independent_s_r_attestation=false");
            return true;
        }
        if (args.length < 1 || engine == null || stopped
                || sourceFault || !args[0].equals(nonce)) return false;
        if (kind.equals("p1bodyaction")) {
            if (args.length != 3 || !args[2].matches("[a-z0-9-]{1,64}")) {
                return false;
            }
            if (args[1].equals("begin")) {
                if (pendingAction != null) return false;
                pendingAction = args[2];
                ownerMoveWasOpen = true;
            } else if (args[1].equals("closed")) {
                if (!args[2].equals(pendingAction)) return false;
                pendingAction = null;
            } else return false;
            plugin.getLogger().info("P1WORLD_S49_ACTION nonce=" + nonce
                    + " world=" + world + " tick=" + Bukkit.getCurrentTick()
                    + " phase=" + args[1] + " action=" + args[2]);
            return true;
        }
        if (kind.equals("p1bodystop")) {
            if (args.length != 1 || pendingAction != null) return false;
            stopped = true;
            plugin.getLogger().info("P1WORLD_STOP nonce=" + nonce
                    + " world=" + world + " tick=" + Bukkit.getCurrentTick()
                    + " committed=" + committed + " move=" + observedMove
                    + " fight=" + observedFight + " wait_candidate=" + creditedWait
                    + " cap_applied=" + capApplied
                    + " independent_s_r_attestation=false");
            return true;
        }
        return false;
    }

    /** Frozen world tick, not a newly minted S49 Action or a REST credit. */
    void worldTick() {
        if (engine == null || stopped || sourceFault) return;
        Player p = target();
        long tick = Bukkit.getCurrentTick();
        if (!matches(p) || tick != lastTick + 1) {
            fail("PLAYER_WORLD_OR_TICK_GAP");
            return;
        }
        boolean currentInput = inputActive(p.getCurrentInput());
        Location now = p.getLocation();
        boolean stable = previousLocation != null
                && now.getWorld().equals(previousLocation.getWorld())
                && now.distanceSquared(previousLocation) < EPSILON * EPSILON
                && p.isOnGround()
                && p.getVelocity().lengthSquared() < 0.0001;
        double moved = acceptedThisTick;
        try {
            P1WorldTickGateDev.DevResult result = engine.accept(
                    new P1WorldTickGateDev.NativeTick(
                            nonce, tick, true, ownerMoveWasOpen,
                            inputWasActive || inputAtPreviousEdge,
                            currentInput, nonMoveActivity, stable, moved,
                            fightEvents
                    )
            );
            committed++;
            switch (result.activity()) {
                case MOVE -> observedMove++;
                case FIGHT -> observedFight++;
                case WAIT -> creditedWait++;
            }
            P1FatigueLaw.State after = result.transition().after();
            P1FatigueLaw.Capability capacity = result.transition().capacityAfter();
            // This operator-only diagnostic is never added to S49 / SelfBody
            // Present, nor may Self read true state or adjust profile rates.
            plugin.getLogger().info("P1WORLD_TICK nonce=" + nonce
                    + " world=" + world + " tick=" + tick
                    + " activity=" + result.activity()
                    + " accepted_blocks=" + moved
                    + " blocked=" + result.blockedMove()
                    + " truth_fatigue=" + after.fatigue()
                    + " p1_cap_blocks=" + capacity.maxMoveBlocksPerWorldTick()
                    + " recovered=" + result.transition().recovered()
                    + " r_qualified=false");
        } catch (IllegalArgumentException ex) {
            fail("PHYSICAL_ACTIVITY_SOURCE_UNATTESTED");
            return;
        }
        lastTick = tick;
        previousLocation = now.clone();
        acceptedThisTick = 0.0;
        ownerMoveWasOpen = pendingAction != null;
        inputAtPreviousEdge = currentInput;
        inputWasActive = currentInput;
        nonMoveActivity = false;
        fightEvents = 0;
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
    public void onInput(PlayerInputEvent e) {
        if (matches(e.getPlayer()) && inputActive(e.getInput())) {
            inputWasActive = true;
        }
    }

    @EventHandler(priority = EventPriority.HIGHEST, ignoreCancelled = true)
    public void onMove(PlayerMoveEvent e) {
        if (e instanceof PlayerTeleportEvent || !matches(e.getPlayer())
                || e.getTo() == null) return;
        Location from = e.getFrom(), to = e.getTo();
        if (from.getWorld() == null || !from.getWorld().equals(to.getWorld())) {
            fail("WORLD_TRANSFER_DURING_P1_MOTION");
            return;
        }
        double dx = to.getX() - from.getX();
        double dz = to.getZ() - from.getZ();
        double step = Math.hypot(dx, dz);
        if (!Double.isFinite(step) || step > MAX_EVENT_BLOCKS) {
            fail("UNBOUNDED_PHYSICAL_MOVEMENT");
            return;
        }
        if (step <= EPSILON) return;
        // Physical cap is P1 prospective MAX BLOCKS PER WORLD TICK, not
        // #738's 0.35 multiplier and never an Action grant.
        double max = engine.prospective().maxMoveBlocksPerWorldTick();
        double remaining = Math.max(0.0, max - acceptedThisTick);
        double allowed = Math.min(step, remaining);
        if (allowed < step) {
            double ratio = allowed / step;
            Location limited = to.clone();
            limited.setX(from.getX() + dx * ratio);
            limited.setZ(from.getZ() + dz * ratio);
            e.setTo(limited);
            capApplied++;
            plugin.getLogger().info("P1WORLD_CAP world=" + world
                    + " tick=" + Bukkit.getCurrentTick()
                    + " desired=" + step + " accepted=" + allowed
                    + " p1_cap_blocks=" + max
                    + " world_authority=true");
        }
        acceptedThisTick += allowed;
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
    public void onFight(EntityDamageByEntityEvent e) {
        if (e.getDamager() instanceof Player p && matches(p)) {
            fightEvents++;
            if (!engine.prospective().fightMechanicallyPossible()) {
                // No Self override: world rule disallows attack above fatigue.
                e.setCancelled(true);
            }
        }
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
    public void onInteract(PlayerInteractEvent e) {
        if (matches(e.getPlayer())) nonMoveActivity = true;
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
    public void onAnimation(PlayerAnimationEvent e) {
        if (matches(e.getPlayer())) nonMoveActivity = true;
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
    public void onTeleport(PlayerTeleportEvent e) {
        if (matches(e.getPlayer())) nonMoveActivity = true;
    }

    @EventHandler
    public void onQuit(PlayerQuitEvent e) {
        if (engine != null && TARGET.equals(e.getPlayer().getName()) && !stopped) {
            fail("ORIGINAL_PLAYER_QUIT_BEFORE_SOURCE_STOP");
        }
    }

    void close() {
        if (engine != null && !stopped) {
            fail("WORLD_SHUTDOWN_WITH_UNSEALED_P1_SOURCE");
        }
    }
}
