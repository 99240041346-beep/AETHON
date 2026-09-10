# Android command foreground service

`AndroidCommandService` is declared as a non-exported foreground service and uses the `dataSync` foreground-service type. The service remains bounded by the authenticated cloud command transport and `AndroidCapabilityRegistry`/`AndroidActionExecutor`.

Physical-device execution still requires an actual enrolled device and an observed end-to-end command/result verification.
