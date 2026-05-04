# Agent Machine Install Guide

Agent Machine follows the same installation philosophy as TurtleTerm and BearBrowser:

- Homebrew is a first-class distribution surface for immediate developer use.
- Direct repository formula installs work before the public tap is promoted.
- The public SourceOS tap is the preferred long-term install surface.
- Release artifact installers come later and must preserve manifests, SBOMs, and attestations.
- Installation should expose diagnostics before it performs privileged setup.
- Runtime setup must be explicit and policy-aware.

## Immediate Homebrew install

Install directly from this repository formula:

```bash
brew install --HEAD https://raw.githubusercontent.com/SourceOS-Linux/agent-machine/main/packaging/homebrew/Formula/agent-machine.rb
```

Validate:

```bash
agent-machine version && agent-machine paths && agent-machine probe --format json
```

## Future SourceOS tap install

After promotion to `SourceOS-Linux/homebrew-tap`:

```bash
brew install SourceOS-Linux/tap/agent-machine
```

Current tap HEAD formula flow after the tap is published:

```bash
brew install --HEAD SourceOS-Linux/tap/agent-machine
```

## Local checkout flow

From a local checkout:

```bash
brew install --HEAD ./packaging/homebrew/Formula/agent-machine.rb
```

## Installer philosophy

The bootstrap formula installs:

- `agent-machine` CLI;
- draft contracts;
- architecture docs;
- example payloads.

The bootstrap formula does not yet create privileged runtime directories, install systemd services, configure LVM, modify container runtime policy, download models, or start inference providers.

That is deliberate. Agent Machine setup must separate install from activation.

## Target runtime directories

Future setup commands should manage these paths explicitly:

```text
/etc/agent-machine
/var/lib/agent-machine
/var/lib/agent-machine/models
/var/lib/agent-machine/cache
/var/lib/agent-machine/evidence
/run/agent-machine
```

## Future setup command shape

```text
agent-machine doctor
agent-machine init --profile m2-asahi-linux
agent-machine init --profile sourceos-workstation --storage local-lvm
agent-machine init --profile kubernetes-node --storage topolvm-k8s
agent-machine probe --format json --fail-closed
agent-machine storage plan --profile local-lvm
agent-machine storage apply --profile local-lvm
agent-machine provider list
agent-machine provider enable llama.cpp
```

These are target commands, not all implemented behavior yet.

## SourceOS install surfaces

| Surface | Role |
| --- | --- |
| Homebrew direct formula | Immediate bootstrap install from this repo. |
| SourceOS Homebrew tap | Preferred developer/operator install after tap promotion. |
| SourceOS package/channel | Future Linux-native package lane. |
| rpm-ostree / image composition | Future immutable SourceOS host integration. |
| systemd / Quadlet | Future local AgentPod runtime activation. |
| Kubernetes / TopoLVM | Future cluster AgentPod runtime activation. |

## M2 Asahi notes

M2 Asahi is Linux on Apple Silicon. The install path must not assume macOS-only Metal or MLX acceleration. The initial local path is:

1. install CLI through Homebrew or Linux package lane;
2. run `agent-machine probe --format json`;
3. inspect CPU, Vulkan, LVM, Podman, SELinux, and cgroup facts;
4. configure local LVM only through explicit setup;
5. enable `llama.cpp` or another Linux-compatible provider through a governed provider contract.

## BearBrowser and TurtleTerm alignment

TurtleTerm uses tapless Homebrew install from its repository formula and a future `SourceOS-Linux/tap/turtle-term` path. BearBrowser uses immediate direct Homebrew formula install and a future `SourceOS-Linux/tap/bearbrowser` path.

Agent Machine follows that same pattern:

```bash
brew install --HEAD https://raw.githubusercontent.com/SourceOS-Linux/agent-machine/main/packaging/homebrew/Formula/agent-machine.rb
brew install SourceOS-Linux/tap/agent-machine
brew install --HEAD SourceOS-Linux/tap/agent-machine
```

## Validation

Minimum post-install checks:

```bash
agent-machine version
agent-machine paths
agent-machine probe --format json
```

The probe must remain secret-free. It must not emit raw prompts, raw KV-cache contents, private memory content, unredacted credentials, or model-provider secrets.
