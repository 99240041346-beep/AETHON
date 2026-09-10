# AETHON Assistant Command Bridge

This slice connects bounded voice intents to Android actions without allowing arbitrary package execution.

## Supported Android action

- `android.open_app`
- Allowlisted applications: YouTube, Chrome, Calculator, Settings

The API emits an action only for an allowlisted application. The Android client independently checks the package against the same allowlist before launching it.

The command bridge does not execute commands on the server and does not provide shell execution or permission bypass.
