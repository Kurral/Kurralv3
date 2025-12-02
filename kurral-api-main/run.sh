#!/bin/bash

# Kurral API Run Script (without dependency installation)

echo "🚀 Starting Kurral API..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found!"
    echo "Please create .env file from .env.template"
    exit 1
fi

# Check if running in Docker
if [ -f /.dockerenv ]; then
    echo "📦 Running in Docker container"
    exec uvicorn main:app --host 0.0.0.0 --port 8001
else
    echo "💻 Running in local environment"

    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        echo "❌ Virtual environment not found!"
        echo "Please run ./start.sh first to create venv and install dependencies"
        exit 1
    fi

    # Activate virtual environment
    source venv/bin/activate

    # Run application
    echo "✅ Starting server on http://localhost:8001"
    echo "📚 API docs: http://localhost:8001/docs"
    echo ""
    uvicorn main:app --reload --host 0.0.0.0 --port 8001
fi
