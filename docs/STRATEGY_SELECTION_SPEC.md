# AETHON 17Q — Adaptive Strategy Selection

17Q turns bounded retrieved experience into a ranked strategy suggestion for the current goal. It adapts to the present task rather than blindly copying history.

## Contract
- Input is generalized experience retrieved within the current memory scope.
- Failed, blocked, or uncertain historical approaches are excluded.
- Ranking combines retrieval relevance, current-goal overlap, and evidence confidence.
- Candidate count and context length are bounded and ties deterministic.
- Selected strategy is contextual guidance, never executable authority.

## Safety
The Safety Kernel remains authoritative. Strategy selection cannot grant permissions, authorize tools, alter risk levels, bypass approval, or replace current verification. Historical success is not proof of current task success.

## Pipeline
Verified outcome → agent learning → experience generalization → experience retrieval → adaptive strategy selection → Agent Brain → plan → execute → verify → learn.
