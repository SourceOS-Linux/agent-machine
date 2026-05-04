# ADR 0002: Homebrew Bootstrap Strategy

Status: accepted for bootstrap.

## Context

Agent Machine must be easy to install for developers and operators while remaining conservative about runtime activation. TurtleTerm and BearBrowser already use a Homebrew-first bootstrap pattern. Agent Machine should align with that pattern without silently creating privileged runtime directories, downloading models, configuring LVM, or starting provider services.

## Decision

Homebrew is a first-class bootstrap distribution surface.

The formula installs:

- bootstrap CLI;
- contracts;
- docs;
- examples;
- Python package source;
- package metadata;
- development/render dependencies file.

The formula does not automatically:

- create `/etc/agent-machine`;
- create `/var/lib/agent-machine`;
- configure LVM;
- start systemd services;
- install Quadlet units;
- download models;
- activate inference providers.

Render and activation-evaluation commands may delegate to the Python package source. Python dependencies are documented during bootstrap and may become formula-managed later.

## Consequences

Installation remains safe and reversible. Activation remains explicit, policy-aware, and evidence-backed. The tradeoff is that render/evaluation commands may require a separate dependency install until the package surface stabilizes.

This is acceptable for bootstrap and not sufficient for release-candidate status.
