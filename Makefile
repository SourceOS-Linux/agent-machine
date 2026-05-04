.PHONY: validate validate-json validate-yaml validate-quadlet validate-render validate-cli validate-formula doctor probe

PYTHON ?= python3
RUBY ?= ruby
CLI := bin/agent-machine
FORMULA := packaging/homebrew/Formula/agent-machine.rb

validate: validate-json validate-yaml validate-quadlet validate-render validate-cli validate-formula

validate-json:
	$(PYTHON) scripts/validate-json.py

validate-yaml:
	$(PYTHON) scripts/validate-yaml.py

validate-quadlet:
	$(PYTHON) scripts/validate-quadlet.py

validate-render:
	$(PYTHON) scripts/render-agentpod-plan.py examples/local-podman-llama-cpp.agent-pod.json --pretty >/tmp/agent-machine-local-agentpod-plan.json
	$(PYTHON) scripts/render-agentpod-plan.py examples/k8s-topolvm.agent-pod.json --pretty >/tmp/agent-machine-k8s-agentpod-plan.json

validate-cli:
	sh -n $(CLI)
	chmod +x $(CLI)
	$(CLI) version
	$(CLI) paths
	$(CLI) doctor --format json
	$(CLI) probe --format json

validate-formula:
	$(RUBY) -c $(FORMULA)

doctor:
	$(CLI) doctor --format json

probe:
	$(CLI) probe --format json
