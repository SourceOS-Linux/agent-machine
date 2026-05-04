# TopoLVM Integration

TopoLVM is the Kubernetes storage implementation path for Agent Machine model, cache, scratch, evidence, and artifact volumes.

## Current bootstrap artifacts

Agent Machine currently includes:

- Kubernetes/TopoLVM AgentPod example;
- Kubernetes/TopoLVM deployment skeleton;
- TopoLVM evidence StorageReceipt example;
- deterministic Kubernetes renderer comparison.

## Required future integration

A production integration must provide:

- StorageClass discovery;
- PVC lifecycle observation;
- node-local volume placement facts;
- storage receipt generation from actual PVC/mount state;
- wipe/teardown receipt behavior;
- scheduling integration with AgentPod placement.

## Safety rule

TopoLVM storage receipts must never include raw prompt content, raw KV-cache contents, credentials, or private memory. Sensitive cache volumes must fail closed when encryption, quota, or policy requirements are unmet.
