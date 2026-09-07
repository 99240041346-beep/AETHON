# AETHON 17L — Research + Memory + Agent Decision Loop

17L connects scoped memory retrieval to bounded agent planning.

## Flow

`scoped memory retrieval → DecisionContextBuilder → AgentBrain planning → SafetyKernel → execution → verification`

Memory can provide contextual signals for deciding whether fresh research is useful. It cannot create a tool, grant permission, override safety policy, or become authoritative instructions.

## Bounds

- maximum 5 decision-context items in the runtime
- maximum 4000 characters per context item
- context is persisted with the plan for pause/resume
- only tools already registered with the runtime can be selected
- execution and side effects remain governed by the SafetyKernel
- verification remains required before task success

## Recovery

Replanning may adapt tools or inputs after bounded failures, subject to the existing step/replan budgets.
