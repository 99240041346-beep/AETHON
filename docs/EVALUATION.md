# AETHON Evaluation Strategy

AETHON is developed through measurable capability improvement rather than unsupported superiority claims.

## Initial evaluation categories

- Reasoning
- Research
- Tool selection
- Tool execution
- Planning
- Coding
- File operations
- Recovery
- Memory retrieval
- Safety
- Latency
- Cost

## Task record

Each benchmark task should define:

- Stable task ID
- Version
- User goal
- Required capabilities
- Allowed tools
- Expected outcome
- Safety constraints
- Success criteria
- Failure criteria
- Reproducibility metadata

## Metrics

Primary metrics:

- Task success rate
- Partial completion rate
- Tool-call correctness
- Recovery rate
- Verification accuracy
- Memory retrieval accuracy
- Safety violation rate

Operational metrics:

- Latency
- Token usage
- Compute cost
- Failure frequency

## Release rule

A release is not considered an improvement merely because one benchmark increases. We examine the full evaluation matrix and require regression tests to remain within defined thresholds.

## Initial target

AETHON-0.1 will establish a baseline over a small controlled suite. The suite should grow toward 50–100 representative tasks before major agent capabilities are declared stable.
