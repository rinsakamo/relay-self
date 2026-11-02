package io.github.rinsakamo.relayzombie;

import com.destroystokyo.paper.event.entity.EntityRemoveFromWorldEvent;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.UUID;
import java.util.regex.Pattern;
import org.bukkit.Bukkit;
import org.bukkit.Location;
import org.bukkit.World;
import org.bukkit.command.Command;
import org.bukkit.command.CommandSender;
import org.bukkit.command.ConsoleCommandSender;
import org.bukkit.entity.Zombie;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.plugin.java.JavaPlugin;
import org.bukkit.scheduler.BukkitTask;

/**
 * DEV-only read-only Paper same-Zombie source.
 *
 * This logs Paper main-thread server ticks and positions, but NOT native
 * Mineflayer observation correlation or full entity-lifetime qualification.
 * Any actual client timestamp/seq mapping requires a separate audited join.
 * It never summons, despawns, teleports, damages or commands any entity.
 */
public final class ZombieTickWitnessPlugin extends JavaPlugin implements Listener {
    private static final Pattern TOKEN = Pattern.compile("[A-Za-z0-9._:-]{1,48}");
    private static final int LAST_OFFSET = 30;
    private static final int FIRST_PREDICTION_OFFSET = 10;
    private BukkitTask sampler;
    private Zombie zombie;
    private UUID uuid;
    private UUID worldUuid;
    private int entityId;
    private int baselineTick;
    private int lastTick;
    private int lastOffset;
    private String marker;
    private String session;
    private int samples;
    private boolean enabled;
    private boolean prospectiveCheap;
    private boolean forecastFrozen;
    private double firstX;
    private double firstZ;

    @Override
    public void onEnable() {
        saveDefaultConfig();
        enabled = getConfig().getBoolean("dev-enabled", false)
            && getConfig().getBoolean("zombie-tick-readonly-dev", false)
            && "1.21.8".equals(getConfig().getString("minecraft-version"));
        prospectiveCheap = enabled
            && getConfig().getBoolean("zombie-prospective-cheap-dev", false);
        if (!enabled) {
            getLogger().info("L_ZOMBIE_DISABLED_DEFAULT_NO_WORLD_ACCESS");
            return;
        }
        Bukkit.getPluginManager().registerEvents(this, this);
        getLogger().info("L_ZOMBIE_READONLY_READY ticks=31 forecast=10_to_30");
    }

    @Override
    public void onDisable() {
        if (sampler != null) {
            closeWindow("DISABLED");
        }
        enabled = false;
    }

    private void closeWindow(String state) {
        if (sampler != null) {
            sampler.cancel();
            sampler = null;
        }
        if (marker != null) {
            getLogger().info("L_ZOMBIE_END_V1 marker=" + marker
                + " session=" + session + " result=" + state
                + " samples=" + samples + " last_offset=" + lastOffset);
        }
        zombie = null;
        uuid = null;
        worldUuid = null;
        marker = null;
        session = null;
    }

    @EventHandler
    public void removed(EntityRemoveFromWorldEvent event) {
        if (sampler != null && uuid != null
                && uuid.equals(event.getEntity().getUniqueId())) {
            closeWindow("ENTITY_REMOVED");
        }
    }

    private List<Zombie> selectOne() {
        List<Zombie> found = new ArrayList<>();
        for (World world : Bukkit.getWorlds()) {
            for (Zombie candidate : world.getEntitiesByClass(Zombie.class)) {
                if (!candidate.isDead() && candidate.isValid()) {
                    found.add(candidate);
                    if (found.size() > 1) {
                        return found;
                    }
                }
            }
        }
        return found;
    }

    private void sample() {
        if (sampler == null || zombie == null) {
            return;
        }
        // Server main-thread scheduler callback; NOT host/packet time.
        int tick = Bukkit.getCurrentTick();
        int offset = tick - baselineTick;
        Zombie current = null;
        if (uuid != null && Bukkit.getEntity(uuid) instanceof Zombie same) {
            current = same;
        }
        if (
            current == null || current.isDead() || !current.isValid()
            || current.getEntityId() != entityId
            || !current.getUniqueId().equals(uuid)
            || !current.getWorld().getUID().equals(worldUuid)
        ) {
            closeWindow("ENTITY_LOST_OR_REPLACED");
            return;
        }
        if (tick < baselineTick || offset != lastOffset + 1) {
            closeWindow("NONCONTIGUOUS_PAPER_TICK");
            return;
        }
        Location location = current.getLocation();
        if (!Double.isFinite(location.getX())
                || !Double.isFinite(location.getY())
                || !Double.isFinite(location.getZ())) {
            closeWindow("INVALID_POSITION");
            return;
        }
        // One unambiguous bounded original row per Paper server tick.
        // Sample t=0,10,30 is necessary but not sufficient for client join.
        getLogger().info(String.format(Locale.ROOT,
            "L_ZOMBIE_TICK_V1 marker=%s session=%s world=%s entity_uuid=%s "
            + "entity_id=%d spawn_instance=1 server_tick=%d offset=%d "
            + "x=%.12f y=%.12f z=%.12f",
            marker, session, worldUuid, uuid, entityId,
            tick, offset, location.getX(), location.getY(), location.getZ()
        ));
        samples++;
        if (prospectiveCheap && offset == 0) {
            firstX = location.getX();
            firstZ = location.getZ();
        }
        if (prospectiveCheap && offset == FIRST_PREDICTION_OFFSET) {
            // Synchronous main-thread, strictly before offset11..30.
            double currentX = location.getX();
            double currentZ = location.getZ();
            double velocityX = currentX + 2.0 * (currentX - firstX);
            double velocityZ = currentZ + 2.0 * (currentZ - firstZ);
            if (!Double.isFinite(velocityX) || !Double.isFinite(velocityZ)) {
                closeWindow("NONFINITE_FORECAST");
                return;
            }
            getLogger().info(String.format(Locale.ROOT,
                "L_ZOMBIE_CHEAP_FREEZE_V2 marker=%s session=%s world=%s "
                + "entity_uuid=%s entity_id=%d source_first_tick=%d "
                + "issued_tick=%d target_tick=%d "
                + "stationary_x=%.12f stationary_z=%.12f "
                + "velocity_x=%.12f velocity_z=%.12f",
                marker, session, worldUuid, uuid, entityId,
                tick - FIRST_PREDICTION_OFFSET, tick, tick + 20,
                currentX, currentZ, velocityX, velocityZ
            ));
            forecastFrozen = true;
        }
        lastTick = tick;
        lastOffset = offset;
        if (offset == LAST_OFFSET) {
            closeWindow(
                (samples == LAST_OFFSET + 1 && (!prospectiveCheap || forecastFrozen))
                ? "PAPER_WINDOW_COMPLETE" : "INCOMPLETE_FORECAST"
            );
        }
    }

    @Override
    public boolean onCommand(
        CommandSender sender, Command cmd, String label, String[] args
    ) {
        if (!cmd.getName().equalsIgnoreCase("relayzombietrack")) {
            return false;
        }
        if (!(sender instanceof ConsoleCommandSender) || !enabled) {
            return true;
        }
        if (args.length == 1 && args[0].equals("stop")) {
            if (sampler != null) {
                closeWindow("OPERATOR_STOP");
            }
            return true;
        }
        if (args.length != 3 || !args[0].equals("start")
                || !TOKEN.matcher(args[1]).matches()
                || !TOKEN.matcher(args[2]).matches()
                || sampler != null) {
            getLogger().info("L_ZOMBIE_START_REJECTED invalid_scope_or_active");
            return true;
        }
        List<Zombie> candidates = selectOne();
        if (candidates.size() != 1) {
            getLogger().info("L_ZOMBIE_START_REJECTED zombie_candidates="
                + (candidates.size() > 1 ? "MULTIPLE" : "ZERO"));
            return true;
        }
        zombie = candidates.get(0);
        uuid = zombie.getUniqueId();
        worldUuid = zombie.getWorld().getUID();
        entityId = zombie.getEntityId();
        marker = args[1];
        session = args[2];
        samples = 0;
        forecastFrozen = false;
        firstX = 0.0;
        firstZ = 0.0;
        lastOffset = -1;
        lastTick = -1;
        // Paper scheduler will sample offset zero on its first callback.
        baselineTick = Bukkit.getCurrentTick() + 1;
        getLogger().info("L_ZOMBIE_ARM_V1 marker=" + marker
            + " session=" + session + " world=" + worldUuid
            + " entity_uuid=" + uuid + " entity_id=" + entityId
            + " expected_samples=31 pre_offset=" + FIRST_PREDICTION_OFFSET
            + " future_offset=" + LAST_OFFSET);
        sampler = Bukkit.getScheduler().runTaskTimer(this, this::sample, 1L, 1L);
        return true;
    }
}
