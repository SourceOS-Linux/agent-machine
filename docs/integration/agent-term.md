# AgentTerm Integration

AgentTerm is an operator surface. It should consume Agent Machine facts and decisions rather than owning machine-runtime policy itself.

## Current bootstrap command surfaces

Agent Machine exposes:

- `agent-machine doctor`;
- `agent-machine probe`;
- `agent-machine render ...`;
- `agent-machine activate evaluate ...`.

These commands can feed terminal-native operator workflows and ChatOps summaries.

## Required future integration

AgentTerm integration should provide:

- command palettes for doctor/probe/render/activation evaluation;
- readable summaries of ActivationDecision and fail-closed reasons;
- links to receipts and evidence artifacts;
- clear distinction between dry-run evaluation and real activation;
- no display of secret values or raw cache contents.

## Safety rule

AgentTerm must not convert a render/evaluation artifact into runtime activation without Policy Fabric admission and Agent Registry grants.
