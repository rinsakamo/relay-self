package io.github.rinsakamo.p0m;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.DirectoryStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Properties;
import java.util.UUID;
import org.bukkit.Bukkit;
import org.bukkit.Location;
import org.bukkit.World;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.player.PlayerJoinEvent;
import org.bukkit.plugin.java.JavaPlugin;

/**
 * P0M: independent, read-only main-thread Minecraft player position per tick.
 *
 * No physical Action, world mutation, retry, authorization, plugin commands or
 * Paper save control. A spool file is an untrusted local DEV request; the
 * Bukkit on-main-thread observations are evidence, not an identity proof.
 */
public final class MoveWitness extends JavaPlugin implements Listener {
    private static final int MAX_ARM_TICKS = 100;
    private static final int POST_STOP_TICKS = 16;
    private final String bootId = UUID.randomUUID().toString();
    private final Map<String, Window> active = new HashMap<>();
    private Path requests;
    private Path handled;
    private Path acks;
    private Path complete;

    private static final class Window {
        final String nonce;
        final String world;
        final String actor;
        final String action;
        final String nativeSession;
        final int armTick;
        final StringBuilder samples = new StringBuilder();
        int stopTick = -1;
        int lastTick;

        Window(String nonce, String world, String actor, String action,
               String nativeSession, int armTick) {
            this.nonce = nonce;
            this.world = world;
            this.actor = actor;
            this.action = action;
            this.nativeSession = nativeSession;
            this.armTick = armTick;
            this.lastTick = armTick - 1;
        }
    }

    @Override
    public void onEnable() {
        try {
            Path root = getDataFolder().toPath().resolve("p0m");
            requests = root.resolve("requests");
            handled = root.resolve("handled");
            acks = root.resolve("acks");
            complete = root.resolve("complete");
            for (Path dir : List.of(requests, handled, acks, complete)) {
                Files.createDirectories(dir);
            }
        } catch (IOException exc) {
            throw new IllegalStateException("cannot create P0M witness spool", exc);
        }
        Bukkit.getPluginManager().registerEvents(this, this);
        Bukkit.getScheduler().runTaskTimer(this, this::sampleOnMainThread, 1L, 1L);
        getLogger().info("P0M_READY boot=" + bootId + " source=PAPER_MAIN_THREAD");
    }

    /** Bind Paper actor UUID to Mineflayer's configured login name in the
     * same owned log *before* a MOVE is ever issued.
     * This is a DEV identity join, not authenticated remote attestation.
     */
    @EventHandler(priority = EventPriority.MONITOR)
    public void playerJoined(PlayerJoinEvent event) {
        Player player = event.getPlayer();
        getLogger().info("P0M_PLAYER boot=" + bootId
            + " world=" + player.getWorld().getUID()
            + " actor=" + player.getUniqueId()
            + " name=" + player.getName()
            + " tick=" + Bukkit.getCurrentTick());
    }

    private static String field(Properties p, String key) {
        String value = p.getProperty(key);
        if (value == null || !value.matches("[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")) {
            throw new IllegalArgumentException("invalid P0M " + key);
        }
        return value;
    }

    private static String canonicalUuid(String value) {
        if (!UUID.fromString(value).toString().equals(value)) {
            throw new IllegalArgumentException("noncanonical P0M UUID");
        }
        return value;
    }

    private static Properties claim(Path source, String[] names) throws IOException {
        Properties p = new Properties();
        try (InputStream input = Files.newInputStream(source)) {
            p.load(input);
        }
        if (p.size() != names.length) {
            throw new IllegalArgumentException("unknown or duplicate P0M request field");
        }
        for (String key : names) field(p, key);
        return p;
    }

    private static void publish(Path dest, String text) throws IOException {
        Path temp = dest.resolveSibling(dest.getFileName() + ".tmp");
        Files.writeString(temp, text, StandardCharsets.UTF_8,
            StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE);
        Files.move(temp, dest, StandardCopyOption.ATOMIC_MOVE);
    }

    private void pollArms(int now) {
        try (DirectoryStream<Path> stream = Files.newDirectoryStream(requests, "*.arm")) {
            for (Path path : stream) {
                try {
                    String name = path.getFileName().toString();
                    String nonce = canonicalUuid(name.substring(0, name.length() - 4));
                    if (Files.isSymbolicLink(path) || active.containsKey(nonce)) {
                        throw new IllegalArgumentException("reused P0M nonce");
                    }
                    Path consumed = handled.resolve(nonce + ".arm");
                    Files.move(path, consumed);
                    Properties p = claim(consumed, new String[] {
                        "nonce", "world_uuid", "actor_uuid", "action_id",
                        "native_session_id",
                    });
                    String worldId = canonicalUuid(field(p, "world_uuid"));
                    String actorId = canonicalUuid(field(p, "actor_uuid"));
                    if (!nonce.equals(field(p, "nonce"))) {
                        throw new IllegalArgumentException("mismatched P0M nonce");
                    }
                    String action = field(p, "action_id");
                    String nativeSession = field(p, "native_session_id");
                    World world = Bukkit.getWorld(UUID.fromString(worldId));
                    Player actor = Bukkit.getPlayer(UUID.fromString(actorId));
                    if (world == null || actor == null || !actor.isOnline()
                            || actor.getWorld() != world || actor.isDead()
                            || active.values().stream().anyMatch(
                                entry -> entry.actor.equals(actorId))) {
                        throw new IllegalArgumentException("P0M actor/World is not uniquely live");
                    }
                    Window window = new Window(nonce, worldId, actorId,
                        action, nativeSession, now);
                    active.put(nonce, window);
                    publish(acks.resolve(nonce + ".armed"), armFields(window));
                    getLogger().info("P0M_ARM nonce=" + nonce + " boot=" + bootId
                        + " action=" + action + " actor=" + actorId
                        + " world=" + worldId + " tick=" + now);
                } catch (Exception exc) {
                    getLogger().warning("P0M_ARM_REJECT file=" + path.getFileName()
                        + " reason=" + exc.getClass().getSimpleName());
                }
            }
        } catch (IOException exc) {
            getLogger().warning("P0M_ARM_IO_FAILED " + exc.getClass().getSimpleName());
        }
    }

    private void pollStopMarks(int now) {
        try (DirectoryStream<Path> stream = Files.newDirectoryStream(requests, "*.mark")) {
            for (Path path : stream) {
                try {
                    String name = path.getFileName().toString();
                    String nonce = canonicalUuid(name.substring(0, name.length() - 5));
                    Path consumed = handled.resolve(nonce + ".mark");
                    if (Files.isSymbolicLink(path)) {
                        throw new IllegalArgumentException("P0M marker symlink");
                    }
                    Files.move(path, consumed);
                    Properties p = claim(consumed, new String[] {"nonce", "action_id"});
                    Window window = active.get(nonce);
                    if (window == null || window.stopTick >= 0
                            || now <= window.armTick
                            || !nonce.equals(field(p, "nonce"))
                            || !window.action.equals(field(p, "action_id"))) {
                        throw new IllegalArgumentException("foreign/duplicate P0M STOP marker");
                    }
                    window.stopTick = now;
                    getLogger().info("P0M_STOP_MARK nonce=" + nonce
                        + " boot=" + bootId + " tick=" + now);
                } catch (Exception exc) {
                    getLogger().warning("P0M_STOP_REJECT file=" + path.getFileName()
                        + " reason=" + exc.getClass().getSimpleName());
                }
            }
        } catch (IOException exc) {
            getLogger().warning("P0M_STOP_IO_FAILED " + exc.getClass().getSimpleName());
        }
    }

    private String armFields(Window w) {
        return "boot_id=" + bootId + "\n"
            + "nonce=" + w.nonce + "\n"
            + "world_uuid=" + w.world + "\n"
            + "actor_uuid=" + w.actor + "\n"
            + "action_id=" + w.action + "\n"
            + "native_session_id=" + w.nativeSession + "\n"
            + "arm_tick=" + w.armTick + "\n"
            + "source=PAPER_MAIN_THREAD\n";
    }

    private String traceFields(Window w) {
        return armFields(w)
            + "stop_mark_tick=" + w.stopTick + "\n"
            + w.samples.toString();
    }

    private void sampleOnMainThread() {
        if (!Bukkit.isPrimaryThread()) {
            throw new IllegalStateException("P0M position read escaped main thread");
        }
        int now = Bukkit.getCurrentTick();
        pollArms(now);
        pollStopMarks(now);
        List<String> finished = new ArrayList<>();
        for (Window w : active.values()) {
            try {
                Player actor = Bukkit.getPlayer(UUID.fromString(w.actor));
                World world = Bukkit.getWorld(UUID.fromString(w.world));
                if (actor == null || world == null || !actor.isOnline()
                        || actor.isDead() || actor.getWorld() != world
                        || now > w.armTick + MAX_ARM_TICKS
                        || w.lastTick + 1 != now
                        || w.samples.length() > 12000) {
                    throw new IllegalStateException("P0M observation/World continuity lost");
                }
                Location xyz = actor.getLocation();
                w.samples.append("sample=").append(now).append(",")
                    .append(Double.toString(xyz.getX())).append(",")
                    .append(Double.toString(xyz.getY())).append(",")
                    .append(Double.toString(xyz.getZ())).append("\n");
                w.lastTick = now;
                if (w.stopTick >= 0 && now >= w.stopTick + POST_STOP_TICKS) {
                    publish(complete.resolve(w.nonce + ".trace"), traceFields(w));
                    getLogger().info("P0M_COMPLETE nonce=" + w.nonce
                        + " boot=" + bootId + " tick=" + now
                        + " source=PAPER_MAIN_THREAD");
                    finished.add(w.nonce);
                }
            } catch (Exception exc) {
                // No terminal trace is emitted on lost actor, World or samples.
                getLogger().warning("P0M_ABORT nonce=" + w.nonce
                    + " reason=" + exc.getClass().getSimpleName());
                finished.add(w.nonce);
            }
        }
        for (String nonce : finished) active.remove(nonce);
    }
}
