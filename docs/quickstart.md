# Agent Machine Quickstart

This quickstart proves the current bootstrap flow end to end without activating a runtime provider. It exercises installation intent, host probing, rendering, governance, storage/evidence receipts, and activation decisions.

Agent Machine is still production-blocked by design. The commands below produce deterministic plans, manifests, receipts, and decisions. They do not start model servers, mutate privileged runtime directories, mount LVM volumes, or authorize sensitive execution.

## 1. Install from Homebrew

Direct repository formula:

```bash
brew install --HEAD https://raw.githubusercontent.com/SourceOS-Linux/agent-machine/main/packaging/homebrew/Formula/agent-machine.rb
```

SourceOS tap flow:

```bash
brew install --HEAD SourceOS-Linux/tap/agent-machine
```

Repository checkout flow:

```bash
brew install --HEAD ./packaging/homebrew/Formula/agent-machine.rb
```

## 2. Install Python render dependencies

The bootstrap commands are dependency-light. Render and activation evaluation commands require `jsonschema` and `PyYAML`.

From a repository checkout:

```bash
python3 -m pip install -r requirements-dev.txt
```

From a Homebrew install:

```bash
python3 -m pip install -r $(brew --prefix)/share/agent-machine/requirements-dev.txt
```

## 3. Run safe bootstrap diagnostics

```bash
agent-machine version
agent-machine paths
agent-machine doctor --format json
agent-machine probe --format json
```

Expected safety posture:

- probe is secret-free;
- raw prompts are not included;
- raw KV-cache contents are not included;
- provider secrets are not included;
- runtime directories are not created automatically.

## 4. Render a local AgentPod plan

From a repository checkout:

```bash
agent-machine render plan examples/local-podman-llama-cpp.agent-pod.json --pretty
```

From a Homebrew install:

```bash
agent-machine render plan $(brew --prefix)/share/agent-machine/examples/local-podman-llama-cpp.agent-pod.json --pretty
```

This emits an `AgentPodDeploymentPlan`. It is not authorization.

## 5. Render a deployment receipt

```bash
agent-machine render receipt examples/local-podman-llama-cpp.agent-pod.json \
  --artifact-path /tmp/agent-machine-local-agentpod-plan.json \
  --pretty
```

The receipt proves deterministic derivation. It does not authorize activation.

## 6. Compare local Quadlet rendering

```bash
agent-machine render quadlet \
  examples/local-podman-llama-cpp.agent-pod.json \
  --compare deploy/quadlet/agent-machine-llama-cpp.container
```

This checks the contract-derived local Quadlet output against the checked-in skeleton.

Required local skeleton posture:

- loopback-only exposure;
- no privileged mode;
- no raw Docker/Podman socket mounts;
- read-only model mount;
- receipts required;
- SELinux labels not disabled.

## 7. Compare Kubernetes / TopoLVM rendering

```bash
agent-machine render k8s \
  examples/k8s-topolvm.agent-pod.json \
  --compare deploy/k8s/llama-cpp-topolvm-pod.yaml
```

This checks the contract-derived Kubernetes skeleton against the checked-in manifest.

Required cluster skeleton posture:

- namespace and service account present;
- TopoLVM PVCs present;
- ClusterIP service only;
- default-deny egress NetworkPolicy;
- no privileged container;
- read-only root filesystem;
- seccomp runtime default.

## 8. Validate fail-closed activation

This proves that missing Policy Fabric admission and missing Agent Registry grants block activation.

```bash
agent-machine activate evaluate \
  examples/local-podman-llama-cpp.agent-pod.json \
  examples/policy-admission.missing.json \
  examples/agent-registry-grant.missing.json \
  --deployment-receipt-id urn:srcos:agent-machine:deployment-receipt:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  --storage-receipt-dir examples \
  --decided-at 2026-05-04T12:51:00Z \
  --decision-id urn:srcos:agent-machine:activation-decision:local-llama-cpp-fail-closed \
  --pretty
```

Expected decision:

```text
status: fail-closed
activationAllowed: false
```

## 9. Validate allowed activation evaluation

This proves that activation can become allowed only when the PolicyAdmission and AgentRegistryGrant are activation-scoped and required storage receipts resolve.

```bash
agent-machine activate evaluate \
  examples/local-podman-llama-cpp.agent-pod.json \
  examples/policy-admission.allowed-activation.json \
  examples/agent-registry-grant.active-activation.json \
  --deployment-receipt-id urn:srcos:agent-machine:deployment-receipt:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  --storage-receipt-dir examples \
  --decided-at 2026-05-04T12:51:00Z \
  --decision-id urn:srcos:agent-machine:activation-decision:local-llama-cpp-allowed \
  --pretty
```

Expected decision:

```text
status: allowed
activationAllowed: true
```

This still does not start a provider. It only proves that the activation decision object evaluates to allowed under the current prototype governance artifacts.

## 10. Run full repository validation

```bash
make validate
```

This currently runs:

```text
validate-json
validate-yaml
validate-quadlet
validate-render
validate-evidence
validate-governance
validate-activation
validate-package
validate-cli
validate-formula
```

## 11. Failure model

Agent Machine should fail closed when any required precondition is absent or unsafe.

Fail-closed cases include:

- invalid AgentPod;
- missing PolicyAdmission;
- denied PolicyAdmission;
- missing AgentRegistryGrant;
- revoked AgentRegistryGrant;
- missing deployment receipt ID;
- unresolved StorageReceipt ref;
- unsafe StorageReceipt;
- missing encryption when encryption is required;
- missing quota when quota is required;
- world-writable storage;
- symlink traversal observed;
- raw prompt/KV-cache/secret/private memory included in evidence.

## 12. Current production blockers

This quickstart demonstrates the bootstrap substrate. It does not remove production blockers.

Remaining production blockers include:

- confirmed visible GitHub Actions run;
- image digest pinning and provenance gate;
- real Policy Fabric client or admission endpoint;
- real Agent Registry grant resolver;
- real AgentPlane evidence submission/staging client;
- local LVM provisioning/probe implementation;
- M2 Asahi host measurement and provider readiness data;
- release evidence bundle with signed/provenance artifacts.
