# Network Assessment lab edition. Every target is a plain uv invocation; nothing reaches a cloud.
.PHONY: setup lint test run image e2e rules-doc package clean

setup:
	uv python pin 3.14.6
	uv sync

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run python scripts/rules-doc.py --check

test:
	uv run pytest -q --cov=src --cov-report=term-missing

run:
	NA_ALLOW_NO_TURNSTILE=1 PORT=8080 uv run python -m network_assessment

image:
	docker build -f infrastructure/docker/Dockerfile --build-arg EDITION=lab -t hcw-networkeyes:dev .

e2e:
	npx --yes playwright@1.63.0 test -c tests/e2e/playwright.config.ts

rules-doc:
	uv run python scripts/rules-doc.py --write

package:
	bash scripts/package-repository.sh

clean:
	rm -rf .venv .pytest_cache .ruff_cache .coverage htmlcov hcw-networkeyes-addon.zip test-results playwright-report
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
