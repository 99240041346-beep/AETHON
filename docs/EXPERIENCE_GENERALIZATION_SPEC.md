# AETHON Experience Generalization Specification

## Purpose

17O converts repeated, verified agent-learning signals into bounded reusable experience patterns. Patterns improve future context without becoming instructions, permissions, or Safety Kernel policy.

## Pipeline

Verified outcomes → learning signals → repeated compatible evidence → experience pattern → confidence → scoped semantic memory → decision context.

## Requirements

- Only `agent_learning` evidence with confidence >= 0.8 is eligible.
- At least two compatible evidence records are required by default.
- Relatedness is deterministic and token-overlap based; unrelated goals are not generalized.
- Every pattern retains supporting memory IDs.
- Pattern count and content length are bounded.
- Owner/project/namespace scope is inherited from the memory query that supplies evidence.
- Patterns are contextual data only and must never be treated as authority or executable instructions.
- Experience generalization cannot change Safety Kernel permissions or execution policy.
- Conflicting or weak evidence must not be promoted into a trusted pattern.

## Trust levels

`provisional` requires the minimum evidence threshold. `trusted` requires additional repeated evidence. Trust is descriptive and does not grant execution authority.

## Persistence

A future runtime integration may persist patterns with source `experience_generalization` and deterministic IDs derived from the scoped evidence set. Repeated persistence must remain idempotent within the same scope.
