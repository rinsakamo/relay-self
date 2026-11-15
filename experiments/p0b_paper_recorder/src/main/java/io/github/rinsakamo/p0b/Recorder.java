package io.github.rinsakamo.p0b;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.DirectoryStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.util.HashMap;
import java.util.Map;
import java.util.Properties;
import java.util.UUID;
import org.bukkit.Bukkit;
import org.bukkit.World;
import org.bukkit.entity.Entity;
import org.bukkit.entity.Player;
import org.bukkit.entity.Zombie;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.entity.EntityDamageByEntityEvent;
import org.bukkit.event.entity.EntityDeathEvent;
import org.bukkit.event.entity.CreatureSpawnEvent;
import org.bukkit.event.player.PlayerJoinEvent;
import org.bukkit.plugin.java.JavaPlugin;

/** DEV-only passive observer. Tickets never issue or authorize physical Actions. */
public final class Recorder extends JavaPlugin implements Listener {
    private record Ticket(
        String nonce, String world, String branch, String action, String session,
        UUID actor, UUID target, int tick
    ) {}
    private record DamageLink(String damageId, UUID attacker, int tick) {}
    private final Map<String, Ticket> pending = new HashMap<>();
    private final Map<UUID, DamageLink> lastDamage = new HashMap<>();
    private Path requests;
    private Path acks;
    private Path handled;
    private long ordinal;

    @Override public void onEnable() {
        try {
            requests = getDataFolder().toPath().resolve("requests");
            acks = getDataFolder().toPath().resolve("acks");
            handled = getDataFolder().toPath().resolve("handled");
            Files.createDirectories(requests);
            Files.createDirectories(acks);
            Files.createDirectories(handled);
        } catch (IOException exc) {
            throw new IllegalStateException("P0B observer ticket spool cannot initialize", exc);
        }
        Bukkit.getPluginManager().registerEvents(this, this);
        try {
            new TickWitness(this).start();
            new ResidentPresenceWitness(this).start();
        } catch (IOException exc) {
            throw new IllegalStateException("P0D Paper tick witness spool cannot initialize", exc);
        }
        Bukkit.getScheduler().runTaskTimer(this, this::readTicketRequests, 1L, 1L);
        getLogger().info("P0B_READY source=PAPER_MONITOR ticket_dev=LOCAL_SPOOL");
    }

    private static String field(Properties props, String name) {
        String value = props.getProperty(name);
        if (value == null || !value.matches("[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")) {
            throw new IllegalArgumentException("invalid " + name);
        }
        return value;
    }
    private static String encodeAck(Ticket t) {
        return "action_id=" + t.action() + "\n"
            + "actor_uuid=" + t.actor() + "\n"
            + "branch_id=" + t.branch() + "\n"
            + "native_session_id=" + t.session() + "\n"
            + "nonce=" + t.nonce() + "\n"
            + "registered_at_tick=" + t.tick() + "\n"
            + "server_ack_ref=paper:ticket-ack:" + t.nonce() + ":" + t.tick() + "\n"
            + "target_uuid=" + t.target() + "\n"
            + "world_id=" + t.world() + "\n";
    }

    private void readTicketRequests() {
        int now = Bukkit.getCurrentTick();
        pending.values().removeIf(t -> now - t.tick() > 80);
        try (DirectoryStream<Path> stream = Files.newDirectoryStream(requests, "*.request")) {
            for (Path request : stream) {
                try {
                    String filename = request.getFileName().toString();
                    String nonce = filename.substring(0, filename.length() - ".request".length());
                    UUID.fromString(nonce);
                    Path saved = handled.resolve(nonce + ".handled");
                    // Consume the input exactly once on this server instance,
                    // retaining the original as an evidence artifact.
                    Files.move(request, saved);
                    Properties props = new Properties();
                    try (InputStream input = Files.newInputStream(saved)) {
                        props.load(input);
                    }
                    if (!field(props, "nonce").equals(nonce)) {
                        throw new IllegalArgumentException("request filename and nonce differ");
                    }
                    String worldId = field(props, "world_id");
                    World world = Bukkit.getWorld(UUID.fromString(worldId));
                    UUID actorId = UUID.fromString(field(props, "actor_uuid"));
                    UUID targetId = UUID.fromString(field(props, "target_uuid"));
                    Player player = Bukkit.getPlayer(actorId);
                    Entity entity = Bukkit.getEntity(targetId);
                    if (world == null || player == null || !player.isOnline()
                            || !(entity instanceof Zombie zombie)
                            || player.getWorld() != world || zombie.getWorld() != world
                            || player.getUniqueId().equals(zombie.getUniqueId())
                            || pending.values().stream().anyMatch(t ->
                                t.actor().equals(actorId) && t.target().equals(targetId))) {
                        throw new IllegalArgumentException("not one live unique actor/Zombie World");
                    }
                    Ticket ticket = new Ticket(nonce, worldId, field(props, "branch_id"),
                        field(props, "action_id"), field(props, "native_session_id"),
                        actorId, targetId, now);
                    Path temporary = acks.resolve(nonce + ".tmp");
                    Files.writeString(temporary, encodeAck(ticket), StandardCharsets.UTF_8,
                        StandardOpenOption.CREATE_NEW);
                    Files.move(temporary, acks.resolve(nonce + ".ack"),
                        StandardCopyOption.ATOMIC_MOVE);
                    pending.put(nonce, ticket);
                    getLogger().info("P0B_TICKET_ACK nonce=" + nonce + " tick=" + now
                        + " world=" + worldId + " branch=" + ticket.branch()
                        + " action=" + ticket.action() + " session=" + ticket.session()
                        + " actor=" + actorId + " victim=" + targetId);
                } catch (Exception failure) {
                    getLogger().warning("P0B_TICKET_REJECT file=" + request.getFileName()
                        + " reason=" + failure.getClass().getSimpleName());
                }
            }
        } catch (IOException exc) {
            getLogger().warning("P0B_TICKET_READ_ERROR " + exc.getClass().getSimpleName());
        }
    }

    @EventHandler(priority = EventPriority.MONITOR)
    public void spawn(CreatureSpawnEvent event) {
        if (!(event.getEntity() instanceof Zombie z)) return;
        var p = z.getLocation();
        getLogger().info("P0B_SPAWN tick=" + Bukkit.getCurrentTick() + " world="
            + z.getWorld().getUID() + " victim=" + z.getUniqueId() + " health=" + z.getHealth()
            + " x=" + p.getX() + " y=" + p.getY() + " z=" + p.getZ()
            + " difficulty=" + z.getWorld().getDifficulty() + " cancelled=" + event.isCancelled());
    }

    @EventHandler(priority = EventPriority.MONITOR)
    public void join(PlayerJoinEvent event) {
        Player p = event.getPlayer();
        getLogger().info("P0B_PLAYER tick=" + Bukkit.getCurrentTick() + " world="
            + p.getWorld().getUID() + " actor=" + p.getUniqueId() + " name=" + p.getName());
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = false)
    public void damage(EntityDamageByEntityEvent event) {
        if (!(event.getEntity() instanceof Zombie z)) return;
        Entity attacker = event.getDamager();
        String id = "damage-" + (++ordinal);
        int tick = Bukkit.getCurrentTick();
        UUID world = z.getWorld().getUID();
        UUID victim = z.getUniqueId();
        double before = z.getHealth();
        Ticket found = null;
        if (!event.isCancelled()
                && event.getCause() == org.bukkit.event.entity.EntityDamageEvent.DamageCause.ENTITY_ATTACK
                && attacker instanceof Player) {
            for (Ticket t : pending.values()) {
                if (t.world().equals(world.toString()) && t.actor().equals(attacker.getUniqueId())
                        && t.target().equals(victim) && tick >= t.tick() && tick - t.tick() <= 80) {
                    found = t;
                    break;
                }
            }
        }
        String nonce = "NONE";
        if (found != null) {
            nonce = found.nonce();
            pending.remove(nonce);
            lastDamage.put(victim, new DamageLink(id, attacker.getUniqueId(), tick));
            getLogger().info("P0B_TICKET_CONSUMED nonce=" + nonce + " action=" + found.action()
                + " damage_event=" + id + " tick=" + tick);
        } else if (!event.isCancelled()) {
            // Independent damage may still be seen, but no Action attribution.
            lastDamage.remove(victim);
        }
        getLogger().info("P0B_DAMAGE event=" + id + " tick=" + tick + " world=" + world
            + " victim=" + victim + " attacker=" + attacker.getUniqueId()
            + " cause=" + event.getCause() + " before=" + before
            + " final_damage=" + event.getFinalDamage() + " cancelled=" + event.isCancelled()
            + " ticket_nonce=" + nonce);
        Bukkit.getScheduler().runTask(this, () -> {
            String health = z.isValid() && !z.isDead() ? Double.toString(z.getHealth()) : "UNKNOWN";
            getLogger().info("P0B_AFTER event=" + id + " tick=" + Bukkit.getCurrentTick()
                + " world=" + world + " victim=" + victim + " health=" + health);
        });
    }

    @EventHandler(priority = EventPriority.MONITOR)
    public void death(EntityDeathEvent event) {
        if (!(event.getEntity() instanceof Zombie z)) return;
        Player killer = z.getKiller();
        int tick = Bukkit.getCurrentTick();
        DamageLink prev = lastDamage.remove(z.getUniqueId());
        String link = prev != null && killer != null
            && prev.tick() == tick && prev.attacker().equals(killer.getUniqueId())
            ? prev.damageId() : "UNKNOWN";
        getLogger().info("P0B_DEATH event=death-" + (++ordinal) + " tick=" + tick
            + " world=" + z.getWorld().getUID() + " victim=" + z.getUniqueId()
            + " killer=" + (killer == null ? "UNKNOWN" : killer.getUniqueId())
            + " health=" + z.getHealth() + " damage_link=" + link);
    }
}
