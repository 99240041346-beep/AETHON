# AETHON 17Q — Adaptive Strategy Selection

## Purpose

17Q converts bounded, retrieved experience into a ranked strategy suggestion for the current goal. It adapts to the present task instead of blindly copying historical behavior.

## Contract

- Input is retrieved generalized experience only.
- Failed, blocked, or uncertain historical approaches are excluded from selection.
- Candidates are scored using retrieval relevance, current-goal overlap, and evidence confidence.
- Candidate count and context length are bounded.
- Ties are deterministic.
- The selected strategy is contextual guidance, not an executable command or instruction.

## Compatibility

A strategy is only a suggestion. The agent must still evaluate compatibility with the current goal, available tools, current observations, and current verification requirements. Historical success is not proof that the same approach will succeed now.

## Safety

The Safety Kernel remains authoritative. Strategy selection cannot grant permissions, authorize tools, change risk levels, bypass approval, or alter execution policy. Scope is inherited from the memory/experience retrieval layer.

## Pipeline

Verified outcome → agent learning → experience generalization → experience retrieval → adaptive strategy selection → Agent Brain → plan → execute → verify → learn.

## Evaluation

Measure strategy usefulness, rejection of failed history, deterministic ranking, scope isolation, bounded output, and task success delta. Never count a selected strategy as evidence that the current task has succeeded; only current verification can establish success.
