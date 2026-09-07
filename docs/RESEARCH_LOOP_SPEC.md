# AETHON Autonomous Research Loop

## Purpose

Step 17I provides a bounded research controller that repeatedly plans research, invokes the public-web researcher, records limitations, and performs limited follow-up rounds.

## Contract

`AutonomousResearchLoop.run(goal, max_questions, max_rounds)` returns a `ResearchLoopResult` containing the original `ResearchPlan`, collected `ResearchReport` objects, pending follow-up queries, and deduplicated unresolved gaps.

## Bounds

- `max_questions`: 1–10
- `max_rounds`: 1–20
- duplicate queries are suppressed case-insensitively
- researcher failures are isolated to the current query
- follow-ups are generated only from research limitations

## Safety

Retrieved web text is treated strictly as data. The loop never interprets evidence, snippets, or page content as executable instructions. External side effects remain outside the research loop and must pass AETHON authorization and safety controls.
