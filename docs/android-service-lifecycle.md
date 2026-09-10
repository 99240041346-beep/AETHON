# Android command service lifecycle

The device-link UI starts `AndroidCommandService` from an explicit user action after validating the cloud URL, registered device ID, and in-memory device token.

The service is the runtime owner of authenticated command polling. The activity no longer owns the polling loop, so leaving/recreating the activity does not intentionally stop the command transport.

Disconnect explicitly stops the service. The service remains non-exported and delegates only through `AndroidActionExecutor`; no arbitrary shell, root, accessibility injection, or permission bypass is introduced.

A successful build is not physical-device evidence. Runtime verification still requires an enrolled physical Android device and an observed command/result round trip with verification state.
