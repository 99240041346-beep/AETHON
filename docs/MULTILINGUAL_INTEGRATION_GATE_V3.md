# Multilingual Integration Gate V3

Merge gate for the multilingual assistant stack.

- Language detection and locale normalization are deterministic and bounded.
- Telugu-English mixed input is supported.
- Voice and assistant responses preserve the selected/detected locale.
- Android uses UTF-8 transport and consumes the returned locale for TTS.
- Conversation persistence remains owner-scoped.
- Language classification never authorizes an action.
- Device execution remains behind the existing Safety Kernel and command bridge.
- API and Android CI must pass before merge.
