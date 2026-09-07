# AETHON Decision Context

Step 17K adds a bounded bridge from scoped memory into agent planning context.

## Contract

`DecisionContextBuilder` converts retrieved memory records into a small, deterministic context package for the Agent Brain. Memory is contextual data only; it is never treated as executable instructions or authority.

## Bounds

- at most 5 memory records are considered
- each memory is truncated to a bounded size
- duplicate memory content is removed deterministically
- owner/project/namespace scoping remains the responsibility of the memory repository

## Safety

Decision context cannot authorize tools, bypass SafetyKernel, or create external side effects. Tool authorization remains a separate control-plane decision.
