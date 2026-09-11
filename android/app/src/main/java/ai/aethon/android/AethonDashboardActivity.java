package ai.aethon.android;

import android.app.Activity;
import android.graphics.Color;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.view.Gravity;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import org.json.JSONObject;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

/**
 * Personal AETHON command center. This is a UI layer over the existing
 * authenticated assistant API; it does not bypass Android permissions or
 * create unrestricted device control.
 */
public final class AethonDashboardActivity extends Activity {
    private final android.os.Handler handler = new android.os.Handler(android.os.Looper.getMainLooper());
    private EditText apiUrl;
    private EditText command;
    private TextView result;

    private int dp(float v) { return (int) (v * getResources().getDisplayMetrics().density + .5f); }
    private TextView text(String value, float size) {
        TextView t = new TextView(this);
        t.setText(value);
        t.setTextSize(size);
        t.setTextColor(Color.rgb(226,232,240));
        t.setPadding(0, dp(5), 0, dp(5));
        return t;
    }
    private GradientDrawable card() {
        GradientDrawable g = new GradientDrawable();
        g.setColor(Color.rgb(24,32,48));
        g.setCornerRadius(dp(20));
        g.setStroke(dp(1), Color.rgb(51,65,85));
        return g;
    }
    private Button action(String label) {
        Button b = new Button(this);
        b.setText(label);
        b.setTextColor(Color.WHITE);
        b.setTextSize(14);
        b.setAllCaps(false);
        b.setMinHeight(dp(52));
        GradientDrawable g = new GradientDrawable(GradientDrawable.Orientation.LEFT_RIGHT,
                new int[]{Color.rgb(37,99,235), Color.rgb(124,58,237)});
        g.setCornerRadius(dp(16));
        b.setBackground(g);
        return b;
    }
    private LinearLayout cardLayout() {
        LinearLayout l = new LinearLayout(this);
        l.setOrientation(LinearLayout.VERTICAL);
        l.setPadding(dp(18), dp(14), dp(18), dp(14));
        l.setBackground(card());
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(-1, -2);
        p.setMargins(0, dp(8), 0, dp(8));
        l.setLayoutParams(p);
        return l;
    }

    @Override protected void onCreate(Bundle state) {
        super.onCreate(state);
        buildUi();
    }

    private void buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(18), dp(24), dp(18), dp(24));
        root.setBackgroundColor(Color.rgb(8,13,24));
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.addView(root);
        setContentView(scroll);

        TextView title = text("AETHON", 32);
        title.setGravity(Gravity.CENTER);
        title.setTypeface(null, 1);
        root.addView(title, new LinearLayout.LayoutParams(-1, -2));
        TextView subtitle = text("PERSONAL AI COMMAND CENTER", 13);
        subtitle.setGravity(Gravity.CENTER);
        subtitle.setTextColor(Color.rgb(129,140,248));
        root.addView(subtitle, new LinearLayout.LayoutParams(-1, -2));

        LinearLayout hero = cardLayout();
        hero.addView(text("●  PERSONAL AGENT ONLINE", 15));
        TextView detail = text("Think • Create • Code • Build • Control • Verify", 14);
        detail.setTextColor(Color.rgb(148,163,184));
        hero.addView(detail);
        root.addView(hero);

        LinearLayout workspace = cardLayout();
        workspace.addView(text("AI Workspace", 19));
        workspace.addView(text("Ask AETHON to plan, write, explain, design or transform an idea.", 13));
        LinearLayout row1 = new LinearLayout(this);
        row1.setOrientation(LinearLayout.HORIZONTAL);
        Button code = action("⌘  Code");
        code.setOnClickListener(v -> preset("Build a complete production-ready software feature. First plan it, then provide the files, code, tests and run instructions."));
        row1.addView(code, new LinearLayout.LayoutParams(0, dp(54), 1));
        Button website = action("◇  Website");
        website.setOnClickListener(v -> preset("Create a complete modern website from my idea. Produce the architecture, UI, frontend, backend/API and database plan, then generate the implementation files."));
        LinearLayout wp = new LinearLayout.LayoutParams(0, dp(54), 1);
        wp.setMargins(dp(8),0,0,0);
        row1.addView(website, wp);
        workspace.addView(row1);
        LinearLayout row2 = new LinearLayout(this);
        row2.setOrientation(LinearLayout.HORIZONTAL);
        Button create = action("✦  Create");
        create.setOnClickListener(v -> preset("Turn my idea into a complete executable project plan with design, implementation, testing and deployment steps."));
        row2.addView(create, new LinearLayout.LayoutParams(0, dp(54), 1));
        Button analyze = action("◎  Analyze");
        analyze.setOnClickListener(v -> preset("Analyze my request deeply, identify requirements and risks, then propose the best implementation."));
        LinearLayout ap = new LinearLayout.LayoutParams(0, dp(54), 1);
        ap.setMargins(dp(8),0,0,0);
        row2.addView(analyze, ap);
        workspace.addView(row2);
        root.addView(workspace);

        LinearLayout device = cardLayout();
        device.addView(text("Android Control", 19));
        device.addView(text("Authorized device actions use AETHON's authenticated, allowlisted and verification-gated channel.", 13));
        Button observe = action("👁  Observe device UI");
        observe.setOnClickListener(v -> preset("Observe my authorized Android device UI and summarize the visible actionable elements. Do not take any action yet."));
        device.addView(observe);
        Button workflow = action("▶  Plan device workflow");
        workflow.setOnClickListener(v -> preset("Plan a safe multi-step workflow for my authorized Android device. Explain each step and request approval before side effects."));
        LinearLayout.LayoutParams f = new LinearLayout.LayoutParams(-1, dp(54));
        f.setMargins(0, dp(8), 0, 0);
        device.addView(workflow, f);
        root.addView(device);

        LinearLayout chat = cardLayout();
        chat.addView(text("Command", 19));
        apiUrl = field("Cloud API URL");
        apiUrl.setText("http://10.0.2.2:8000");
        chat.addView(apiUrl);
        command = field("Tell AETHON what you want…");
        command.setSingleLine(false);
        command.setMinLines(4);
        chat.addView(command, new LinearLayout.LayoutParams(-1, dp(110)));
        Button send = action("➤  Run with AETHON");
        send.setOnClickListener(v -> send());
        chat.addView(send);
        result = text("Ready. No action is claimed until the backend verifies it.", 13);
        result.setTextColor(Color.rgb(148,163,184));
        chat.addView(result);
        root.addView(chat);

        TextView safety = text("🔒 Safety Kernel • authenticated commands • explicit approval for side effects • bounded Android capabilities", 12);
        safety.setTextColor(Color.rgb(100,116,139));
        root.addView(safety);
    }

    private EditText field(String hint) {
        EditText e = new EditText(this);
        e.setHint(hint);
        e.setHintTextColor(Color.rgb(100,116,139));
        e.setTextColor(Color.WHITE);
        e.setTextSize(15);
        e.setPadding(dp(12), dp(10), dp(12), dp(10));
        GradientDrawable g = new GradientDrawable();
        g.setColor(Color.rgb(15,23,42));
        g.setCornerRadius(dp(12));
        g.setStroke(dp(1), Color.rgb(51,65,85));
        e.setBackground(g);
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(-1, dp(52));
        p.setMargins(0, dp(5), 0, dp(5));
        e.setLayoutParams(p);
        return e;
    }

    private void preset(String value) {
        command.setText(value);
        command.setSelection(command.length());
        result.setText("Prompt prepared. Review it, then tap Run with AETHON.");
    }

    private void send() {
        String base = apiUrl.getText().toString().trim().replaceAll("/+$", "");
        String prompt = command.getText().toString().trim();
        if (base.isEmpty() || prompt.isEmpty()) {
            result.setText("Enter an API URL and a request first.");
            return;
        }
        result.setText("AETHON is thinking…");
        new Thread(() -> {
            HttpURLConnection c = null;
            try {
                c = (HttpURLConnection) new URL(base + "/v1/assistant/respond").openConnection();
                c.setRequestMethod("POST");
                c.setDoOutput(true);
                c.setConnectTimeout(8000);
                c.setReadTimeout(30000);
                c.setRequestProperty("Content-Type", "application/json; charset=UTF-8");
                JSONObject body = new JSONObject();
                body.put("text", prompt);
                body.put("language", "auto");
                try (OutputStream out = c.getOutputStream()) {
                    out.write(body.toString().getBytes(StandardCharsets.UTF_8));
                }
                int code = c.getResponseCode();
                BufferedReader rd = new BufferedReader(new InputStreamReader(code >= 400 ? c.getErrorStream() : c.getInputStream(), StandardCharsets.UTF_8));
                StringBuilder b = new StringBuilder();
                String line;
                while ((line = rd.readLine()) != null) b.append(line);
                if (code >= 400) throw new IllegalStateException("HTTP " + code);
                JSONObject response = new JSONObject(b.toString());
                String answer = response.optString("response", "No response");
                handler.post(() -> result.setText(answer));
            } catch (Exception e) {
                handler.post(() -> result.setText("Connection failed: " + e.getMessage() + "\n\nFor a physical phone, use the API server's LAN IP or production HTTPS endpoint, not 10.0.2.2."));
            } finally {
                if (c != null) c.disconnect();
            }
        }).start();
    }
}
