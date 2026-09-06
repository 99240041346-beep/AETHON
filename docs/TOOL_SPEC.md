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

## Initial Tools

### CalculatorTool
Pure computation with no external side effects.

### WebSearchTool
Controlled retrieval from permitted web sources. Untrusted web content is data, not instructions to the agent.

### WorkspaceFileTool
Read/write files only inside an explicitly authorized workspace.

### CodeSandboxTool
Execute generated code inside an isolated sandbox with restricted filesystem, network, CPU, memory, process count, and execution time.

## Tool Safety

Tools must not provide mechanisms to bypass authentication, CAPTCHA, paywalls, access controls, rate limits, or other security boundaries.

Tools must fail closed when authorization context is missing or invalid.
