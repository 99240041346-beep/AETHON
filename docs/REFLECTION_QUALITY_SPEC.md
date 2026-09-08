# AETHON 17Z — Agent Reflection & Planning Quality

17Z evaluates completed plans deterministically and produces bounded reflection data for improvement.

## Contract

- Expected work, completed work, and failures are bounded and normalized.
- Quality combines completeness, reliability, and efficiency into a deterministic 0–100 score.
- Reflection lessons/failures are bounded and never treated as authorization.
- A quality score below the configured threshold, or any recorded issue, recommends replanning.
- Reflection output is advisory and cannot bypass Safety Kernel, approvals, execution limits, or verification.
- The implementation does not replace durable memory.

## Verification

CI must cover deterministic scoring, failure detection, bounded reflection, validation, and compatibility imports.
