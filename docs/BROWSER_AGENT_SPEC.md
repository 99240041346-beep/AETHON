# AETHON Phase 19 — Browser Agent

The browser layer provides a provider-neutral policy boundary for web navigation and interaction.

## Guarantees
- HTTP/HTTPS only.
- Optional explicit domain allowlist.
- Bounded page text, links, action count, and action payloads.
- Explicit approval gate for actions marked `requires_approval`.
- Adapter abstraction keeps browser implementation separate from policy.
- Execution stops on the first failed action.
- Browser content and plans are untrusted data; they never grant permissions or bypass Safety Kernel policy.

## Non-goals
This phase does not claim a browser backend, CAPTCHA bypass, authentication bypass, arbitrary credential handling, or unrestricted web access. Provider adapters can be added later behind this boundary.
