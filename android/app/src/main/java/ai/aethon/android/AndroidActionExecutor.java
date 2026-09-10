package ai.aethon.android;

import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.hardware.camera2.CameraAccessException;
import android.hardware.camera2.CameraCharacteristics;
import android.hardware.camera2.CameraManager;
import android.media.AudioManager;
import android.os.BatteryManager;
import android.os.Build;

import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

/**
 * Executes only explicitly allowlisted, bounded Android actions and reports whether
 * the observable result was actually verified. No shell, root, accessibility
 * injection, or arbitrary Intent execution is exposed here.
 */
public final class AndroidActionExecutor {
    public static final class Result {
        public final boolean accepted;
        public final boolean verified;
        public final String capability;
        public final String message;
        public final Map<String, Object> data;

        private Result(boolean accepted, boolean verified, String capability,
                       String message, Map<String, Object> data) {
            this.accepted = accepted;
            this.verified = verified;
            this.capability = capability;
            this.message = message;
            this.data = data == null ? Collections.emptyMap() : Collections.unmodifiableMap(data);
        }

        static Result rejected(String capability, String message) {
            return new Result(false, false, capability, message, null);
        }

        static Result success(String capability, String message, Map<String, Object> data) {
            return new Result(true, true, capability, message, data);
        }

        static Result acceptedUnverified(String capability, String message, Map<String, Object> data) {
            return new Result(true, false, capability, message, data);
        }
    }

    private final Context context;

    public AndroidActionExecutor(Context context) {
        this.context = context.getApplicationContext();
    }

    public Result execute(String capability, Map<String, Object> arguments) {
        if (!AndroidCapabilityRegistry.isAllowed(capability)) {
            return Result.rejected(capability, "Capability is not allowlisted");
        }
        Map<String, Object> args = arguments == null ? Collections.emptyMap() : arguments;
        switch (capability) {
            case AndroidCapabilityRegistry.OPEN_APP:
                return openApp(stringArg(args, "package_name"));
            case AndroidCapabilityRegistry.BATTERY_READ:
                return batteryRead();
            case AndroidCapabilityRegistry.VOLUME_READ:
                return volumeRead();
            case AndroidCapabilityRegistry.VOLUME_SET:
                return volumeSet(numberArg(args, "level"));
            case AndroidCapabilityRegistry.FLASHLIGHT_ON:
                return flashlight(true);
            case AndroidCapabilityRegistry.FLASHLIGHT_OFF:
                return flashlight(false);
            case AndroidCapabilityRegistry.MEDIA_PLAY:
                return mediaKey(AndroidCapabilityRegistry.MEDIA_PLAY, android.view.KeyEvent.KEYCODE_MEDIA_PLAY);
            case AndroidCapabilityRegistry.MEDIA_PAUSE:
                return mediaKey(AndroidCapabilityRegistry.MEDIA_PAUSE, android.view.KeyEvent.KEYCODE_MEDIA_PAUSE);
            case AndroidCapabilityRegistry.MEDIA_STOP:
                return mediaKey(AndroidCapabilityRegistry.MEDIA_STOP, android.view.KeyEvent.KEYCODE_MEDIA_STOP);
            case AndroidCapabilityRegistry.DEVICE_INFO:
                return deviceInfo();
            default:
                return Result.rejected(capability, "Capability is registered but not executable on this Android client yet");
        }
    }

    private Result openApp(String packageName) {
        if (packageName == null || packageName.length() > 200 || packageName.indexOf(' ') >= 0) {
            return Result.rejected(AndroidCapabilityRegistry.OPEN_APP, "Invalid package name");
        }
        PackageManager pm = context.getPackageManager();
        Intent launch = pm.getLaunchIntentForPackage(packageName);
        if (launch == null) {
            return Result.rejected(AndroidCapabilityRegistry.OPEN_APP, "Application is not installed or launchable");
        }
        launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        try {
            context.startActivity(launch);
        } catch (RuntimeException ex) {
            return Result.rejected(AndroidCapabilityRegistry.OPEN_APP, "Android rejected app launch");
        }
        Map<String, Object> data = new HashMap<>();
        data.put("package_name", packageName);
        data.put("launch_intent_available", true);
        // Package launchability is verified; foreground visibility is intentionally
        // left to the future device observation channel.
        return Result.success(AndroidCapabilityRegistry.OPEN_APP, "Application launch requested", data);
    }

    private Result batteryRead() {
        BatteryManager bm = (BatteryManager) context.getSystemService(Context.BATTERY_SERVICE);
        if (bm == null) return Result.rejected(AndroidCapabilityRegistry.BATTERY_READ, "Battery service unavailable");
        int level = bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY);
        if (level < 0 || level > 100) return Result.rejected(AndroidCapabilityRegistry.BATTERY_READ, "Battery level unavailable");
        Map<String, Object> data = new HashMap<>();
        data.put("percent", level);
        return Result.success(AndroidCapabilityRegistry.BATTERY_READ, "Battery level read", data);
    }

    private Result volumeRead() {
        AudioManager audio = (AudioManager) context.getSystemService(Context.AUDIO_SERVICE);
        if (audio == null) return Result.rejected(AndroidCapabilityRegistry.VOLUME_READ, "Audio service unavailable");
        int stream = AudioManager.STREAM_MUSIC;
        Map<String, Object> data = new HashMap<>();
        data.put("stream", "music");
        data.put("level", audio.getStreamVolume(stream));
        data.put("max", audio.getStreamMaxVolume(stream));
        return Result.success(AndroidCapabilityRegistry.VOLUME_READ, "Music volume read", data);
    }

    private Result volumeSet(Number requested) {
        if (requested == null) return Result.rejected(AndroidCapabilityRegistry.VOLUME_SET, "Volume level is required");
        AudioManager audio = (AudioManager) context.getSystemService(Context.AUDIO_SERVICE);
        if (audio == null) return Result.rejected(AndroidCapabilityRegistry.VOLUME_SET, "Audio service unavailable");
        int max = audio.getStreamMaxVolume(AudioManager.STREAM_MUSIC);
        int level = Math.max(0, Math.min(max, requested.intValue()));
        audio.setStreamVolume(AudioManager.STREAM_MUSIC, level, 0);
        boolean verified = audio.getStreamVolume(AudioManager.STREAM_MUSIC) == level;
        if (!verified) return Result.rejected(AndroidCapabilityRegistry.VOLUME_SET, "Volume change could not be verified");
        Map<String, Object> data = new HashMap<>();
        data.put("level", level);
        data.put("max", max);
        return Result.success(AndroidCapabilityRegistry.VOLUME_SET, "Music volume updated", data);
    }

    private Result flashlight(boolean enabled) {
        String capability = enabled ? AndroidCapabilityRegistry.FLASHLIGHT_ON : AndroidCapabilityRegistry.FLASHLIGHT_OFF;
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.M) {
            return Result.rejected(capability, "Flashlight control requires Android 6.0 or newer");
        }
        CameraManager camera = (CameraManager) context.getSystemService(Context.CAMERA_SERVICE);
        if (camera == null) return Result.rejected(capability, "Camera service unavailable");
        try {
            String selected = null;
            for (String id : camera.getCameraIdList()) {
                CameraCharacteristics characteristics = camera.getCameraCharacteristics(id);
                Boolean flash = characteristics.get(CameraCharacteristics.FLASH_INFO_AVAILABLE);
                if (Boolean.TRUE.equals(flash)) {
                    selected = id;
                    break;
                }
            }
            if (selected == null) return Result.rejected(capability, "No camera with flash is available");
            camera.setTorchMode(selected, enabled);
            Map<String, Object> data = new HashMap<>();
            data.put("enabled", enabled);
            data.put("camera_id", selected);
            return Result.success(capability, enabled ? "Flashlight enabled" : "Flashlight disabled", data);
        } catch (CameraAccessException | SecurityException ex) {
            return Result.rejected(capability, "Flashlight action was rejected");
        }
    }

    private Result mediaKey(String capability, int keyCode) {
        AudioManager audio = (AudioManager) context.getSystemService(Context.AUDIO_SERVICE);
        if (audio == null) return Result.rejected(capability, "Audio service unavailable");
        audio.dispatchMediaKeyEvent(new android.view.KeyEvent(android.view.KeyEvent.ACTION_DOWN, keyCode));
        audio.dispatchMediaKeyEvent(new android.view.KeyEvent(android.view.KeyEvent.ACTION_UP, keyCode));
        Map<String, Object> data = new HashMap<>();
        data.put("key_code", keyCode);
        // Dispatch is not proof that playback changed. Keep it explicitly unverified.
        return Result.acceptedUnverified(capability, "Media key dispatched; playback requires observation verification", data);
    }

    private Result deviceInfo() {
        Map<String, Object> data = new HashMap<>();
        data.put("manufacturer", Build.MANUFACTURER);
        data.put("model", Build.MODEL);
        data.put("android_version", Build.VERSION.RELEASE);
        data.put("sdk", Build.VERSION.SDK_INT);
        return Result.success(AndroidCapabilityRegistry.DEVICE_INFO, "Device information read", data);
    }

    private static String stringArg(Map<String, Object> args, String key) {
        Object value = args.get(key);
        return value instanceof String ? (String) value : null;
    }

    private static Number numberArg(Map<String, Object> args, String key) {
        Object value = args.get(key);
        return value instanceof Number ? (Number) value : null;
    }
}
