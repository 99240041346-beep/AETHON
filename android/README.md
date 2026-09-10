# AETHON Android Device Client

The Android module is the first device-side client for AETHON. It is intentionally bounded: the current build exposes API connectivity, read-only device metadata, and a Telugu voice input/output layer.

## Telugu voice interface

- Tap **Speak to AETHON** and speak naturally in Telugu (`te-IN`).
- Android's `SpeechRecognizer` converts speech into text and places the transcript in the input field.
- Tap **AETHON Voice** to read the transcript aloud with Android `TextToSpeech`.
- AETHON prefers a Telugu (`te-IN`) TTS voice and falls back to English if Telugu voice data is unavailable.
- The voice tuning uses a slower rate and lower pitch for a calm, futuristic assistant character. It is JARVIS-inspired, not an imitation of a specific actor or copyrighted performance.
- Install Telugu speech/TTS language data on the phone if the device does not provide it by default.

This first slice is voice I/O only. It does not execute arbitrary shell commands, bypass Android permissions, or grant voice input authority to perform privileged actions. The next integration step is to send the verified transcript through the AETHON API/device-agent safety boundary and speak the verified response.

## Local API connection

- Android Emulator: `http://10.0.2.2:8000`
- Physical Android device: use the reachable LAN address of the AETHON API, for example `http://192.168.x.x:8000`
- Production: use an HTTPS API endpoint.

## Build

From this directory with Gradle 8.9 and JDK 17:

```text
gradle --no-daemon assembleDebug
```

APK output:

`app/build/outputs/apk/debug/app-debug.apk`

GitHub Actions builds the same debug APK and uploads it as the `aethon-debug-apk` artifact.
