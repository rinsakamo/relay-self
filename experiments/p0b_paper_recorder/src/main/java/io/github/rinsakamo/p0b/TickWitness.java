package io.github.rinsakamo.p0b;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.DirectoryStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.util.Properties;
import java.util.UUID;
import org.bukkit.Bukkit;
import org.bukkit.World;
import org.bukkit.plugin.java.JavaPlugin;

/**
 * Read-only P0-D Paper main-thread tick witness, independent of Mineflayer.
 *
 * Requests/ACKs are a local DEV spool. An ACK proves the plugin code executed
 * a main-thread Bukkit tick read, not a cryptographically authenticated server,
 * an atomic multi-world save, or an authorization to issue physical Actions.
 */
final class TickWitness {
    private final JavaPlugin plugin;
    private final UUID bootId = UUID.randomUUID();
    private final Path requests;
    private final Path handled;
    private final Path acks;

    TickWitness(JavaPlugin plugin) throws IOException {
        this.plugin = plugin;
        Path root = plugin.getDataFolder().toPath().resolve("p0d-ticks");
        requests = root.resolve("requests");
        handled = root.resolve("handled");
        acks = root.resolve("acks");
        Files.createDirectories(requests);
        Files.createDirectories(handled);
        Files.createDirectories(acks);
    }

    void start() {
        Bukkit.getScheduler().runTaskTimer(plugin, this::pollOnMainThread, 1L, 1L);
        plugin.getLogger().info("P0D_TICK_READY boot=" + bootId
            + " source=PAPER_MAIN_THREAD");
    }

    private static String field(Properties properties, String name) {
        String value = properties.getProperty(name);
        if (value == null || !value.matches("[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")) {
            throw new IllegalArgumentException("invalid " + name);
        }
        return value;
    }

    private void pollOnMainThread() {
        if (!Bukkit.isPrimaryThread()) {
            throw new IllegalStateException("P0D tick witness escaped Paper main thread");
        }
        try (DirectoryStream<Path> stream = Files.newDirectoryStream(requests, "*.request")) {
            for (Path request : stream) {
                try {
                    String filename = request.getFileName().toString();
                    String nonce = filename.substring(0, filename.length() - ".request".length());
                    if (!UUID.fromString(nonce).toString().equals(nonce)) {
                        throw new IllegalArgumentException("noncanonical nonce");
                    }
                    // Consume once, retaining source evidence. Duplicate nonce
                    // or a stale request from a previous Paper boot is refused.
                    Path source = handled.resolve(nonce + ".handled");
                    Files.move(request, source);
                    Properties input = new Properties();
                    try (InputStream data = Files.newInputStream(source)) {
                        input.load(data);
                    }
                    if (!field(input, "nonce").equals(nonce)) {
                        throw new IllegalArgumentException("nonce mismatch");
                    }
                    UUID worldUuid = UUID.fromString(field(input, "world_uuid"));
                    World world = Bukkit.getWorld(worldUuid);
                    if (world == null) {
                        throw new IllegalArgumentException("world UUID not loaded");
                    }
                    String session = field(input, "server_session_id");
                    if (!session.startsWith("paper-owned-")) {
                        throw new IllegalArgumentException("unknown owned Paper session format");
                    }
                    int tick = Bukkit.getCurrentTick();
                    if (tick < 0) {
                        throw new IllegalStateException("negative Bukkit tick");
                    }
                    String text = "boot_id=" + bootId + "\n"
                        + "nonce=" + nonce + "\n"
                        + "paper_tick=" + tick + "\n"
                        + "server_session_id=" + session + "\n"
                        + "source=PAPER_MAIN_THREAD\n"
                        + "world_uuid=" + worldUuid + "\n";
                    Path temporary = acks.resolve(nonce + ".tmp");
                    Files.writeString(temporary, text, StandardCharsets.UTF_8,
                        StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE);
                    Files.move(temporary, acks.resolve(nonce + ".ack"),
                        StandardCopyOption.ATOMIC_MOVE);
                    plugin.getLogger().info("P0D_TICK_ACK nonce=" + nonce
                        + " boot=" + bootId + " session=" + session
                        + " world=" + worldUuid + " tick=" + tick
                        + " source=PAPER_MAIN_THREAD");
                } catch (Exception failure) {
                    plugin.getLogger().warning("P0D_TICK_REJECT file="
                        + request.getFileName() + " reason="
                        + failure.getClass().getSimpleName());
                }
            }
        } catch (IOException failure) {
            plugin.getLogger().warning("P0D_TICK_READ_ERROR "
                + failure.getClass().getSimpleName());
        }
    }
}
