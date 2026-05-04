.PHONY: validate validate-json validate-cli validate-formula doctor probe

PYTHON ?= python3
RUBY ?= ruby
CLI := bin/agent-machine
FORMULA := packaging/homebrew/Formula/agent-machine.rb

validate: validate-json validate-cli validate-formula

validate-json:
	$(PYTHON) scripts/validate-json.py

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
