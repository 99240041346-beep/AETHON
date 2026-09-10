# AETHON Integrated Release Gate

This milestone consolidates the Android Telugu voice client, bounded voice conversation API, and authenticated device gateway into one release candidate.

## Gates 11–16

1. **Voice → Brain → Telugu response:** Android speech recognition sends `te-IN` transcript to `/v1/voice/respond`; the API uses the configured model router and has a deterministic fallback; the Android client speaks the verified response with Android TTS.
2. **Authenticated device gateway:** devices register under an owner and receive a high-entropy token; heartbeats and commands require the device token plus owner scope.
3. **Capability authorization:** commands are accepted only for declared capabilities and bounded payload/TTL values.
4. **Safety boundary:** side-effecting capabilities require explicit approval; critical/denied operations remain blocked. Voice input itself never authorizes a device operation.
5. **Reliability:** replay, expiry, future-dated envelopes, oversized payloads, unavailable model providers, and unavailable voice engines fail safely.
6. **Verification:** automated tests cover voice fallback/HTTP behavior and device registration/authentication/capability/replay/approval/expiry paths; Android CI must build and upload the debug APK.

## Production boundary

The device gateway in this milestone is a **policy and simulator boundary**. It does not drive Android, Windows, or IoT hardware directly. Real device adapters must be authenticated, capability-scoped, independently verified, and routed through the same SafetyExecutionGate before production actuation.

For production deployment, use HTTPS, configure `AETHON_API_TOKEN` and `AETHON_API_OWNER_ID`, configure PostgreSQL via `AETHON_DATABASE_URL`, and provide an approved model provider through the existing model-router environment variables.
