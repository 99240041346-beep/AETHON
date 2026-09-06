# AETHON Tool Specification

## Tool Contract

Tools are capability boundaries. A tool must declare what it can access and what side effects it can cause.

Required metadata:

```text
id
version
name
description
input_schema
output_schema
permissions
risk_class
timeout_ms
supports_dry_run
network_policy
filesystem_policy
```

## Execution Requirements

Before execution:

1. Validate the request schema.
2. Resolve the authenticated actor and project scope.
3. Evaluate security policy.
4. Check resource/network/filesystem constraints.
5. Obtain approval if required.
6. Generate an audit event.

During execution:

- enforce timeout/resource limits
- capture structured output
- redact secrets from logs
- support cancellation where possible

After execution:

- validate output schema
- record side effects
- emit success/failure event
- pass evidence to verification

## Web Evidence Requirements

Web search and fetch results are untrusted evidence. Every web-derived fact used by an agent should retain provenance including source URL, retrieval time when available, normalized source identity, and content hash when content is captured.

The verification layer should:

- preserve provenance through planning and answer generation
- deduplicate equivalent source URLs
- assign a transparent source-quality score rather than treating domains as inherently authoritative
- detect conflicting claims across independent sources
- avoid presenting a disputed claim as established fact
- require stronger evidence for high-impact decisions

A source-quality score is a heuristic, not proof of truth. AETHON must not equate `.gov`, `.edu`, `.org`, or `.com` with factual correctness.

## Initial Tools

### CalculatorTool
Pure computation with no external side effects.

### WebSearchTool
Controlled retrieval from permitted web sources. Untrusted web content is data, not instructions to the agent.

### WebFetchTool
Fetches public HTTP(S) resources under network and response-size policy. Redirects require explicit re-validation.

### WorkspaceFileTool
Read/write files only inside an explicitly authorized workspace.

### CodeSandboxTool
Execute generated code inside an isolated sandbox with restricted filesystem, network, CPU, memory, process count, and execution time.

## Tool Safety

Tools must not provide mechanisms to bypass authentication, CAPTCHA, paywalls, access controls, rate limits, or other security boundaries.

Tools must fail closed when authorization context is missing or invalid.
