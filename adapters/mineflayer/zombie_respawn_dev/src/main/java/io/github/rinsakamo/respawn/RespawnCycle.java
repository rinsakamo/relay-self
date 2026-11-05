package io.github.rinsakamo.respawn;

import java.util.Objects;
import java.util.UUID;

/**
 * Pure World-owned 600-server-tick generation gate.
 * No Bukkit, L0, Action, host clock, retry loop or Self-controlled coefficient.
 */
public final class RespawnCycle {
    public static final long DELAY_TICKS = 600L;

    private UUID world;
    private UUID living;
    private UUID deceased;
    private long generation;
    private long dueTick = -1L;

    public boolean begin(UUID worldId, UUID zombieId, long tick) {
        require(worldId, zombieId, tick);
        if (world != null) return false;
        world = worldId;
        living = zombieId;
        generation = 1;
        return true;
    }

    public boolean died(UUID worldId, UUID zombieId, long tick) {
        require(worldId, zombieId, tick);
        if (!Objects.equals(world, worldId)
                || !Objects.equals(living, zombieId) || dueTick != -1L
                || tick > Long.MAX_VALUE - DELAY_TICKS) return false;
        living = null;
        deceased = zombieId;
        dueTick = tick + DELAY_TICKS;
        return true;
    }

    public boolean due(UUID worldId, long tick) {
        Objects.requireNonNull(worldId, "worldId");
        if (tick < 0) throw new IllegalArgumentException("negative tick");
        return worldId.equals(world) && living == null
            && dueTick >= 0 && tick >= dueTick;
    }

    public boolean reborn(UUID worldId, UUID zombieId, long tick) {
        require(worldId, zombieId, tick);
        if (!due(worldId, tick) || zombieId.equals(deceased)) return false;
        living = zombieId;
        dueTick = -1L;
        deceased = null;
        generation++;
        return true;
    }

    public long generation() { return generation; }
    public long dueTick() { return dueTick; }
    public UUID living() { return living; }
    public UUID world() { return world; }

    public void clear() {
        world = null;
        living = null;
        deceased = null;
        generation = 0L;
        dueTick = -1L;
    }

    private static void require(UUID worldId, UUID zombieId, long tick) {
        Objects.requireNonNull(worldId, "worldId");
        Objects.requireNonNull(zombieId, "zombieId");
        if (tick < 0) throw new IllegalArgumentException("negative tick");
    }
}
