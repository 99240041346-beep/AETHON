package ai.aethon.android;

import android.app.Activity;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.Gravity;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public final class MainActivity extends Activity {
    private final Handler handler = new Handler(Looper.getMainLooper());
    private TextView status;
    private EditText apiUrl;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(32, 48, 32, 32);
        root.setGravity(Gravity.CENTER_HORIZONTAL);

        TextView title = new TextView(this);
        title.setText("AETHON");
        title.setTextSize(32);
        title.setGravity(Gravity.CENTER);
        root.addView(title, new LinearLayout.LayoutParams(-1, -2));

        TextView subtitle = new TextView(this);
        subtitle.setText("Think. Create. Act.\nAndroid Device Client");
        subtitle.setTextSize(16);
        subtitle.setGravity(Gravity.CENTER);
        root.addView(subtitle, new LinearLayout.LayoutParams(-1, -2));

        apiUrl = new EditText(this);
        apiUrl.setHint("AETHON API URL");
        apiUrl.setSingleLine(true);
        apiUrl.setText("http://10.0.2.2:8000");
        root.addView(apiUrl, new LinearLayout.LayoutParams(-1, -2));

        Button health = new Button(this);
        health.setText("Check AETHON API");
        health.setOnClickListener(v -> checkHealth());
        root.addView(health, new LinearLayout.LayoutParams(-1, -2));

        TextView device = new TextView(this);
        device.setText(deviceInfo());
        device.setTextSize(15);
        device.setPadding(0, 24, 0, 16);
        root.addView(device, new LinearLayout.LayoutParams(-1, -2));

        status = new TextView(this);
        status.setText("Status: ready\nNo privileged device capability is enabled.");
        status.setTextSize(15);
        root.addView(status, new LinearLayout.LayoutParams(-1, -2));

        ScrollView scroll = new ScrollView(this);
        scroll.addView(root);
        setContentView(scroll);
    }

    private String deviceInfo() {
        return "Device\n"
                + "Manufacturer: " + Build.MANUFACTURER + "\n"
                + "Model: " + Build.MODEL + "\n"
                + "Android: " + Build.VERSION.RELEASE + " (API " + Build.VERSION.SDK_INT + ")";
    }

    private void checkHealth() {
        final String base = apiUrl.getText().toString().trim().replaceAll("/+$", "");
        status.setText("Status: checking…");
        new Thread(() -> {
            HttpURLConnection connection = null;
            try {
                URL url = new URL(base + "/health");
                connection = (HttpURLConnection) url.openConnection();
                connection.setRequestMethod("GET");
                connection.setConnectTimeout(5000);
                connection.setReadTimeout(5000);
                int code = connection.getResponseCode();
                BufferedReader reader = new BufferedReader(new InputStreamReader(connection.getInputStream()));
                StringBuilder body = new StringBuilder();
                String line;
                while ((line = reader.readLine()) != null) body.append(line);
                String result = "HTTP " + code + "\n" + body;
                handler.post(() -> status.setText("Status: API reachable\n" + result));
            } catch (Exception e) {
                handler.post(() -> status.setText("Status: connection failed\n" + e.getClass().getSimpleName() + ": " + e.getMessage()));
            } finally {
                if (connection != null) connection.disconnect();
            }
        }).start();
    }
}
