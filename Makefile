# URL Shortener - Makefile

TESTS_TO_RUN ?= tests/
DOCKER_COMPOSE := docker-compose -f tests/docker-compose.yml

.PHONY: tests load docker-up docker-down docker-clean clean

docker-up: ## Start test database and Redis
	@echo "Starting test containers..."
	$(DOCKER_COMPOSE) up -d --remove-orphans 2>/dev/null || $(DOCKER_COMPOSE) up -d
	@sleep 3
	@echo "Test containers ready!"

docker-down: ## Stop test containers
	$(DOCKER_COMPOSE) down

docker-clean: ## Stop and remove test containers and volumes
	$(DOCKER_COMPOSE) down -v
	@echo "Test containers cleaned!"

tests: docker-up ## Run tests (usage: make tests TESTS_TO_RUN=tests/func/test_auth.py)
	pytest $(TESTS_TO_RUN) --cov=app --cov-report=term-missing --ignore=tests/load

load: check-locust ## Run load testing with Locust (web UI)
	locust -f tests/load/locustfile.py --host=http://localhost:8000

check-locust: ## Check if locust is installed
	@which locust > /dev/null 2>&1 || (echo "Error: locust is not installed. Run: pip install locust" && exit 1)

clean: ## Remove coverage and cache files
	rm -rf htmlcov .coverage
	find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete 2>/dev/null || true
	@echo "Cleaned!"

coverage: tests ## Run tests and open coverage report
	@echo "Opening coverage report..."
	open htmlcov/index.html 2>/dev/null || xdg-open htmlcov/index.html 2>/dev/null || echo "Open htmlcov/index.html in your browser"
