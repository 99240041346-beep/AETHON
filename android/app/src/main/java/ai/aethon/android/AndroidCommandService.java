package ai.aethon.android;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.os.Build;
import android.os.IBinder;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.Collections;
import java.util.Map;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

/**
 * Authenticated Android command transport. It polls the bounded cloud queue,
 * delegates only to AndroidActionExecutor, and reports the executor's actual
 * verification state. It never accepts arbitrary shell commands or intents.
 */
public final class AndroidCommandService extends Service {
    private static final String CHANNEL_ID = "aethon_commands";
    private static final int NOTIFICATION_ID = 4101;
    private static final String EXTRA_BASE_URL = "base_url";
    private static final String EXTRA_DEVICE_ID = "device_id";
    private static final String EXTRA_DEVICE_TOKEN = "device_token";
    private static final long POLL_MS = 2000L;

    private ScheduledExecutorService executor;
    private volatile String baseUrl;
    private volatile String deviceId;
    private volatile String deviceToken;
    private AndroidActionExecutor actionExecutor;

    public static void start(Context context, String baseUrl, String deviceId, String deviceToken) {
        if (baseUrl == null || deviceId == null || deviceToken == null
                || baseUrl.trim().isEmpty() || deviceId.trim().isEmpty() || deviceToken.length() < 20) {
            throw new IllegalArgumentException("Valid base URL, device ID and device token are required");
        }
        Intent intent = new Intent(context, AndroidCommandService.class);
        intent.putExtra(EXTRA_BASE_URL, baseUrl.trim().replaceAll("/+$", ""));
        intent.putExtra(EXTRA_DEVICE_ID, deviceId.trim());
        intent.putExtra(EXTRA_DEVICE_TOKEN, deviceToken);
        if (Build.VERSION.SDK_INT >= 26) context.startForegroundService(intent);
        else context.startService(intent);
    }

    public static void stop(Context context) {
        context.stopService(new Intent(context, AndroidCommandService.class));
    }

    @Override public void onCreate() {
        super.onCreate();
        actionExecutor = new AndroidActionExecutor(this);
        createChannel();
        startForeground(NOTIFICATION_ID, notification("Device command link starting"));
    }

    @Override public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent == null) return START_NOT_STICKY;
        baseUrl = intent.getStringExtra(EXTRA_BASE_URL);
        deviceId = intent.getStringExtra(EXTRA_DEVICE_ID);
        deviceToken = intent.getStringExtra(EXTRA_DEVICE_TOKEN);
        if (baseUrl == null || deviceId == null || deviceToken == null || deviceToken.length() < 20) {
            stopSelf();
            return START_NOT_STICKY;
        }
        if (executor == null || executor.isShutdown()) {
            executor = Executors.newSingleThreadScheduledExecutor();
            executor.scheduleWithFixedDelay(this::pollOnce, 0, POLL_MS, TimeUnit.MILLISECONDS);
        }
        return START_STICKY;
    }

    private void pollOnce() {
        try {
            JSONObject command = getNext();
            if (command == null) return;
            long now = System.currentTimeMillis() / 1000L;
            if (command.optDouble("expires_at", 0) <= now) return;
            String capability = command.optString("capability", "");
            JSONObject argumentsJson = command.optJSONObject("arguments");
            Map<String, Object> arguments = argumentsJson == null ? Collections.emptyMap() : JsonObjectArguments.toMap(argumentsJson);
            AndroidActionExecutor.Result result = actionExecutor.execute(capability, arguments);
            postResult(command.optString("command_id", ""), result);
        } catch (Exception ignored) {
            // Transport failures are retried on the next bounded polling interval.
            // No action is reported as successful unless its executor verified it.
        }
    }

    private JSONObject getNext() throws Exception {
        HttpURLConnection connection = (HttpURLConnection) new URL(
                baseUrl + "/v1/android/commands/" + encode(deviceId) + "/next").openConnection();
        connection.setRequestMethod("GET");
        connection.setConnectTimeout(5000);
        connection.setReadTimeout(8000);
        connection.setRequestProperty("Authorization", "Bearer " + deviceToken);
        int code = connection.getResponseCode();
        if (code == 401) return null;
        if (code >= 400) throw new IllegalStateException("poll HTTP " + code);
        String body = read(connection);
        JSONObject response = new JSONObject(body);
        return response.isNull("command") ? null : response.getJSONObject("command");
    }

    private void postResult(String commandId, AndroidActionExecutor.Result result) throws Exception {
        if (commandId.isEmpty()) return;
        HttpURLConnection connection = (HttpURLConnection) new URL(
                baseUrl + "/v1/android/commands/" + encode(deviceId) + "/result").openConnection();
        connection.setRequestMethod("POST");
        connection.setDoOutput(true);
        connection.setConnectTimeout(5000);
        connection.setReadTimeout(8000);
        connection.setRequestProperty("Authorization", "Bearer " + deviceToken);
        connection.setRequestProperty("Content-Type", "application/json; charset=UTF-8");
        JSONObject body = new JSONObject();
        body.put("command_id", commandId);
        body.put("success", result.accepted && result.verified);
        body.put("verified", result.verified);
        body.put("result", new JSONObject(result.data));
        body.put("verification", new JSONObject().put("verified", result.verified));
        if (!result.accepted) body.put("error", result.message);
        try (OutputStream out = connection.getOutputStream()) {
            out.write(body.toString().getBytes(StandardCharsets.UTF_8));
        }
        int code = connection.getResponseCode();
        if (code >= 400) throw new IllegalStateException("result HTTP " + code);
        connection.disconnect();
    }

    private static String read(HttpURLConnection connection) throws Exception {
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(
                connection.getInputStream(), StandardCharsets.UTF_8))) {
            StringBuilder body = new StringBuilder();
            String line;
            while ((line = reader.readLine()) != null) body.append(line);
            return body.toString();
        } finally {
            connection.disconnect();
        }
    }

    private static String encode(String value) { return value.replace("%", "%25").replace("/", "%2F"); }

    private void createChannel() {
        if (Build.VERSION.SDK_INT < 26) return;
        NotificationManager manager = getSystemService(NotificationManager.class);
        manager.createNotificationChannel(new NotificationChannel(CHANNEL_ID, "AETHON device commands", NotificationManager.IMPORTANCE_LOW));
    }

    private Notification notification(String text) {
        if (Build.VERSION.SDK_INT >= 26) {
            return new Notification.Builder(this, CHANNEL_ID).setContentTitle("AETHON").setContentText(text)
                    .setSmallIcon(android.R.drawable.ic_dialog_info).setOngoing(true).build();
        }
        return new Notification.Builder(this).setContentTitle("AETHON").setContentText(text)
                .setSmallIcon(android.R.drawable.ic_dialog_info).setOngoing(true).build();
    }

    @Override public void onDestroy() {
        if (executor != null) executor.shutdownNow();
        executor = null;
        super.onDestroy();
    }

    @Override public IBinder onBind(Intent intent) { return null; }
}
