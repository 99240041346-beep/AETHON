package ai.aethon.android;

import android.Manifest;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.os.IBinder;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;

import java.util.ArrayList;
import java.util.Locale;

/**
 * Optional foreground wake listener.
 *
 * Android/browser speech APIs do not provide a universal hardware wake-word
 * primitive, so this service uses bounded SpeechRecognizer sessions. It only
 * emits a local intent after recognizing an explicit wake phrase and never
 * executes a device action itself.
 */
public final class WakeWordService extends Service {
    public static final String ACTION_WAKE = "ai.aethon.android.ACTION_WAKE";
    public static final String EXTRA_COMMAND = "command";
    private static final String CHANNEL = "aethon_wake";
    private SpeechRecognizer recognizer;
    private volatile boolean running;

    @Override public void onCreate() {
        super.onCreate();
        createChannel();
        startForeground(4201, notification("Wake listener active"));
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            stopSelf();
            return;
        }
        if (!SpeechRecognizer.isRecognitionAvailable(this)) {
            stopSelf();
            return;
        }
        recognizer = SpeechRecognizer.createSpeechRecognizer(this);
        recognizer.setRecognitionListener(new RecognitionListener() {
            public void onReadyForSpeech(Bundle b) {}
            public void onBeginningOfSpeech() {}
            public void onRmsChanged(float r) {}
            public void onBufferReceived(byte[] b) {}
            public void onEndOfSpeech() { restart(); }
            public void onError(int e) { restart(); }
            public void onPartialResults(Bundle b) {}
            public void onEvent(int e, Bundle b) {}
            public void onResults(Bundle bundle) {
                ArrayList<String> results = bundle.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
                if (results != null) {
                    for (String value : results) {
                        String command = stripWakePhrase(value);
                        if (command != null) {
                            Intent wake = new Intent(ACTION_WAKE);
                            wake.setPackage(getPackageName());
                            wake.putExtra(EXTRA_COMMAND, command);
                            sendBroadcast(wake);
                            break;
                        }
                    }
                }
                restart();
            }
        });
        running = true;
        startListening();
    }

    private void startListening() {
        if (!running || recognizer == null) return;
        try {
            Intent intent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE, Locale.getDefault().toLanguageTag());
            intent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, false);
            recognizer.startListening(intent);
        } catch (RuntimeException ignored) {
            restart();
        }
    }

    private void restart() {
        if (!running) return;
        new android.os.Handler(getMainLooper()).postDelayed(this::startListening, 650L);
    }

    static String stripWakePhrase(String input) {
        if (input == null) return null;
        String value = input.trim();
        String lower = value.toLowerCase(Locale.ROOT);
        String[] prefixes = {
                "hey assistant", "ok assistant", "okay assistant",
                "hey aethon", "ok aethon", "okay aethon",
                "hey astra", "ok astra", "okay astra"
        };
        for (String prefix : prefixes) {
            if (lower.equals(prefix)) return "";
            if (lower.startsWith(prefix + " ")) return value.substring(prefix.length()).trim();
        }
        return null;
    }

    @Override public int onStartCommand(Intent intent, int flags, int startId) {
        return START_STICKY;
    }

    @Override public void onDestroy() {
        running = false;
        if (recognizer != null) {
            recognizer.destroy();
            recognizer = null;
        }
        super.onDestroy();
    }

    @Override public IBinder onBind(Intent intent) { return null; }

    private void createChannel() {
        if (Build.VERSION.SDK_INT >= 26) {
            NotificationManager manager = getSystemService(NotificationManager.class);
            manager.createNotificationChannel(new NotificationChannel(
                    CHANNEL, "AETHON wake listener", NotificationManager.IMPORTANCE_LOW));
        }
    }

    private Notification notification(String text) {
        if (Build.VERSION.SDK_INT >= 26) {
            return new Notification.Builder(this, CHANNEL)
                    .setContentTitle("AETHON")
                    .setContentText(text)
                    .setSmallIcon(android.R.drawable.ic_btn_speak_now)
                    .setOngoing(true).build();
        }
        return new Notification.Builder(this)
                .setContentTitle("AETHON")
                .setContentText(text)
                .setSmallIcon(android.R.drawable.ic_btn_speak_now)
                .setOngoing(true).build();
    }
}
