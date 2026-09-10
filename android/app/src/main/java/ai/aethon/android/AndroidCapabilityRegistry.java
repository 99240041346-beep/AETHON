package ai.aethon.android;

import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.Set;

/**
 * Explicit allowlist of Android capabilities exposed to the cloud command layer.
 * This registry intentionally contains no shell or arbitrary automation capability.
 */
public final class AndroidCapabilityRegistry {
    public static final String SCREEN_READ = "SCREEN_READ";
    public static final String APP_LIST = "APP_LIST";
    public static final String DEVICE_INFO = "DEVICE_INFO";
    public static final String NETWORK_STATUS = "NETWORK_STATUS";
    public static final String BATTERY_READ = "BATTERY_READ";
    public static final String VOLUME_READ = "VOLUME_READ";
    public static final String OPEN_APP = "OPEN_APP";
    public static final String MEDIA_PLAY = "MEDIA_PLAY";
    public static final String MEDIA_PAUSE = "MEDIA_PAUSE";
    public static final String MEDIA_STOP = "MEDIA_STOP";
    public static final String VOLUME_SET = "VOLUME_SET";
    public static final String FLASHLIGHT_ON = "FLASHLIGHT_ON";
    public static final String FLASHLIGHT_OFF = "FLASHLIGHT_OFF";
    public static final String SCREEN_CAPTURE = "SCREEN_CAPTURE";

    private static final Set<String> ALLOWED;
    static {
        LinkedHashSet<String> values = new LinkedHashSet<>();
        Collections.addAll(values,
                SCREEN_READ, APP_LIST, DEVICE_INFO, NETWORK_STATUS,
                BATTERY_READ, VOLUME_READ, OPEN_APP, MEDIA_PLAY,
                MEDIA_PAUSE, MEDIA_STOP, VOLUME_SET, FLASHLIGHT_ON,
                FLASHLIGHT_OFF, SCREEN_CAPTURE);
        ALLOWED = Collections.unmodifiableSet(values);
    }

    private AndroidCapabilityRegistry() {}

    public static boolean isAllowed(String capability) {
        return capability != null && ALLOWED.contains(capability);
    }

    public static Set<String> all() {
        return ALLOWED;
    }
}
