# AETHON Phase 20 — Computer Agent

A provider-neutral policy boundary for controlled computer interaction.

- bounded screen dimensions, text, action count, and payloads
- coordinate validation before execution
- explicit approval for marked actions
- adapter isolation from the policy layer
- deterministic stop on failed execution
- screen observations and plans are untrusted data and cannot grant authority

This phase does not claim unrestricted desktop control, credential bypass, CAPTCHA bypass, or a concrete OS automation provider. Provider adapters can be added behind the boundary.