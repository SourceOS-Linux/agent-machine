# Receipt Chain

Agent Machine must distinguish evidence from authorization. A generated plan or manifest proves derivation. It does not prove that execution is permitted.

## Chain overview

```text
AgentPod source object
  -> schema validation
  -> deployment plan rendering
  -> deployment plan schema validation
  -> manifest rendering
  -> manifest validation
  -> deployment receipt rendering
  -> Policy Fabric admission
  -> Agent Registry grant
  -> AgentPlane runtime evidence
```

## Artifact roles

| Artifact | Role | Authorization status |
| --- | --- | --- |
| `AgentPod` | Typed workload intent and runtime envelope | Not authorization |
| `AgentPodDeploymentPlan` | Non-mutating rendered deployment plan | Not authorization |
| Quadlet / Kubernetes YAML | Runtime-specific deployment artifact | Not authorization |
| `DeploymentReceipt` | Secret-free derivation evidence | Not authorization |
| Policy Fabric decision | Admission decision | Can authorize only within its scope |
| Agent Registry grant | Identity/session/tool grant | Can authorize only within its scope |
| AgentPlane receipt | Runtime evidence after execution or placement | Evidence, not retroactive authorization |

## Source object

The source object is an `AgentPod` JSON payload. It must pass `contracts/agent-pod.schema.json` before any rendering step.

The source object records:

- workload purpose;
- runtime mode;
- model/provider image or command reference;
- network exposure intent;
- storage/cache/evidence mounts;
- policy requirements;
- receipt requirements.

The source object must not contain secret values, raw prompt content, raw KV-cache content, or private memory contents.

## Plan rendering

The plan renderer produces an `AgentPodDeploymentPlan` from the source object. The plan must pass `contracts/agentpod-deployment-plan.schema.json`.

The plan captures:

- generator name and version;
- source AgentPod digest;
- target surface;
- workload summary;
- runtime summary;
- storage resolution summary;
- ports;
- policy flags;
- receipt flags.

The plan explicitly states that it is non-mutating and not authorization.

## Manifest rendering

Manifest renderers derive runtime-specific artifacts from the same source object.

Current render targets:

- local Podman Quadlet `.container` file;
- Kubernetes YAML skeleton.

Required safety checks:

- no privileged mode;
- no secret values in specs;
- no raw Docker/Podman socket mounts;
- loopback-only local exposure unless policy-approved;
- ClusterIP-only Kubernetes skeleton services;
- default-deny egress for Kubernetes skeletons;
- model mounts read-only where possible;
- receipt intent preserved as metadata or environment.

## Deployment receipt

The `DeploymentReceipt` proves deterministic derivation of an artifact from a typed source object by a named generator. It must pass `contracts/deployment-receipt.schema.json`.

The receipt contains:

- generator name and version;
- source object kind, path, ID, and digest;
- artifact kind, path, and digest;
- target surface and profile;
- policy requirement flags;
- empty policy/admission grant references until later admission;
- raw-content safety flags.

The receipt must not claim authorization. In the current schema, `authorizationGranted` is fixed to `false`.

## Policy Fabric admission

Policy Fabric admission happens after the typed source object and generated artifacts are available. It evaluates whether a proposed deployment may proceed.

Admission inputs should include:

- AgentPod object;
- deployment plan;
- deployment receipt;
- manifest digest;
- AgentMachine profile;
- cache tier facts;
- provider facts;
- requested network exposure;
- requested storage classes;
- requested side effects.

Admission output should include:

- decision reference;
- decision digest;
- allowed scope;
- denied scope;
- obligations;
- expiration;
- revocation hooks.

## Agent Registry grant

Agent Registry resolves the non-human participant before sensitive context, tools, cache, or memory are exposed.

The grant should cover:

- agent identity;
- session identity;
- tool grants;
- model/provider authorization;
- cache/memory scope;
- storage/evidence scope;
- expiration;
- revocation status.

## AgentPlane runtime evidence

AgentPlane receives runtime evidence after placement or execution begins. It should not be asked to infer missing deployment metadata after the fact.

Runtime evidence should include:

- AgentMachine ID;
- AgentPod ID;
- provider ID;
- deployment receipt ID;
- Policy Fabric decision reference;
- Agent Registry grant reference;
- image digest;
- model digest;
- tokenizer digest;
- storage receipts;
- cache reuse decision;
- runtime status.

## Failure rule

If any required link in the chain is absent, execution should fail closed for sensitive workloads.

Minimum fail-closed cases:

- invalid source schema;
- invalid generated plan schema;
- manifest validation failure;
- missing deployment receipt;
- missing Policy Fabric decision where required;
- missing Agent Registry grant where required;
- cache reuse requested without policy approval;
- secret values detected in source, plan, manifest, or receipt.

## Current implementation status

Implemented now:

- AgentPod schema;
- AgentPodDeploymentPlan schema;
- DeploymentReceipt schema;
- local Quadlet safety validation;
- Kubernetes YAML skeleton validation;
- local Quadlet deterministic renderer comparison;
- Kubernetes deterministic renderer comparison;
- plan and receipt rendering from AgentPod examples.

Not implemented yet:

- live Policy Fabric admission;
- live Agent Registry grant resolution;
- image digest pinning;
- generated manifest receipts for Quadlet/Kubernetes artifacts;
- AgentPlane receipt submission;
- signed provenance bundles.
