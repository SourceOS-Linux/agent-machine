# Agent Machine Troubleshooting

This document records operator-facing failure modes and direct remediation paths. Agent Machine should fail clearly, not noisily. Ordinary setup problems should not produce Python tracebacks or ambiguous runtime behavior.

## Missing Python dependency during render

Render commands delegate from the bootstrap shell CLI into the Python package source:

```bash
agent-machine render plan examples/local-podman-llama-cpp.agent-pod.json --pretty
agent-machine render quadlet examples/local-podman-llama-cpp.agent-pod.json
agent-machine render k8s examples/k8s-topolvm.agent-pod.json
```

If `jsonschema` or `PyYAML` is missing, install the package dependencies from the repository or Homebrew package share path:

```bash
python3 -m pip install -r requirements-dev.txt
```

For Homebrew installs, use the path printed in formula caveats. It is typically under the formula package share directory:

```bash
python3 -m pip install -r $(brew --prefix)/share/agent-machine/requirements-dev.txt
```

Expected error shape:

```text
Agent Machine Python dependency missing: PyYAML.
Install dependencies with: python3 -m pip install -r <path>/requirements-dev.txt
```

Unexpected behavior:

- raw traceback for missing `jsonschema` or `PyYAML`;
- dependency error without a remediation command;
- render command silently skipping validation.

Any of those should be treated as a bug.

## GitHub Actions runs are not visible

The repository has a validation workflow at:

```text
.github/workflows/validate.yml
```

The canonical local validation command is:

```bash
make validate
```

If GitHub Actions runs are not visible for recent commits, check:

1. repository Actions are enabled;
2. workflow file exists on the default branch;
3. workflow syntax is valid;
4. the repository has not disabled Actions for organization policy reasons;
5. the connector/API surface can see Actions runs.

Current tracking issue:

```text
SourceOS-Linux/agent-machine#2 Verify GitHub Actions visibility for Agent Machine validation workflow
```

Absence of visible workflow runs is not proof of validation success or failure.

## Render output is not authorization

The following artifacts are evidence only:

- `AgentPodDeploymentPlan`;
- generated Quadlet `.container` files;
- generated Kubernetes YAML;
- `DeploymentReceipt`.

They do not authorize execution. Sensitive activation still requires:

- Policy Fabric admission;
- Agent Registry grant;
- AgentPlane runtime evidence;
- image digest/provenance checks;
- storage/cache policy checks.

## Homebrew install succeeded but render delegation fails

The Homebrew formula should install:

- `bin/agent-machine`;
- `contracts/`;
- `docs/`;
- `examples/`;
- `src/`;
- `pyproject.toml`;
- `requirements-dev.txt`.

Validate expected installed package source:

```bash
test -f $(brew --prefix)/share/agent-machine/src/agent_machine/cli.py
```

Validate bootstrap commands:

```bash
agent-machine version
agent-machine paths
agent-machine doctor --format json
agent-machine probe --format json
```

Validate render delegation after dependencies are installed:

```bash
agent-machine render plan $(brew --prefix)/share/agent-machine/examples/local-podman-llama-cpp.agent-pod.json --pretty
```

If render delegation fails with `Python package CLI unavailable`, the formula did not install package source in a path the bootstrap CLI can discover, or the package was installed in a non-standard prefix layout.

## `make validate` fails in `validate-json`

Likely causes:

- invalid JSON syntax;
- invalid JSON Schema syntax;
- an example has no `kind` field;
- an example `kind` has no schema mapping;
- an example violates its schema.

Run:

```bash
python3 scripts/validate-json.py
```

Expected validator behavior:

- every schema under `contracts/` is schema-checked;
- every example under `examples/` is mapped by `kind`;
- every example is validated against the matching schema;
- error output includes path and field location.

## `make validate` fails in `validate-yaml`

Likely causes:

- invalid YAML syntax;
- Kubernetes document missing `apiVersion`, `kind`, or `metadata`;
- Pod lacks container security posture;
- PVC lacks `storageClassName` or storage request;
- Service uses non-ClusterIP type in a skeleton manifest;
- NetworkPolicy lacks `policyTypes`.

Run:

```bash
python3 scripts/validate-yaml.py
```

## `make validate` fails in `validate-quadlet`

Likely causes:

- missing `[Container]` section;
- missing `Image` or `Exec`;
- `ReadOnly=true` absent;
- `NoNewPrivileges=true` absent;
- host networking enabled;
- privileged mode enabled;
- container runtime socket mounted;
- model volume is not read-only;
- loopback-only port binding is violated;
- deterministic renderer output drifted from the checked-in skeleton.

Run:

```bash
python3 scripts/validate-quadlet.py
python3 scripts/render-agentpod-quadlet.py examples/local-podman-llama-cpp.agent-pod.json --compare deploy/quadlet/agent-machine-llama-cpp.container
```

## `make validate` fails in render comparison

Render comparisons intentionally fail when checked-in skeletons drift from contract-derived output.

Local Quadlet comparison:

```bash
python3 scripts/render-agentpod-quadlet.py examples/local-podman-llama-cpp.agent-pod.json --compare deploy/quadlet/agent-machine-llama-cpp.container
```

Kubernetes comparison:

```bash
python3 scripts/render-agentpod-k8s.py examples/k8s-topolvm.agent-pod.json --compare deploy/k8s/llama-cpp-topolvm-pod.yaml
```

A diff usually means one of two things:

1. The source `AgentPod` changed and the checked-in deployment skeleton must be regenerated.
2. A human edited the deployment skeleton directly and bypassed the contract source.

The long-term rule is: generated deployment artifacts should be reproducible from typed source objects and generator versions.

## Probe reports Metal unavailable on M2 Asahi

This is expected. M2 Asahi is Linux on Apple Silicon, not macOS. Metal is a macOS acceleration path and must not be assumed for Asahi.

Expected M2 Asahi baseline:

- CPU available;
- Metal unavailable;
- Vulkan probe-gated;
- `llama.cpp` CPU/ARM64 baseline;
- no hard dependency on oMLX.

## Runtime directories are not created automatically

Homebrew installation intentionally does not create or mutate privileged runtime directories.

Target paths:

```text
/etc/agent-machine
/var/lib/agent-machine
/var/lib/agent-machine/models
/var/lib/agent-machine/cache
/var/lib/agent-machine/evidence
/run/agent-machine
```

Future setup commands will manage these explicitly after policy-aware activation exists.

## World-class failure posture

Agent Machine should prefer:

- fail closed for sensitive workload activation;
- fail clearly for missing dependencies;
- fail deterministically for contract/render drift;
- never hide validation failures;
- never emit secrets, raw prompts, raw KV-cache contents, or private memory contents;
- never treat render output as authorization.
