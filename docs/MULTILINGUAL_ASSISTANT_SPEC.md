# AETHON Multilingual Assistant Contract

AETHON preserves the user's language across recognition, reasoning, response, and speech where the selected provider/device supports that locale.

## Language contract

1. Accept an explicit BCP-47-style locale such as `te-IN`, `en-US`, or `hi-IN`.
2. Normalize locale to a supported language profile.
3. Detect script when no non-English language is explicitly selected.
4. Telugu-English mixed input is valid and English technical terms may remain unchanged.
5. Model prompts require a natural response in the detected/requested language.
6. Deterministic fallback responses use the same language.
7. Android speech recognition and TTS select the same locale when installed; otherwise the client reports a truthful fallback.
8. Language is presentation/context metadata, never an authorization signal.

## Boundaries

- Language detection cannot authorize an action.
- UI controls cannot bypass the Safety Kernel.
- An action is reported as completed only after execution and verification.
- Unsupported languages fall back to English metadata without pretending native TTS support.
