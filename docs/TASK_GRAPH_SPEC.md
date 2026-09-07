# AETHON 17T — Goal Decomposition & Task Graph Intelligence

Represent complex goals as bounded dependency graphs so independent work can become ready in parallel while dependent work waits for prerequisites.

## Contract
- Nodes have stable local IDs, goals, and dependency IDs.
- Graph size is bounded.
- Duplicate subgoals are removed deterministically.
- A node is ready only when every declared dependency is complete.
- Invalid or unknown dependency references are ignored rather than granting implicit authority.
- Graph structure is planning data; Safety Kernel authorization remains authoritative for every actual action.

## Flow
Goal → subgoals → dependency graph → ready set → execute → verify → update graph → continue/replan.
