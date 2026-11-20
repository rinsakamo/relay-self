package io.github.rinsakamo.p0b;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.DirectoryStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.time.Instant;
import java.util.Properties;
import java.util.UUID;
import org.bukkit.Bukkit;
import org.bukkit.World;
import org.bukkit.entity.Entity;
import org.bukkit.entity.Player;
import org.bukkit.plugin.java.JavaPlugin;
import org.bukkit.util.BoundingBox;

/** Bounded, operator-only observation; this is not an identity or action authority. */
final class WorldSnapshot {
    private static final int MAX_BLOCKS = 1024, MAX_BOXES = 4096, MAX_ENTITIES = 128;
    private final JavaPlugin plugin;
    private final UUID boot = UUID.randomUUID();
    private final Path requests, handled, output;

    WorldSnapshot(JavaPlugin plugin) throws Exception {
        this.plugin = plugin;
        Path root = plugin.getDataFolder().toPath().resolve("p0d-snapshots");
        requests = root.resolve("requests"); handled = root.resolve("handled"); output = root.resolve("output");
        Files.createDirectories(requests); Files.createDirectories(handled); Files.createDirectories(output);
    }
    void start() { Bukkit.getScheduler().runTaskTimer(plugin, this::poll, 1L, 1L); }
    private static JsonArray box(BoundingBox b, double x, double y, double z) {
        JsonArray a = new JsonArray();
        for (double v : new double[]{b.getMinX()+x,b.getMinY()+y,b.getMinZ()+z,
                                     b.getMaxX()+x,b.getMaxY()+y,b.getMaxZ()+z}) a.add(v);
        return a;
    }
    private void poll() {
        if (!Bukkit.isPrimaryThread()) throw new IllegalStateException("not main thread");
        try (DirectoryStream<Path> stream = Files.newDirectoryStream(requests, "*.request")) {
            // At most one request per tick.
            for (Path path : stream) {
                try { capture(path); } catch (Exception e) {
                    plugin.getLogger().warning("SNAPSHOT_REJECT " + e.getClass().getSimpleName());
                }
                break;
            }
        } catch (Exception e) { plugin.getLogger().warning("SNAPSHOT_SPOOL_ERROR " + e.getClass().getSimpleName()); }
    }
    private void capture(Path path) throws Exception {
        String file = path.getFileName().toString();
        String id = file.substring(0, file.length()-8);
        if (!UUID.fromString(id).toString().equals(id)) throw new IllegalArgumentException("request id");
        Path original = handled.resolve(id + ".handled");
        Files.move(path, original);
        Properties p = new Properties();
        try (InputStream in = Files.newInputStream(original)) { p.load(in); }
        if (!id.equals(p.getProperty("request_id"))) throw new IllegalArgumentException("request mismatch");
        World w = Bukkit.getWorld(UUID.fromString(p.getProperty("world_uuid")));
        Player player = Bukkit.getPlayer(UUID.fromString(p.getProperty("player_uuid")));
        if (w == null || player == null || !player.isOnline() || !player.getWorld().equals(w))
            throw new IllegalArgumentException("player/world unavailable");
        double tx = Double.parseDouble(p.getProperty("target_x"));
        double tz = Double.parseDouble(p.getProperty("target_z"));
        var loc = player.getLocation(); var b = player.getBoundingBox();
        if (!Double.isFinite(tx) || !Double.isFinite(tz) || Math.hypot(tx-loc.getX(), tz-loc.getZ()) > 5.01)
            throw new IllegalArgumentException("target out of bounds");
        int x0 = (int)Math.floor(Math.min(b.getMinX(), b.getMinX()+tx-loc.getX()))-1;
        int x1 = (int)Math.ceil(Math.max(b.getMaxX(), b.getMaxX()+tx-loc.getX()))+1;
        int z0 = (int)Math.floor(Math.min(b.getMinZ(), b.getMinZ()+tz-loc.getZ()))-1;
        int z1 = (int)Math.ceil(Math.max(b.getMaxZ(), b.getMaxZ()+tz-loc.getZ()))+1;
        int y0 = (int)Math.floor(b.getMinY())-2, y1 = (int)Math.ceil(b.getMaxY())+1;
        if (y0 < w.getMinHeight() || y1 > w.getMaxHeight() || (long)(x1-x0)*(y1-y0)*(z1-z0)>MAX_BLOCKS)
            throw new IllegalArgumentException("capture bounds");
        int start = Bukkit.getCurrentTick(), count = 0;
        JsonObject out = new JsonObject(); out.addProperty("request_id", id); out.addProperty("boot_id", boot.toString());
        out.addProperty("world_uuid", w.getUID().toString()); out.addProperty("dimension", w.getKey().toString());
        out.addProperty("environment", w.getEnvironment().name()); out.addProperty("capture_time", Instant.now().toString());
        out.addProperty("start_tick", start); out.addProperty("player_uuid", player.getUniqueId().toString());
        out.add("body_aabb", box(b, 0, 0, 0));
        JsonArray position = new JsonArray(); position.add(loc.getX()); position.add(loc.getY()); position.add(loc.getZ()); out.add("position", position);
        out.addProperty("pose", player.getPose().name()); out.addProperty("on_ground", player.isOnGround());
        out.addProperty("sneaking", player.isSneaking()); out.addProperty("sprinting", player.isSprinting());
        out.addProperty("flying", player.isFlying()); out.addProperty("yaw", loc.getYaw()); out.addProperty("pitch", loc.getPitch());
        JsonArray bounds = new JsonArray(); for (int n : new int[]{x0,y0,z0,x1,y1,z1}) bounds.add(n); out.add("bounds_exclusive", bounds);
        JsonArray cells = new JsonArray(); boolean complete = true;
        outer: for (int x=x0; x<x1; x++) for (int z=z0; z<z1; z++) for (int y=y0; y<y1; y++) {
            JsonObject cell = new JsonObject(); cell.addProperty("x",x); cell.addProperty("y",y); cell.addProperty("z",z);
            boolean loaded = w.isChunkLoaded(x >> 4,z >> 4); cell.addProperty("chunk_loaded",loaded);
            if (!loaded) { complete=false; cells.add(cell); continue; }
            try {
                var block = w.getBlockAt(x,y,z); cell.addProperty("block_state",block.getBlockData().getAsString());
                JsonArray boxes = new JsonArray();
                for (BoundingBox shape : block.getCollisionShape().getBoundingBoxes()) {
                    if (++count > MAX_BOXES) { complete=false; break outer; }
                    boxes.add(box(shape,x,y,z));
                }
                cell.add("collision_boxes_world", boxes); cell.addProperty("read_ok",true);
            } catch (RuntimeException e) { complete=false; cell.addProperty("read_ok",false); }
            cells.add(cell);
        }
        out.add("cells",cells); out.addProperty("terrain_complete",complete);
        JsonArray entities = new JsonArray();
        for (Entity e : w.getNearbyEntities(new BoundingBox(x0,y0,z0,x1,y1,z1))) {
            if (e.getUniqueId().equals(player.getUniqueId())) continue;
            if (entities.size() >= MAX_ENTITIES) break;
            JsonObject item = new JsonObject(); item.addProperty("uuid",e.getUniqueId().toString());
            item.addProperty("type",e.getType().name()); item.addProperty("valid",e.isValid());
            item.addProperty("dead",e.isDead()); item.add("aabb",box(e.getBoundingBox(),0,0,0)); entities.add(item);
        }
        out.add("entities",entities);
        // API explicitly allows implementation search restrictions, so absence cannot prove coverage.
        out.addProperty("entity_coverage_complete",false);
        out.addProperty("end_tick", Bukkit.getCurrentTick());
        Path temp = output.resolve(id + ".tmp");
        Files.writeString(temp,out.toString(),StandardCharsets.UTF_8,StandardOpenOption.CREATE_NEW);
        Files.move(temp,output.resolve(id + ".json"),StandardCopyOption.ATOMIC_MOVE);
    }
}
