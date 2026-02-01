# FinAgent - Development Commands
# Usage: make <command>

.PHONY: help install test test-cov backend frontend dev setup-hooks clean

help:
	@echo "FinAgent Development Commands"
	@echo ""
	@echo "  make install      - Install all dependencies"
	@echo "  make test         - Run backend tests"
	@echo "  make test-cov     - Run tests with coverage"
	@echo "  make backend      - Start backend server"
	@echo "  make frontend     - Start frontend dev server"
	@echo "  make dev          - Start both servers"
	@echo "  make setup-hooks  - Install git pre-commit hook"
	@echo "  make clean        - Clean cache files"

# Install dependencies
install:
	@echo "📦 Installing backend dependencies..."
	cd backend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt
	@echo "📦 Installing frontend dependencies..."
	cd frontend && npm install
	@echo "✅ Installation complete!"

# Run backend tests
test:
	@echo "🧪 Running backend tests..."
	cd backend && source venv/bin/activate && python -m pytest tests/ -v

# Run tests with coverage
test-cov:
	@echo "🧪 Running tests with coverage..."
	cd backend && source venv/bin/activate && python -m pytest tests/ --cov=. --cov-report=html --cov-report=term-missing
	@echo "📊 Coverage report: backend/htmlcov/index.html"

# Start backend server
backend:
	@echo "🚀 Starting backend server..."
	cd backend && source venv/bin/activate && uvicorn main:app --reload --port 8000

# Start frontend dev server
frontend:
	@echo "🚀 Starting frontend server..."
	cd frontend && npm run dev

# Start both servers (requires terminal multiplexer or run in separate terminals)
dev:
	@echo "🚀 Starting development servers..."
	@echo "Run 'make backend' and 'make frontend' in separate terminals"

# Install git hooks
setup-hooks:
	@echo "🔧 Setting up git hooks..."
	cp scripts/pre-commit .git/hooks/pre-commit
	chmod +x .git/hooks/pre-commit
	@echo "✅ Pre-commit hook installed!"

# Clean cache files
clean:
	@echo "🧹 Cleaning cache files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Clean complete!"
