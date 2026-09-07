# AETHON 17P — Experience Retrieval Specification

## Purpose

17P retrieves relevant generalized experiences for a new task and ranks them as bounded planning context. Retrieval is advisory and never authoritative.

## Retrieval contract

Only memories with source `experience_generalization` are eligible. Ranking combines deterministic goal-term overlap and stored confidence. Results are capped and ties are resolved by memory ID.

## Safety

Retrieved experience is explicitly contextual data. It cannot grant permissions, execute tools, override the Safety Kernel, or be treated as an instruction. Scope remains the responsibility of the memory repository query supplying candidates.

## Pipeline

New goal → scoped experience search → eligibility filtering → relevance ranking → bounded context → Agent Brain planning.

## Evaluation

Measure retrieval precision, useful-context rate, task success delta, and cases where irrelevant experience is correctly excluded. Retrieval must not be allowed to inflate success metrics by treating an experience pattern as proof of current task completion.
