package ai.aethon.android;

import android.accessibilityservice.AccessibilityService;
import android.view.accessibility.AccessibilityNodeInfo;
import android.view.accessibility.AccessibilityEvent;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.List;

/**
 * Optional, user-enabled Android accessibility observer.
 * It exposes a bounded semantic snapshot only; it does not inject input.
 */
public final class UiObservationService extends AccessibilityService {
    private static volatile UiObservationService instance;

    @Override public void onServiceConnected() {
        super.onServiceConnected();
        instance = this;
    }

    @Override public void onAccessibilityEvent(AccessibilityEvent event) { }

    @Override public void onInterrupt() { }

    @Override public void onDestroy() {
        if (instance == this) instance = null;
        super.onDestroy();
    }

    public static boolean isConnected() { return instance != null; }

    public static JSONObject snapshot(int maxNodes) {
        UiObservationService service = instance;
        JSONObject result = new JSONObject();
        if (service == null) {
            try { result.put("connected", false); } catch (Exception ignored) { }
            return result;
        }
        try {
            result.put("connected", true);
            AccessibilityNodeInfo root = service.getRootInActiveWindow();
            if (root == null) {
                result.put("node_count", 0);
                result.put("nodes", new JSONArray());
                return result;
            }
            JSONArray nodes = new JSONArray();
            int[] count = {0};
            collect(root, nodes, count, Math.max(1, Math.min(maxNodes, 250)));
            result.put("node_count", count[0]);
            result.put("nodes", nodes);
        } catch (Exception ex) {
            try { result.put("error", "Unable to read active window"); } catch (Exception ignored) { }
        }
        return result;
    }

    private static void collect(AccessibilityNodeInfo node, JSONArray out, int[] count, int limit) throws Exception {
        if (node == null || count[0] >= limit) return;
        JSONObject item = new JSONObject();
        CharSequence text = node.getText();
        CharSequence desc = node.getContentDescription();
        CharSequence className = node.getClassName();
        CharSequence packageName = node.getPackageName();
        item.put("index", count[0]++);
        if (className != null) item.put("class", className.toString());
        if (packageName != null) item.put("package", packageName.toString());
        if (text != null) item.put("text", truncate(text.toString(), 300));
        if (desc != null) item.put("description", truncate(desc.toString(), 300));
        item.put("clickable", node.isClickable());
        item.put("scrollable", node.isScrollable());
        item.put("enabled", node.isEnabled());
        out.put(item);
        for (int i = 0; i < node.getChildCount() && count[0] < limit; i++) {
            collect(node.getChild(i), out, count, limit);
        }
    }

    private static String truncate(String value, int max) {
        return value.length() <= max ? value : value.substring(0, max);
    }
}
