# 18 — Multimodal Intelligence

AETHON 18 provides a bounded multimodal normalization layer for text, images, audio, video, and documents. It validates media type and size, computes content identity, sanitizes extracted text, and produces advisory context for downstream reasoning.

## Security boundary

Multimodal content is untrusted data. Extracted text, metadata, OCR/transcripts, captions, and model observations never become instructions, permissions, approvals, or tool authority. The Safety Kernel, execution limits, approvals, and verification remain authoritative.

## Bounds

- 32 media items per packet by default
- 12,000 context characters by default
- 25 MiB per media item by default
- Explicit MIME allowlist by modality
- Secret and instruction-like content sanitization
- Deterministic SHA-256 media identity
- No automatic external upload or tool execution

## Supported modalities

`text`, `image`, `audio`, `video`, `document`.

The engine intentionally does not pretend to perform OCR, speech recognition, video understanding, or vision inference itself. Provider-specific perception belongs behind this validated boundary and must return bounded observations.
