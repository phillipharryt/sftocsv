.PHONY: test
test: ## Execute Python tests
	echo -e Executing tests
	coverage run --source=. -m pytest tests/ -s -vv && \
	coverage report && \
	coverage html --show-contexts && \
	coverage xml
	