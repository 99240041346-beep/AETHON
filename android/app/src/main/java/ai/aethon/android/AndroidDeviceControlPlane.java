package ai.aethon.android;

import android.os.SystemClock;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * Local device-control coordinator.
 *
 * Keeps the phone as the execution authority while the cloud remains an
 * intelligence/orchestration layer. Commands are bounded by capability,
 * expiry and idempotency before reaching AndroidActionExecutor.
 */
public final class AndroidDeviceControlPlane {
    public static final long DEFAULT_COMMAND_TTL_MS = 60_000L;
    private static final int MAX_DEDUPE_ENTRIES = 256;

    private final AndroidActionExecutor executor;
    private final Map<String, Long> completedCommands =
            new LinkedHashMap<String, Long>(MAX_DEDUPE_ENTRIES, .75f, true) {
                @Override protected boolean removeEldestEntry(Map.Entry<String, Long> eldest) {
                    return size() > MAX_DEDUPE_ENTRIES;
                }
            };

    private volatile long lastHeartbeatElapsed;
    private volatile boolean online;

    public AndroidDeviceControlPlane(AndroidActionExecutor executor) {
        if (executor == null) throw new IllegalArgumentException("executor is required");
        this.executor = executor;
    }

    public synchronized AndroidActionExecutor.Result execute(
            String commandId,
            String capability,
            Map<String, Object> arguments,
            long expiresAtEpochSeconds) {
        String id = commandId == null ? "" : commandId.trim();
        if (id.isEmpty()) {
            return AndroidActionExecutor.Result.rejected(capability, "command_id is required");
        }
        long nowSeconds = System.currentTimeMillis() / 1000L;
        if (expiresAtEpochSeconds <= nowSeconds) {
            return AndroidActionExecutor.Result.rejected(capability, "command expired");
        }
        if (!AndroidCapabilityRegistry.isAllowed(capability)) {
            return AndroidActionExecutor.Result.rejected(capability, "capability is not allowlisted");
        }

        purgeOldEntries();
        if (completedCommands.containsKey(id)) {
            return AndroidActionExecutor.Result.rejected(capability, "duplicate command rejected by idempotency guard");
        }

        AndroidActionExecutor.Result result = executor.execute(
                capability,
                arguments == null ? Collections.emptyMap() : arguments);
        if (result.accepted) completedCommands.put(id, System.currentTimeMillis());
        return result;
    }

    public void markTransportState(boolean connected) {
        online = connected;
        if (connected) lastHeartbeatElapsed = SystemClock.elapsedRealtime();
    }

    public boolean isOnline() { return online; }

    public long millisSinceHeartbeat() {
        long heartbeat = lastHeartbeatElapsed;
        return heartbeat == 0 ? Long.MAX_VALUE : SystemClock.elapsedRealtime() - heartbeat;
    }

    public JSONObject describe(String deviceId) {
        JSONObject out = new JSONObject();
        try {
            out.put("device_id", deviceId == null ? "" : deviceId);
            out.put("online", online);
            out.put("heartbeat_age_ms", millisSinceHeartbeat());
            JSONArray capabilities = new JSONArray();
            Set<String> allowed = AndroidCapabilityRegistry.all();
            for (String capability : allowed) capabilities.put(capability);
            out.put("capabilities", capabilities);
            out.put("ui_observation", UiObservationService.isConnected());
        } catch (Exception ignored) {
            // JSONObject.put does not normally fail for these values.
        }
        return out;
    }

    private void purgeOldEntries() {
        long cutoff = System.currentTimeMillis() - DEFAULT_COMMAND_TTL_MS * 4L;
        completedCommands.entrySet().removeIf(e -> e.getValue() < cutoff);
    }
}
