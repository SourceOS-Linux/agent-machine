.PHONY: validate validate-json validate-yaml validate-quadlet validate-render validate-evidence validate-governance validate-activation validate-package validate-cli validate-formula doctor probe

PYTHON ?= python3
RUBY ?= ruby
CLI := bin/agent-machine
FORMULA := packaging/homebrew/Formula/agent-machine.rb
LOCAL_AGENTPOD := examples/local-podman-llama-cpp.agent-pod.json
K8S_AGENTPOD := examples/k8s-topolvm.agent-pod.json
LOCAL_QUADLET := deploy/quadlet/agent-machine-llama-cpp.container
K8S_MANIFEST := deploy/k8s/llama-cpp-topolvm-pod.yaml
READY_POLICY := examples/policy-admission.allowed-activation.json
READY_GRANT := examples/agent-registry-grant.active-activation.json
FAIL_POLICY := examples/policy-admission.missing.json
FAIL_GRANT := examples/agent-registry-grant.missing.json
RECEIPT_DIR := examples
DEPLOYMENT_RECEIPT_ID := urn:srcos:agent-machine:deployment-receipt:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
DECIDED_AT := 2026-05-04T12:51:00Z
PYCLI := PYTHONPATH=src $(PYTHON) -m agent_machine.cli

validate: validate-json validate-yaml validate-quadlet validate-render validate-evidence validate-governance validate-activation validate-package validate-cli validate-formula

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
	$(CLI) render plan $(LOCAL_AGENTPOD) --pretty >/tmp/agent-machine-bootstrap-local-agentpod-plan.json
	$(CLI) render quadlet $(LOCAL_AGENTPOD) --compare $(LOCAL_QUADLET)
	$(CLI) render k8s $(K8S_AGENTPOD) --compare $(K8S_MANIFEST)

validate-evidence:
	$(PYTHON) scripts/validate-evidence.py

validate-governance:
	$(PYTHON) scripts/validate-governance.py

validate-activation:
	$(PYTHON) scripts/validate-activation.py
	$(PYTHON) scripts/evaluate-activation.py $(LOCAL_AGENTPOD) $(READY_POLICY) $(READY_GRANT) --deployment-receipt-id $(DEPLOYMENT_RECEIPT_ID) --storage-receipt-dir $(RECEIPT_DIR) --decided-at $(DECIDED_AT) --decision-id urn:srcos:agent-machine:activation-decision:local-llama-cpp-allowed --pretty >/tmp/agent-machine-evaluate-activation-allowed.json
	$(PYCLI) activate evaluate $(LOCAL_AGENTPOD) $(FAIL_POLICY) $(FAIL_GRANT) --deployment-receipt-id $(DEPLOYMENT_RECEIPT_ID) --storage-receipt-dir $(RECEIPT_DIR) --decided-at $(DECIDED_AT) --decision-id urn:srcos:agent-machine:activation-decision:local-llama-cpp-fail-closed --pretty >/tmp/agent-machine-pycli-evaluate-activation-fail-closed.json
	$(CLI) activate evaluate $(LOCAL_AGENTPOD) $(READY_POLICY) $(READY_GRANT) --deployment-receipt-id $(DEPLOYMENT_RECEIPT_ID) --storage-receipt-dir $(RECEIPT_DIR) --decided-at $(DECIDED_AT) --decision-id urn:srcos:agent-machine:activation-decision:local-llama-cpp-allowed --pretty >/tmp/agent-machine-bootstrap-evaluate-activation-allowed.json

validate-package:
	$(PYTHON) scripts/validate-package.py

validate-cli:
	sh -n $(CLI)
	chmod +x $(CLI)
	$(CLI) version
	$(CLI) paths
	$(CLI) doctor --format json
	$(CLI) probe --format json
	$(PYCLI) version
	$(PYCLI) paths --format json
	$(PYCLI) doctor --format json
	$(PYCLI) probe --format json

validate-formula:
	$(RUBY) -c $(FORMULA)

doctor:
	$(CLI) doctor --format json

probe:
	$(CLI) probe --format json
