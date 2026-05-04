# Homebrew Python Dependency Strategy

Agent Machine currently follows the TurtleTerm and BearBrowser install philosophy: Homebrew is a first-class bootstrap surface, but install must not silently perform privileged runtime activation. Agent Machine adds one extra complication: render commands are Python package commands and require Python dependencies.

## Current state

The Homebrew formula installs:

- `bin/agent-machine` bootstrap CLI;
- `contracts/`;
- `docs/`;
- `examples/`;
- `src/` Python package source;
- `pyproject.toml`;
- `requirements-dev.txt`.

The bootstrap commands are dependency-light:

```text
agent-machine version
agent-machine paths
agent-machine doctor
agent-machine probe
```

The delegated render commands require the package dependencies:

```text
agent-machine render plan
agent-machine render receipt
agent-machine render quadlet
agent-machine render k8s
```

Current Python dependencies:

```text
jsonschema>=4.22,<5
PyYAML>=6.0,<7
```

## Options

### Option 1: Document external Python dependencies

Keep the Homebrew formula simple. Install the package source and document that render commands need the dependencies from `requirements-dev.txt`.

Advantages:

- simplest formula;
- lowest packaging risk during early bootstrap;
- keeps SourceOS runtime activation explicit;
- avoids pretending the package is mature before contracts stabilize.

Disadvantages:

- render commands can fail if dependencies are missing;
- user experience is weaker;
- Homebrew install is not fully self-contained for render features.

This is the current policy.

### Option 2: Homebrew Python resources

Use Homebrew `resource` blocks for Python dependencies and install them into a formula-managed virtual environment or libexec path.

Advantages:

- render commands work immediately after Homebrew install;
- more polished operator experience;
- formula can test render commands directly.

Disadvantages:

- resource maintenance burden;
- dependency pinning must be kept current;
- package layout should be more stable before we commit to this surface;
- risk of over-investing in Homebrew before Linux-native packaging is ready.

### Option 3: Full Python package install

Treat Agent Machine as a normal Python package installed through `pyproject.toml`, with console script `agent-machine-py`.

Advantages:

- standard packaging path;
- clean imports and entrypoints;
- testable package behavior;
- easier future migration to RPM/OCI package flows.

Disadvantages:

- not yet aligned with the bootstrap-first Homebrew model;
- requires clearer dependency isolation;
- still needs a policy-aware split between install and runtime activation.

## Decision

Use Option 1 for the current bootstrap phase, but improve error messages. The CLI should explain exactly which dependency is missing and point to `requirements-dev.txt`.

Move to Option 2 or Option 3 only after these stabilize:

- package-owned renderers;
- package-owned validators;
- package-owned probe/doctor implementation;
- stable contract schemas;
- working CI visibility;
- a tested Homebrew install path.

## Acceptance rule for changing policy

Do not move to Homebrew-managed Python resources until the formula can test all of the following without privileged setup:

```text
agent-machine version
agent-machine paths
agent-machine doctor --format json
agent-machine probe --format json
agent-machine render plan examples/local-podman-llama-cpp.agent-pod.json --pretty
agent-machine render quadlet examples/local-podman-llama-cpp.agent-pod.json --compare deploy/quadlet/agent-machine-llama-cpp.container
agent-machine render k8s examples/k8s-topolvm.agent-pod.json --compare deploy/k8s/llama-cpp-topolvm-pod.yaml
```

## Required CLI behavior

If a render dependency is missing, the CLI must fail with a direct message such as:

```text
Agent Machine Python dependency missing: PyYAML.
Install dependencies with: python3 -m pip install -r <path>/requirements-dev.txt
```

The CLI must not emit a traceback for ordinary missing-dependency cases.
