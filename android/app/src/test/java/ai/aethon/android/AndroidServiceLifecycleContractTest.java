package ai.aethon.android;

import org.junit.Test;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

import static org.junit.Assert.assertTrue;

public final class AndroidServiceLifecycleContractTest {
    private static String read(String relative) throws Exception {
        Path path = Paths.get("src/main", relative);
        return Files.readString(path);
    }

    @Test
    public void manifestDeclaresNonExportedDataSyncService() throws Exception {
        String manifest = read("AndroidManifest.xml");
        assertTrue(manifest.contains("android:name=\".AndroidCommandService\""));
        assertTrue(manifest.contains("android:exported=\"false\""));
        assertTrue(manifest.contains("android:foregroundServiceType=\"dataSync\""));
    }

    @Test
    public void activityStartsAndStopsService() throws Exception {
        String activity = read("java/ai/aethon/android/MainActivity.java");
        assertTrue(activity.contains("AndroidCommandService.start(this,base,id,token)"));
        assertTrue(activity.contains("AndroidCommandService.stop(this)"));
    }
}
