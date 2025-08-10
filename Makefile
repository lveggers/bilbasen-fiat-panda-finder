# Bilbasen Fiat Panda Finder - Development Makefile

# Variables
PYTHON = python
PIP = pip
POETRY = poetry
PROJECT_DIR = src/app
TESTS_DIR = tests

.PHONY: help setup install install-dev format lint typecheck test test-unit test-integration test-api test-coverage clean run scrape serve docs build docker-build docker-run precommit

# Default target
help: ## Show this help message
	@echo "Bilbasen Fiat Panda Finder - Development Commands"
	@echo "================================================="
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Setup and Installation
setup: ## Initial project setup
	$(POETRY) install
	$(POETRY) run playwright install chromium
	@echo "✅ Project setup complete!"

install: ## Install production dependencies only
	$(POETRY) install --only=main

install-dev: ## Install all dependencies including development tools
	$(POETRY) install
	$(POETRY) run playwright install chromium
	$(POETRY) run pre-commit install

# Code Quality
format: ## Format code with black and ruff
	$(POETRY) run black $(PROJECT_DIR) $(TESTS_DIR)
	$(POETRY) run ruff format $(PROJECT_DIR) $(TESTS_DIR)
	@echo "✅ Code formatted!"

lint: ## Run linting with ruff
	$(POETRY) run ruff check $(PROJECT_DIR) $(TESTS_DIR)
	@echo "✅ Linting complete!"

lint-fix: ## Run linting with automatic fixes
	$(POETRY) run ruff check --fix $(PROJECT_DIR) $(TESTS_DIR)
	@echo "✅ Linting fixes applied!"

typecheck: ## Run type checking with mypy
	$(POETRY) run mypy $(PROJECT_DIR)
	@echo "✅ Type checking complete!"

# Testing
test: ## Run all tests
	$(POETRY) run pytest $(TESTS_DIR) -v

test-unit: ## Run only unit tests
	$(POETRY) run pytest $(TESTS_DIR) -v -m "unit"

test-integration: ## Run only integration tests
	$(POETRY) run pytest $(TESTS_DIR) -v -m "integration"

test-api: ## Run only API tests
	$(POETRY) run pytest $(TESTS_DIR) -v -m "api"

test-scraper: ## Run only scraper tests (excluding live tests)
	$(POETRY) run pytest $(TESTS_DIR) -v -m "scraper and not live"

test-live: ## Run live tests (requires internet)
	$(POETRY) run pytest $(TESTS_DIR) -v -m "live"

test-coverage: ## Run tests with coverage report
	$(POETRY) run pytest $(TESTS_DIR) --cov=$(PROJECT_DIR) --cov-report=html --cov-report=term-missing
	@echo "📊 Coverage report generated in htmlcov/"

test-fast: ## Run fast tests only (exclude slow and live tests)
	$(POETRY) run pytest $(TESTS_DIR) -v -m "not slow and not live"

# Database
db-init: ## Initialize database tables
	$(POETRY) run python -c "from src.app.db import create_db_and_tables; create_db_and_tables()"

db-clean: ## Remove database file
	rm -f listings.db
	@echo "🗑️ Database cleaned!"

# Scraping and Data
scrape: ## Run scraping process
	$(POETRY) run python -c "import asyncio; from src.app.scraper.scraper import scrape_bilbasen_listings; asyncio.run(scrape_bilbasen_listings(max_pages=3, include_details=True))"

scrape-fast: ## Run quick scraping (1 page, no details)
	$(POETRY) run python -c "import asyncio; from src.app.scraper.scraper import scrape_bilbasen_listings; asyncio.run(scrape_bilbasen_listings(max_pages=1, include_details=False))"

rescore: ## Recalculate scores for all listings
	$(POETRY) run python -c "from src.app.api import rescore_all_listings; from src.app.db import get_session; from sqlmodel import Session; from src.app.db import engine; import asyncio; session = Session(engine); asyncio.run(rescore_all_listings(session))"

# Server
run: ## Run the development server
	$(POETRY) run python src/app/server.py

serve: ## Run the production server with uvicorn
	$(POETRY) run uvicorn src.app.server:app --host 0.0.0.0 --port 8000

serve-dev: ## Run the development server with auto-reload
	$(POETRY) run uvicorn src.app.server:app --host 0.0.0.0 --port 8000 --reload

serve-prod: ## Run the production server
	$(POETRY) run uvicorn src.app.server:app --host 0.0.0.0 --port 8000 --workers 4

# Documentation
docs: ## Open API documentation
	@echo "🌐 Opening API documentation..."
	@echo "Swagger UI: http://localhost:8000/docs"
	@echo "ReDoc: http://localhost:8000/redoc"

# Build and Deploy
build: ## Build the project (check all quality gates)
	@echo "🏗️ Building project..."
	$(MAKE) format
	$(MAKE) lint
	$(MAKE) typecheck
	$(MAKE) test-fast
	@echo "✅ Build complete!"

precommit: ## Run pre-commit hooks on all files
	$(POETRY) run pre-commit run --all-files

# Docker
docker-build: ## Build Docker image
	docker build -t bilbasen-fiat-panda-finder .

docker-run: ## Run Docker container
	docker run -p 8000:8000 bilbasen-fiat-panda-finder

# Cleanup
clean: ## Clean up generated files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage coverage.xml 2>/dev/null || true
	rm -rf dist/ build/ 2>/dev/null || true
	@echo "🧹 Cleanup complete!"

clean-all: clean db-clean ## Clean everything including database
	@echo "🧹 Complete cleanup finished!"

# Development Workflow
dev-setup: setup install-dev ## Complete development setup
	@echo "🚀 Development environment ready!"

dev-check: format lint typecheck test-fast ## Quick development check
	@echo "✅ Development check complete!"

ci-check: ## Full CI check (what runs in GitHub Actions)
	$(MAKE) lint
	$(MAKE) typecheck
	$(MAKE) test-coverage
	@echo "✅ CI check complete!"

# Git hooks
install-hooks: ## Install pre-commit hooks
	$(POETRY) run pre-commit install
	@echo "🪝 Git hooks installed!"

# Status and Info
status: ## Show project status
	@echo "📊 Project Status"
	@echo "=================="
	@echo "Python: $$($(PYTHON) --version)"
	@echo "Poetry: $$($(POETRY) --version)"
	@echo "Dependencies: $$($(POETRY) show --outdated | wc -l) outdated packages"
	@echo ""
	@echo "Database:"
	@if [ -f "listings.db" ]; then \
		echo "  📄 Database exists (size: $$(du -h listings.db | cut -f1))"; \
	else \
		echo "  ❌ No database found"; \
	fi
	@echo ""
	@echo "Tests:"
	@echo "  Unit: $$(find $(TESTS_DIR) -name "test_*.py" -exec grep -l "mark.unit" {} \; | wc -l) files"
	@echo "  Integration: $$(find $(TESTS_DIR) -name "test_*.py" -exec grep -l "mark.integration" {} \; | wc -l) files"
	@echo "  API: $$(find $(TESTS_DIR) -name "test_*.py" -exec grep -l "mark.api" {} \; | wc -l) files"

# Performance
profile-scraper: ## Profile the scraper performance
	$(POETRY) run python -m cProfile -o scraper.prof -c "import asyncio; from src.app.scraper.scraper import scrape_bilbasen_listings; asyncio.run(scrape_bilbasen_listings(max_pages=1, include_details=False))"
	@echo "📊 Profiling complete! View with: snakeviz scraper.prof"

# Logs
logs: ## Show recent application logs
	@if [ -f "app.log" ]; then \
		tail -f app.log; \
	else \
		echo "❌ No log file found. Run the application first."; \
	fi

# Quick Commands
quick-start: ## Quick start: setup, scrape some data, and run server
	$(MAKE) setup
	$(MAKE) scrape-fast
	$(MAKE) run

demo: ## Demo mode: setup everything and run with sample data
	$(MAKE) dev-setup
	$(MAKE) scrape-fast
	@echo "🎬 Demo ready! Starting server..."
	$(MAKE) serve-dev