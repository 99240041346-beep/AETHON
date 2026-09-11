package ai.aethon.android;

import android.accessibilityservice.AccessibilityService;
import android.os.Bundle;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityNodeInfo;

import org.json.JSONArray;
import org.json.JSONObject;

/**
 * User-enabled AccessibilityService for bounded semantic observation and interaction.
 * It never executes shell commands, root operations, or arbitrary coordinate injection.
 */
public final class UiObservationService extends AccessibilityService {
    private static volatile UiObservationService instance;

    @Override public void onServiceConnected() { super.onServiceConnected(); instance = this; }
    @Override public void onAccessibilityEvent(AccessibilityEvent event) { }
    @Override public void onInterrupt() { }
    @Override public void onDestroy() { if (instance == this) instance = null; super.onDestroy(); }

    public static boolean isConnected() { return instance != null; }

    public static JSONObject snapshot(int maxNodes) {
        UiObservationService service = instance;
        JSONObject result = new JSONObject();
        if (service == null) { try { result.put("connected", false); } catch (Exception ignored) {} return result; }
        try {
            result.put("connected", true);
            AccessibilityNodeInfo root = service.getRootInActiveWindow();
            if (root == null) { result.put("node_count", 0); result.put("nodes", new JSONArray()); return result; }
            JSONArray nodes = new JSONArray();
            int[] count = {0};
            collect(root, nodes, count, Math.max(1, Math.min(maxNodes, 250)));
            result.put("node_count", count[0]); result.put("nodes", nodes);
        } catch (Exception ex) {
            try { result.put("error", "Unable to read active window"); } catch (Exception ignored) {}
        }
        return result;
    }

    public static JSONObject click(String text, String description, String className, String packageName) {
        return performOnMatch(text, description, className, packageName, Action.CLICK, null);
    }

    public static JSONObject setText(String text, String description, String className, String packageName, String value) {
        if (value == null || value.length() > 2000) return error("Text value is missing or too long");
        return performOnMatch(text, description, className, packageName, Action.TEXT, value);
    }

    public static JSONObject scroll(String text, String description, String className, String packageName, boolean forward) {
        return performOnMatch(text, description, className, packageName, forward ? Action.SCROLL_FORWARD : Action.SCROLL_BACKWARD, null);
    }

    public static JSONObject back() {
        UiObservationService service = instance;
        if (service == null) return error("Accessibility service is not enabled");
        boolean ok = service.performGlobalAction(GLOBAL_ACTION_BACK);
        return result(ok, "Back navigation requested", "global_back");
    }

    private enum Action { CLICK, TEXT, SCROLL_FORWARD, SCROLL_BACKWARD }

    private static JSONObject performOnMatch(String text, String description, String className, String packageName, Action action, String value) {
        UiObservationService service = instance;
        if (service == null) return error("Accessibility service is not enabled");
        if (blank(text) && blank(description) && blank(className) && blank(packageName)) return error("At least one semantic selector is required");
        AccessibilityNodeInfo root = service.getRootInActiveWindow();
        if (root == null) return error("No active accessible window is available");

        AccessibilityNodeInfo[] matches = new AccessibilityNodeInfo[2];
        int[] matchCount = {0};
        collectMatches(root, text, description, className, packageName, matches, matchCount);
        if (matchCount[0] == 0) return error("No matching accessible UI node found");
        if (matchCount[0] > 1) return error("Multiple matching accessible UI nodes found; action refused");

        AccessibilityNodeInfo target = matches[0];
        boolean ok = false;
        switch (action) {
            case CLICK: ok = target.isEnabled() && target.isClickable() && target.performAction(AccessibilityNodeInfo.ACTION_CLICK); break;
            case TEXT:
                if (target.isEnabled() && target.isEditable()) {
                    Bundle args = new Bundle();
                    args.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, value);
                    ok = target.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args);
                }
                break;
            case SCROLL_FORWARD: ok = target.isEnabled() && target.isScrollable() && target.performAction(AccessibilityNodeInfo.ACTION_SCROLL_FORWARD); break;
            case SCROLL_BACKWARD: ok = target.isEnabled() && target.isScrollable() && target.performAction(AccessibilityNodeInfo.ACTION_SCROLL_BACKWARD); break;
        }
        target.recycle();
        return result(ok, ok ? "UI action requested" : "UI action was rejected by Android", action.name().toLowerCase());
    }

    private static void collectMatches(AccessibilityNodeInfo node, String text, String description, String className, String packageName,
                                       AccessibilityNodeInfo[] matches, int[] matchCount) {
        if (node == null || matchCount[0] > 1) return;
        if (matches(node, text, description, className, packageName)) {
            matchCount[0]++;
            if (matchCount[0] <= 2) matches[matchCount[0] - 1] = AccessibilityNodeInfo.obtain(node);
            if (matchCount[0] > 1) return;
        }
        for (int i = 0; i < node.getChildCount() && matchCount[0] <= 1; i++) {
            collectMatches(node.getChild(i), text, description, className, packageName, matches, matchCount);
        }
    }

    private static boolean matches(AccessibilityNodeInfo node, String text, String description, String className, String packageName) {
        return matchesValue(text, node.getText()) && matchesValue(description, node.getContentDescription())
                && matchesValue(className, node.getClassName()) && matchesValue(packageName, node.getPackageName());
    }

    private static boolean matchesValue(String expected, CharSequence actual) {
        return blank(expected) || (actual != null && expected.contentEquals(actual));
    }

    private static boolean blank(String value) { return value == null || value.trim().isEmpty(); }

    private static JSONObject result(boolean ok, String message, String action) {
        JSONObject result = new JSONObject();
        try { result.put("success", ok); result.put("message", message); result.put("action", action); } catch (Exception ignored) {}
        return result;
    }

    private static JSONObject error(String message) { return result(false, message, "none"); }

    private static void collect(AccessibilityNodeInfo node, JSONArray out, int[] count, int limit) throws Exception {
        if (node == null || count[0] >= limit) return;
        JSONObject item = new JSONObject();
        CharSequence text = node.getText(), desc = node.getContentDescription(), cls = node.getClassName(), pkg = node.getPackageName();
        item.put("index", count[0]++);
        if (cls != null) item.put("class", cls.toString());
        if (pkg != null) item.put("package", pkg.toString());
        if (text != null) item.put("text", truncate(text.toString(), 300));
        if (desc != null) item.put("description", truncate(desc.toString(), 300));
        item.put("clickable", node.isClickable()); item.put("scrollable", node.isScrollable());
        item.put("editable", node.isEditable()); item.put("enabled", node.isEnabled()); out.put(item);
        for (int i = 0; i < node.getChildCount() && count[0] < limit; i++) collect(node.getChild(i), out, count, limit);
    }

    private static String truncate(String value, int max) { return value.length() <= max ? value : value.substring(0, max); }
}
