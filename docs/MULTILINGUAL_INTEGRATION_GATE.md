# AETHON Multilingual Integration Gate

## Scope

This gate verifies that language detection, voice responses, assistant sessions, and Android conversation UI remain separate from authorization.

## Required invariants

- Telugu-English mixed input is accepted.
- Requested/detected language is returned as a normalized locale.
- Responses preserve the selected/detected language.
- Deterministic fallback never claims an external action occurred.
- Language handling cannot authorize device actions.
- Assistant sessions remain owner scoped.
- PostgreSQL migrations remain additive and deterministic.
- Android sends UTF-8 JSON and consumes the returned locale for TTS.
- Device execution remains behind the existing safety and command bridge.

## Verification

API tests and Android CI are required before merge. Post-merge main verification is required before declaring the milestone complete.
