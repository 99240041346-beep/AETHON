# AETHON Android Device Client

The Android module is the first device-side client for AETHON. It is intentionally bounded: the current build exposes API connectivity and read-only device metadata only.

## Local API connection

- Android Emulator: `http://10.0.2.2:8000`
- Physical Android device: use the reachable LAN address of the AETHON API, for example `http://192.168.x.x:8000`
- Production: use an HTTPS API endpoint.

The app does not execute arbitrary shell commands and does not bypass Android permissions.

## Build

From this directory with Gradle 8.9 and JDK 17:

```text
gradle --no-daemon assembleDebug
```

APK output:

`app/build/outputs/apk/debug/app-debug.apk`

GitHub Actions builds the same debug APK and uploads it as the `aethon-debug-apk` artifact.
