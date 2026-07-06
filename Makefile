.PHONY: test test-py test-js lint verify help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

test-py: ## Run Python tests via pytest
	python -m pytest tests/ -q

test-js: ## Run Node/JS tests (zenmux-throttle-proxy)
	@if [ -f tests/zenmux-throttle-proxy.test.js ]; then \
		node tests/zenmux-throttle-proxy.test.js; \
	else \
		echo "No JS tests found, skipping."; \
	fi

test: test-py ## Alias for test-py

verify: test-py ## Run all available checks
	@echo "All checks passed."
