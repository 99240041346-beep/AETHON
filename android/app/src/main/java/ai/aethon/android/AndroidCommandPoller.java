package ai.aethon.android;

import android.content.Context;
import android.os.Handler;
import android.os.Looper;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.Collections;
import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Activity-scoped transport bridge. It is intentionally bounded to the cloud
 * command queue and AndroidActionExecutor. A background/foreground service can
 * adopt this same client later without changing the command contract.
 */
public final class AndroidCommandPoller {
    public interface Listener {
        void onStatus(String status);
        void onAction(AndroidActionExecutor.Result result, String commandId);
    }

    private final Context context;
    private final Listener listener;
    private final Handler main = new Handler(Looper.getMainLooper());
    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private final AndroidActionExecutor actionExecutor;
    private volatile boolean running;
    private volatile String baseUrl;
    private volatile String deviceId;
    private volatile String deviceToken;

    public AndroidCommandPoller(Context context, Listener listener) {
        this.context = context.getApplicationContext();
        this.listener = listener;
        this.actionExecutor = new AndroidActionExecutor(context);
    }

    public synchronized void start(String baseUrl, String deviceId, String deviceToken) {
        if (baseUrl == null || deviceId == null || deviceToken == null
                || baseUrl.trim().isEmpty() || deviceId.trim().isEmpty() || deviceToken.length() < 20) {
            throw new IllegalArgumentException("Valid base URL, device ID and device token are required");
        }
        stop();
        this.baseUrl = baseUrl.trim().replaceAll("/+$", "");
        this.deviceId = deviceId.trim();
        this.deviceToken = deviceToken;
        running = true;
        pollLoop();
    }

    public synchronized void stop() {
        running = false;
        main.removeCallbacksAndMessages(null);
    }

    private void pollLoop() {
        if (!running) return;
        worker.execute(() -> {
            try {
                JSONObject command = getNext();
                if (command != null) executeAndReport(command);
                postStatus(command == null ? "Device link online • waiting for commands" : "Command processed");
            } catch (Exception ex) {
                postStatus("Device link error • retrying");
            } finally {
                if (running) main.postDelayed(this::pollLoop, 2000L);
            }
        });
    }

    private JSONObject getNext() throws Exception {
        HttpURLConnection c = connection("/v1/android/commands/" + encode(deviceId) + "/next", "GET");
        int code = c.getResponseCode();
        if (code == 401) throw new SecurityException("device authentication failed");
        if (code >= 400) throw new IllegalStateException("poll HTTP " + code);
        JSONObject response = new JSONObject(read(c));
        c.disconnect();
        return response.isNull("command") ? null : response.getJSONObject("command");
    }

    private void executeAndReport(JSONObject command) throws Exception {
        String commandId = command.optString("command_id", "");
        long now = System.currentTimeMillis() / 1000L;
        if (commandId.isEmpty() || command.optDouble("expires_at", 0) <= now) return;
        String capability = command.optString("capability", "");
        JSONObject jsonArgs = command.optJSONObject("arguments");
        Map<String, Object> args = jsonArgs == null ? Collections.emptyMap() : JsonObjectArguments.toMap(jsonArgs);
        AndroidActionExecutor.Result result = actionExecutor.execute(capability, args);
        postResult(commandId, result);
        main.post(() -> listener.onAction(result, commandId));
    }

    private void postResult(String commandId, AndroidActionExecutor.Result result) throws Exception {
        HttpURLConnection c = connection("/v1/android/commands/" + encode(deviceId) + "/result", "POST");
        c.setDoOutput(true);
        c.setRequestProperty("Content-Type", "application/json; charset=UTF-8");
        JSONObject body = new JSONObject();
        body.put("command_id", commandId);
        body.put("success", result.accepted && result.verified);
        body.put("verified", result.verified);
        body.put("result", new JSONObject(result.data));
        body.put("verification", new JSONObject().put("verified", result.verified));
        if (!result.accepted) body.put("error", result.message);
        try (OutputStream out = c.getOutputStream()) {
            out.write(body.toString().getBytes(StandardCharsets.UTF_8));
        }
        int code = c.getResponseCode();
        c.disconnect();
        if (code >= 400) throw new IllegalStateException("result HTTP " + code);
    }

    private HttpURLConnection connection(String path, String method) throws Exception {
        HttpURLConnection c = (HttpURLConnection) new URL(baseUrl + path).openConnection();
        c.setRequestMethod(method);
        c.setConnectTimeout(5000);
        c.setReadTimeout(8000);
        c.setRequestProperty("Authorization", "Bearer " + deviceToken);
        return c;
    }

    private static String read(HttpURLConnection c) throws Exception {
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(c.getInputStream(), StandardCharsets.UTF_8))) {
            StringBuilder b = new StringBuilder();
            String line;
            while ((line = reader.readLine()) != null) b.append(line);
            return b.toString();
        }
    }

    private static String encode(String value) { return value.replace("%", "%25").replace("/", "%2F"); }

    private void postStatus(String value) { main.post(() -> listener.onStatus(value)); }

    public void close() {
        stop();
        worker.shutdownNow();
        deviceToken = null;
    }
}
