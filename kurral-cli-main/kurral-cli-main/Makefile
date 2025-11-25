.PHONY: help install dev test lint format clean docker-up docker-down

help:
	@echo "Kurral - Development Commands"
	@echo ""
	@echo "install       - Install package in production mode"
	@echo "dev           - Install package in development mode"
	@echo "test          - Run tests"
	@echo "lint          - Run linters"
	@echo "format        - Format code"
	@echo "clean         - Clean build artifacts"
	@echo "docker-up     - Start Docker services"
	@echo "docker-down   - Stop Docker services"

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

test:
	pytest tests/ -v --cov=kurral

lint:
	ruff check kurral/
	mypy kurral/

format:
	black kurral/ tests/ examples/
	ruff check --fix kurral/

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

docker-up:
	docker-compose up -d
	@echo "Waiting for services to be ready..."
	@sleep 5
	@echo "✅ Services started:"
	@echo "  - PostgreSQL: localhost:5432"
	@echo "  - Redis: localhost:6379"
	@echo "  - MinIO: http://localhost:9001 (admin/minioadmin)"

docker-down:
	docker-compose down

init-db:
	python -c "from kurral.storage.postgres import PostgresStorage; storage = PostgresStorage('postgresql://kurral:kurral@localhost:5432/kurral'); storage.create_tables(); print('✅ Database initialized')"

