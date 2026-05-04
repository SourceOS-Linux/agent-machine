# Runtime Package Layout

Agent Machine started with loose scripts because the first priority was to stabilize contracts, examples, install surfaces, and validation. That was correct for bootstrap speed. It is not the right long-term runtime shape.

## Decision

Agent Machine should move toward an installable Python package under `src/agent_machine/`, while keeping thin script entrypoints for compatibility and simple local execution.

The target layout is:

```text
agent-machine/
├── pyproject.toml
├── src/
│   └── agent_machine/
│       ├── __init__.py
│       ├── cli.py
│       ├── contracts.py
│       ├── probe.py
│       ├── renderers/
│       │   ├── __init__.py
│       │   ├── plan.py
│       │   ├── quadlet.py
│       │   └── k8s.py
│       ├── validators/
│       │   ├── __init__.py
│       │   ├── json_contracts.py
│       │   ├── yaml_manifests.py
│       │   └── quadlet.py
│       └── receipts.py
├── scripts/
│   ├── validate-json.py
│   ├── validate-yaml.py
│   ├── validate-quadlet.py
│   ├── render-agentpod-plan.py
│   ├── render-agentpod-quadlet.py
│   └── render-agentpod-k8s.py
└── bin/
    └── agent-machine
```

## Transitional rule

Do not break the current script and Homebrew path while packaging matures.

During transition:

- `bin/agent-machine` remains the bootstrap CLI installed by Homebrew.
- `scripts/*.py` remain directly executable and CI-owned.
- New shared code moves into `src/agent_machine/`.
- Scripts become thin wrappers over the package modules.
- `make validate` remains canonical.

## Package responsibilities

### `agent_machine.cli`

Owns the long-term CLI command tree:

```text
agent-machine version
agent-machine paths
agent-machine doctor
agent-machine probe
agent-machine validate
agent-machine render plan
agent-machine render quadlet
agent-machine render k8s
agent-machine receipt deployment
```

### `agent_machine.probe`

Owns host/runtime discovery:

- host profile;
- OS/kernel/arch;
- SELinux/cgroup mode;
- Podman/Docker/systemd/Quadlet availability;
- LVM/TopoLVM/local filesystem posture;
- accelerator probes;
- provider discovery;
- secret-free probe output.

### `agent_machine.contracts`

Owns schema loading and validation helpers:

- stable schema path discovery;
- kind-to-schema mapping;
- schema validation;
- instance validation;
- digest calculation.

### `agent_machine.renderers.plan`

Owns `AgentPod -> AgentPodDeploymentPlan` rendering and plan schema validation.

### `agent_machine.renderers.quadlet`

Owns `AgentPod -> Quadlet .container` rendering and deterministic comparison.

### `agent_machine.renderers.k8s`

Owns `AgentPod -> Kubernetes YAML` rendering and deterministic semantic comparison.

### `agent_machine.validators.*`

Owns validation surfaces currently implemented as scripts:

- JSON contracts/examples;
- Kubernetes YAML skeletons;
- Quadlet templates.

### `agent_machine.receipts`

Owns secret-free receipt rendering and validation:

- deployment receipt;
- future storage receipt;
- future probe receipt;
- future runtime receipt.

## Why not keep loose scripts forever

Loose scripts are acceptable for bootstrap, but they create problems as the system grows:

- shared digest logic gets duplicated;
- schema loading gets duplicated;
- renderers are hard to unit-test in isolation;
- Homebrew and future Linux packaging become harder;
- AgentTerm/TurtleTerm/BearBrowser integrations need stable import paths;
- future AgentPlane/Policy Fabric bindings need reusable library functions.

## Why not over-package immediately

The repo is still stabilizing core contracts. Moving too early into a heavy package risks freezing bad abstractions.

Keep loose scripts until these are stable:

- `AgentMachine` schema;
- `CacheTier` schema;
- `InferenceProvider` schema;
- `AgentPod` schema;
- `AgentPodDeploymentPlan` schema;
- `DeploymentReceipt` schema;
- local Quadlet renderer;
- Kubernetes renderer.

## Proposed migration phases

### Phase 1: Bootstrap scripts, current state

- Direct scripts under `scripts/`.
- Shell bootstrap CLI under `bin/agent-machine`.
- Homebrew formula installs docs/contracts/examples/bin.
- `make validate` owns local verification.

### Phase 2: Shared library extraction

Add `src/agent_machine/` and move only shared primitives first:

- JSON load helpers;
- stable digest helpers;
- schema validation helpers;
- path constants;
- common safety checks.

Scripts remain as wrappers.

### Phase 3: Renderer modules

Move plan, Quadlet, and Kubernetes rendering into package modules.

Scripts become:

```python
from agent_machine.renderers.plan import main
raise SystemExit(main())
```

### Phase 4: CLI consolidation

Replace the shell bootstrap CLI with a Python CLI once package installation is reliable.

Homebrew formula should install console scripts from `pyproject.toml`.

### Phase 5: Runtime integrations

Add typed integration modules for:

- Policy Fabric admission client/stub;
- Agent Registry grant client/stub;
- AgentPlane receipt emission;
- provider discovery;
- local LVM provisioning plans.

## Packaging targets

Long-term packaging surfaces:

| Surface | Role |
| --- | --- |
| Homebrew formula | Developer/operator bootstrap, matching TurtleTerm/BearBrowser philosophy |
| Python package | Testable runtime library and CLI module |
| RPM / rpm-ostree image composition | SourceOS host integration |
| OCI image | Controller/renderer/validator jobs in Kubernetes |
| Quadlet units | Local long-running AgentPod activation |

## Immediate next package step

Do not migrate everything at once. Add only:

```text
src/agent_machine/__init__.py
src/agent_machine/digest.py
src/agent_machine/paths.py
```

Then update one script to import the shared digest helper. That proves packaging without destabilizing the repo.
