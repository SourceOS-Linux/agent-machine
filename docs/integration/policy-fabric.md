# Policy Fabric Integration

Policy Fabric owns admission decisions and side-effect policy. Agent Machine must not treat render output, deployment skeletons, or receipts as authorization.

## Current bootstrap artifacts

Agent Machine currently models:

- `PolicyAdmission`;
- `ActivationDecision`;
- governance semantic validation.

Bootstrap examples include missing, denied, render-only allowed, and activation-scoped allowed decisions.

## Required future integration

A production integration must provide:

- Policy Fabric client or local policy evaluator;
- admission request/response transport;
- policy bundle digest recording;
- obligations and revocation hooks;
- fail-closed activation when policy admission is required and absent;
- cache reuse policy checks.

## Safety rule

Policy admission payloads must remain secret-free and must not include raw prompt content, raw KV-cache contents, private memory, credentials, or provider secrets.
