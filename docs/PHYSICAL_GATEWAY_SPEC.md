# Phase 29 — IoT / Physical Gateway

AETHON provides a bounded, provider-neutral policy boundary for physical-world operations.

## Guarantees
- Candidate count and payload size are bounded.
- Physical operations are explicit: read, write, actuate, and stop.
- Marked requests and guarded adapters fail closed without explicit approval.
- Missing compatible adapters fail closed rather than being simulated.
- Adapter selection is deterministic by priority, then candidate name.
- This module routes policy only; it never drives hardware or claims device state.

## Safety boundary
A route is not authorization and does not execute a physical action. The Safety Kernel, authorization, approval, execution limits, verification, and audit remain authoritative. Concrete GPIO, MQTT, serial, robotics, smart-home, or industrial adapters must authenticate devices, enforce timeouts and safety limits, verify outcomes, and stop safely on failure before being considered production-ready.
