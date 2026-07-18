.PHONY: validate validate-json validate-yaml validate-quadlet validate-render validate-evidence validate-governance validate-activation validate-supply-chain validate-release-bundle validate-sourceos-projections validate-package validate-cli validate-formula doctor probe
.PHONY: validate validate-json validate-yaml validate-quadlet validate-render validate-evidence validate-governance validate-activation validate-supply-chain validate-release-bundle validate-package validate-cli validate-formula doctor probe
.PHONY: validate validate-json validate-yaml validate-quadlet validate-render validate-evidence validate-governance validate-policy-fabric validate-agent-registry validate-activation validate-supply-chain validate-release-bundle validate-sourceos-projections validate-package validate-cli validate-formula doctor probe
.PHONY: validate validate-json validate-yaml validate-quadlet validate-render validate-evidence validate-governance validate-policy-fabric validate-activation validate-supply-chain validate-release-bundle validate-sourceos-projections validate-package validate-cli validate-formula doctor probe
.PHONY: validate validate-json validate-yaml validate-quadlet validate-render validate-evidence validate-governance validate-policy-fabric validate-agent-registry validate-superconscious-runtime-plan validate-activation validate-supply-chain validate-release-bundle validate-sourceos-projections validate-package validate-cli validate-formula validate-runtime-install-receipts doctor probe

PYTHON ?= python3
RUBY ?= ruby
CLI := bin/agent-machine
BOOTSTRAP_CLI := sh $(CLI)
FORMULA := packaging/homebrew/Formula/agent-machine.rb
LOCAL_AGENTPOD := examples/local-podman-llama-cpp.agent-pod.json
PINNED_AGENTPOD := examples/local-podman-llama-cpp.pinned.agent-pod.json
K8S_AGENTPOD := examples/k8s-topolvm.agent-pod.json
LOCAL_QUADLET := deploy/quadlet/agent-machine-llama-cpp.container
K8S_MANIFEST := deploy/k8s/llama-cpp-topolvm-pod.yaml
READY_POLICY := examples/policy-admission.allowed-activation.json
READY_GRANT := examples/agent-registry-grant.active-activation.json
FAIL_POLICY := examples/policy-admission.missing.json
FAIL_GRANT := examples/agent-registry-grant.missing.json
RECEIPT_DIR := examples
POLICY_DIR := examples
GRANT_DIR := examples
DEPLOYMENT_RECEIPT_ID := urn:srcos:agent-machine:deployment-receipt:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
DECIDED_AT := 2026-05-04T12:51:00Z
PYCLI := PYTHONPATH=src $(PYTHON) -m agent_machine.cli
PYMOD := PYTHONPATH=src $(PYTHON) -m

validate: validate-json validate-yaml validate-quadlet validate-render validate-evidence validate-governance validate-activation validate-supply-chain validate-release-bundle validate-sourceos-projections validate-package validate-cli validate-formula
validate: validate-json validate-yaml validate-quadlet validate-render validate-evidence validate-governance validate-activation validate-supply-chain validate-release-bundle validate-package validate-cli validate-formula
validate: validate-json validate-yaml validate-quadlet validate-render validate-evidence validate-governance validate-policy-fabric validate-agent-registry validate-activation validate-supply-chain validate-release-bundle validate-sourceos-projections validate-package validate-cli validate-formula
validate: validate-json validate-yaml validate-quadlet validate-render validate-evidence validate-governance validate-policy-fabric validate-activation validate-supply-chain validate-release-bundle validate-sourceos-projections validate-package validate-cli validate-formula
validate: validate-json validate-yaml validate-quadlet validate-render validate-evidence validate-governance validate-policy-fabric validate-agent-registry validate-superconscious-runtime-plan validate-activation validate-supply-chain validate-release-bundle validate-sourceos-projections validate-package validate-cli validate-formula validate-runtime-install-receipts

validate-json:
	$(PYTHON) scripts/validate-json.py

validate-yaml:
	$(PYTHON) scripts/validate-yaml.py

validate-quadlet:
	$(PYTHON) scripts/validate-quadlet.py
	$(PYTHON) scripts/render-agentpod-quadlet.py $(LOCAL_AGENTPOD) --compare $(LOCAL_QUADLET)

validate-render:
	$(PYTHON) scripts/render-agentpod-plan.py $(LOCAL_AGENTPOD) --pretty >/tmp/agent-machine-local-agentpod-plan.json
	$(PYTHON) scripts/render-agentpod-plan.py $(K8S_AGENTPOD) --pretty >/tmp/agent-machine-k8s-agentpod-plan.json
	$(PYTHON) scripts/render-agentpod-plan.py $(LOCAL_AGENTPOD) --receipt --artifact-path /tmp/agent-machine-local-agentpod-plan.json --pretty >/tmp/agent-machine-local-deployment-receipt.json
	$(PYTHON) scripts/render-agentpod-plan.py $(K8S_AGENTPOD) --receipt --artifact-path /tmp/agent-machine-k8s-agentpod-plan.json --pretty >/tmp/agent-machine-k8s-deployment-receipt.json
	$(PYTHON) scripts/render-agentpod-k8s.py $(K8S_AGENTPOD) --compare $(K8S_MANIFEST)
	$(PYCLI) render plan $(LOCAL_AGENTPOD) --pretty >/tmp/agent-machine-pycli-local-agentpod-plan.json
	$(PYCLI) render receipt $(K8S_AGENTPOD) --artifact-path /tmp/agent-machine-pycli-k8s-agentpod-plan.json --pretty >/tmp/agent-machine-pycli-k8s-deployment-receipt.json
	$(PYCLI) render quadlet $(LOCAL_AGENTPOD) --compare $(LOCAL_QUADLET)
	$(PYCLI) render k8s $(K8S_AGENTPOD) --compare $(K8S_MANIFEST)
	$(BOOTSTRAP_CLI) render plan $(LOCAL_AGENTPOD) --pretty >/tmp/agent-machine-bootstrap-local-agentpod-plan.json
	$(BOOTSTRAP_CLI) render quadlet $(LOCAL_AGENTPOD) --compare $(LOCAL_QUADLET)
	$(BOOTSTRAP_CLI) render k8s $(K8S_AGENTPOD) --compare $(K8S_MANIFEST)

validate-evidence:
	$(PYTHON) scripts/validate-evidence.py

validate-governance:
	$(PYTHON) scripts/validate-governance.py

validate-policy-fabric:
	$(PYTHON) scripts/validate-policy-fabric.py
	$(PYTHON) scripts/resolve-policy-admission.py $(LOCAL_AGENTPOD) --policy-dir $(POLICY_DIR) --expected-status allowed --deployment-receipt-id $(DEPLOYMENT_RECEIPT_ID) --agent-machine-id urn:srcos:agent-machine:m2-asahi-local --provider-id urn:srcos:agent-machine:inference-provider:asahi-llama-cpp --pretty >/tmp/agent-machine-policy-resolve-allowed.json
	$(PYCLI) policy resolve $(LOCAL_AGENTPOD) --policy-dir $(POLICY_DIR) --expected-status denied --deployment-receipt-id $(DEPLOYMENT_RECEIPT_ID) --agent-machine-id urn:srcos:agent-machine:m2-asahi-local --provider-id urn:srcos:agent-machine:inference-provider:asahi-llama-cpp --pretty >/tmp/agent-machine-pycli-policy-resolve-denied.json

validate-agent-registry:
	$(PYTHON) scripts/validate-agent-registry.py
	$(PYTHON) scripts/resolve-agent-registry-grant.py $(LOCAL_AGENTPOD) --grant-dir $(GRANT_DIR) --grant-id urn:srcos:agent-machine:agent-registry-grant:active-loopback-activation --requested-agent-identity-ref urn:srcos:agent:local-inference-provider --session-ref urn:srcos:session:local-bootstrap --agent-machine-id urn:srcos:agent-machine:m2-asahi-local --pretty >/tmp/agent-machine-registry-resolve-active.json
	$(PYCLI) registry resolve $(LOCAL_AGENTPOD) --grant-dir $(GRANT_DIR) --grant-id urn:srcos:agent-machine:agent-registry-grant:active-render-only --requested-agent-identity-ref urn:srcos:agent:local-inference-provider --session-ref urn:srcos:session:local-bootstrap --agent-machine-id urn:srcos:agent-machine:m2-asahi-local --pretty >/tmp/agent-machine-pycli-registry-resolve-render-only.json
	$(PYCLI) registry resolve $(LOCAL_AGENTPOD) --grant-dir $(GRANT_DIR) --grant-id urn:srcos:agent-machine:agent-registry-grant:active-loopback-activation --session-ref urn:srcos:session:local-bootstrap --agent-machine-id urn:srcos:agent-machine:m2-asahi-local --pretty >/tmp/agent-machine-pycli-registry-resolve-active.json

validate-superconscious-runtime-plan:
	$(PYTHON) scripts/validate-superconscious-runtime-plan.py

validate-superconscious-runtime-plan:
	$(PYTHON) scripts/validate-superconscious-runtime-plan.py
validate-activation:
	$(PYTHON) scripts/validate-activation.py
	$(PYTHON) scripts/evaluate-activation.py $(LOCAL_AGENTPOD) $(READY_POLICY) $(READY_GRANT) --deployment-receipt-id $(DEPLOYMENT_RECEIPT_ID) --storage-receipt-dir examples --decided-at $(DECIDED_AT) --decision-id urn:srcos:agent-machine:activation-decision:local-llama-cpp-allowed --pretty >/tmp/agent-machine-evaluate-activation-allowed.json
	$(PYCLI) activate evaluate $(LOCAL_AGENTPOD) $(FAIL_POLICY) $(FAIL_GRANT) --deployment-receipt-id $(DEPLOYMENT_RECEIPT_ID) --storage-receipt-dir $(RECEIPT_DIR) --decided-at $(DECIDED_AT) --decision-id urn:srcos:agent-machine:activation-decision:local-llama-cpp-fail-closed --pretty >/tmp/agent-machine-pycli-evaluate-activation-fail-closed.json
	$(BOOTSTRAP_CLI) activate evaluate $(LOCAL_AGENTPOD) $(READY_POLICY) $(READY_GRANT) --deployment-receipt-id $(DEPLOYMENT_RECEIPT_ID) --storage-receipt-dir $(RECEIPT_DIR) --decided-at $(DECIDED_AT) --decision-id urn:srcos:agent-machine:activation-decision:local-llama-cpp-allowed --pretty >/tmp/agent-machine-bootstrap-evaluate-activation-allowed.json
	$(PYCLI) activate evaluate $(LOCAL_AGENTPOD) $(READY_GRANT) --policy-dir $(POLICY_DIR) --expected-status allowed --deployment-receipt-id $(DEPLOYMENT_RECEIPT_ID) --agent-machine-id urn:srcos:agent-machine:m2-asahi-local --provider-id urn:srcos:agent-machine:inference-provider:asahi-llama-cpp --storage-receipt-dir $(RECEIPT_DIR) --decided-at $(DECIDED_AT) --decision-id urn:srcos:agent-machine:activation-decision:local-llama-cpp-allowed --pretty >/tmp/agent-machine-pycli-resolved-policy-activation-allowed.json
	$(PYCLI) activate evaluate $(LOCAL_AGENTPOD) $(READY_POLICY) --grant-dir $(GRANT_DIR) --grant-id urn:srcos:agent-machine:agent-registry-grant:active-loopback-activation --deployment-receipt-id $(DEPLOYMENT_RECEIPT_ID) --requested-agent-identity-ref urn:srcos:agent:local-inference-provider --session-ref urn:srcos:session:local-bootstrap --agent-machine-id urn:srcos:agent-machine:m2-asahi-local --provider-id urn:srcos:agent-machine:inference-provider:asahi-llama-cpp --storage-receipt-dir $(RECEIPT_DIR) --decided-at $(DECIDED_AT) --decision-id urn:srcos:agent-machine:activation-decision:local-llama-cpp-allowed --pretty >/tmp/agent-machine-pycli-resolved-grant-activation-allowed.json
	$(PYCLI) activate evaluate $(LOCAL_AGENTPOD) --policy-dir $(POLICY_DIR) --expected-status allowed --grant-dir $(GRANT_DIR) --grant-id urn:srcos:agent-machine:agent-registry-grant:active-loopback-activation --session-ref urn:srcos:session:local-bootstrap --deployment-receipt-id $(DEPLOYMENT_RECEIPT_ID) --agent-machine-id urn:srcos:agent-machine:m2-asahi-local --provider-id urn:srcos:agent-machine:inference-provider:asahi-llama-cpp --storage-receipt-dir $(RECEIPT_DIR) --decided-at $(DECIDED_AT) --decision-id urn:srcos:agent-machine:activation-decision:local-llama-cpp-allowed --pretty >/tmp/agent-machine-pycli-resolved-policy-grant-activation-allowed.json
	$(BOOTSTRAP_CLI) activate evaluate $(LOCAL_AGENTPOD) $(READY_POLICY) $(READY_GRANT) --deployment-receipt-id $(DEPLOYMENT_RECEIPT_ID) --storage-receipt-dir $(RECEIPT_DIR) --decided-at $(DECIDED_AT) --decision-id urn:srcos:agent-machine:activation-decision:local-llama-cpp-allowed --pretty >/tmp/agent-machine-bootstrap-evaluate-activation-allowed.json

validate-supply-chain:
	$(PYTHON) scripts/validate-supply-chain.py
	$(PYMOD) agent_machine.supply_chain $(PINNED_AGENTPOD) --strict

validate-release-bundle:
	$(PYTHON) scripts/validate-release-bundle.py
	$(PYTHON) scripts/generate-release-evidence.py --pretty >/tmp/agent-machine-release-evidence-bundle.json

validate-sourceos-projections:
	$(PYTHON) scripts/validate-sourceos-projection-fixtures.py
validate-package:
	$(PYTHON) scripts/validate-package.py

validate-cli:
	sh -n $(CLI)
	$(BOOTSTRAP_CLI) version
	$(BOOTSTRAP_CLI) paths
	$(BOOTSTRAP_CLI) doctor --format json
	$(BOOTSTRAP_CLI) probe --format json
	printf '%s\n' '{"prompt":"Write one short sentence about Paris.","model_id":"gpt2-small","steering":{"feature_id":"10200","layer":"6-res-jb","strength":5}}' >/tmp/agent-machine-steer-request.json
	$(PYCLI) steer stub-response /tmp/agent-machine-steer-request.json --pretty >/tmp/agent-machine-pycli-steer-stub-response.json
	$(BOOTSTRAP_CLI) steer stub-response /tmp/agent-machine-steer-request.json --pretty >/tmp/agent-machine-bootstrap-steer-stub-response.json
	$(PYCLI) steer preflight --sourceset gpt2-small.res-jb --pretty >/tmp/agent-machine-pycli-steer-preflight.json
	$(BOOTSTRAP_CLI) steer preflight --sourceset gpt2-small.res-jb --pretty >/tmp/agent-machine-bootstrap-steer-preflight.json
	$(PYCLI) steer resolve-artifacts --sourceset gpt2-small.res-jb --local-dir /tmp/agent-machine-steering-artifacts --receipt-out /tmp/agent-machine-steering-artifact-receipt.json --dry-run --pretty >/tmp/agent-machine-pycli-artifact-receipt.json
	$(PYTHON) scripts/verify-steering-receipt.py examples/steering-artifact-receipts/gpt2-small-res-jb.missing.steering-artifact-receipt.json --expect-status not_configured --pretty >/tmp/agent-machine-steering-load-preflight.json
	$(PYTHON) scripts/verify-steering-receipt.py examples/steering-artifact-receipts/gpt2-small-res-jb.missing.steering-artifact-receipt.json --expect-status not_configured --pretty >/tmp/agent-machine-steering-verify-preflight.json
	$(PYTHON) scripts/load-steering-receipt.py examples/steering-artifact-receipts/synthetic.available.steering-artifact-receipt.json --attempt-load --pretty >/tmp/agent-machine-steering-synthetic-load.json
	$(PYTHON) scripts/run-mock-steering.py /tmp/agent-machine-steer-request.json --pretty >/tmp/agent-machine-mock-steering.json
	$(PYCLI) version
	$(PYCLI) paths --format json
	$(PYCLI) doctor --format json
	$(PYCLI) probe --format json

validate-formula:
	$(RUBY) -c $(FORMULA)

validate-runtime-install-receipts:
	$(PYTHON) scripts/validate-runtime-install-receipts.py

doctor:
	$(BOOTSTRAP_CLI) doctor --format json

probe:
	$(BOOTSTRAP_CLI) probe --format json
	$(BOOTSTRAP_CLI) probe --format json
