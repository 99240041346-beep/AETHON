# AETHON Security Architecture

## Security objective

AETHON must remain useful without giving an AI model unrestricted authority over a user's machine, accounts, network, or physical devices.

## Action pipeline

```text
Action proposal
  ↓
Identity check
  ↓
Permission check
  ↓
Risk classification
  ↓
Policy check
  ↓
Reversibility / impact check
  ↓
Approve / Ask / Block
  ↓
Sandboxed execution
  ↓
Audit event
  ↓
Verification
```

## Permission classes

- `READ`: inspect authorized information.
- `WRITE`: modify authorized data.
- `EXECUTE`: run an authorized operation in a controlled environment.
- `EXTERNAL_SIDE_EFFECT`: changes an external service or account.
- `HIGH_RISK`: requires explicit approval and stronger controls.

## Mandatory controls

- Least privilege
- Credential isolation
- Secret redaction
- Sandboxed code execution
- Filesystem boundaries
- Network restrictions
- Timeouts
- Resource limits
- Cancellation
- Rate limits
- Tenant/project isolation
- Audit logging
- Kill switch
- Human approval for sensitive irreversible actions

## Threats to evaluate

- Prompt injection
- Malicious web content
- Tool parameter manipulation
- Data exfiltration
- Credential exposure
- Excessive permissions
- Unsafe generated code
- Cross-project data access
- Resource exhaustion
- Supply-chain compromise

## Non-goals

AETHON will not be designed to bypass authentication, CAPTCHA, paywalls, rate limits, access controls, anti-bot protections, or other security mechanisms.
