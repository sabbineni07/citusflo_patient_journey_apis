# Makefile for CitusFlo Patient Journey APIs

.PHONY: help install test test-unit test-integration test-e2e test-coverage lint format clean docker-build docker-run docker-dev docker-prod docker-stop migrate init-db

# Default target
help:
	@echo "Available commands:"
	@echo "  install          Install dependencies"
	@echo "  test             Run all tests"
	@echo "  test-unit        Run unit tests only"
	@echo "  test-integration Run integration tests only"
	@echo "  test-e2e         Run end-to-end tests only"
	@echo "  test-coverage    Run tests with coverage report"
	@echo "  lint             Run code linting"
	@echo "  format           Format code with black"
	@echo "  clean            Clean up temporary files"
	@echo "  docker-build     Build Docker image"
	@echo "  docker-run       Run Docker container"
	@echo "  docker-dev       Start development environment"
	@echo "  docker-prod      Start production environment"
	@echo "  docker-stop      Stop all Docker containers"
	@echo "  migrate          Run database migrations"
	@echo "  init-db          Initialize database with sample data"

# Install dependencies
install:
	pip install -r requirements.txt

# Testing
test:
	pytest

test-unit:
	pytest -m unit

test-integration:
	pytest -m integration

test-e2e:
	pytest -m e2e

test-coverage:
	pytest --cov=app --cov-report=html --cov-report=term-missing

# Code quality
lint:
	flake8 app/
	pylint app/

format:
	black app/
	isort app/

# Clean up
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/
	rm -rf dist/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/

# Docker commands
docker-build:
	docker build -t citusflo-patient-journey-api .

docker-run:
	docker run -p 5000:5000 --env-file .env citusflo-patient-journey-api

docker-dev:
	docker-compose -f docker-compose.dev.yml up --build

docker-prod:
	docker-compose up --build

docker-stop:
	docker-compose down
	docker-compose -f docker-compose.dev.yml down

# Database commands
migrate:
	flask db upgrade

init-db:
	flask init-db

# Development setup
dev-setup: install
	cp env.example .env
	@echo "Please edit .env file with your configuration"
	@echo "Then run: make docker-dev"

# Production setup
prod-setup: install
	cp env.example .env
	@echo "Please edit .env file with your production configuration"
	@echo "Then run: make docker-prod"

# AWS deployment
aws-deploy:
	chmod +x aws/deploy.sh
	./aws/deploy.sh

# Quick start
quick-start: dev-setup
	@echo "Starting development environment..."
	make docker-dev
