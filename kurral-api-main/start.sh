#!/bin/bash

# Kurral API Startup Script

echo "🚀 Starting Kurral API..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found!"
    echo "Please create .env file with the following variables:"
    echo ""
    echo "DATABASE_URL=postgresql://kurral:password@localhost:5432/kurral_db"
    echo "SECRET_KEY=your-secret-key-here"
    echo "R2_ACCOUNT_ID=your-r2-account-id"
    echo "R2_ACCESS_KEY_ID=your-r2-access-key"
    echo "R2_SECRET_ACCESS_KEY=your-r2-secret-key"
    echo "R2_BUCKET_NAME=kurral-artifacts"
    echo ""
    exit 1
fi

# Check if running in Docker
if [ -f /.dockerenv ]; then
    echo "📦 Running in Docker container"
    exec uvicorn main:app --host 0.0.0.0 --port 8000
else
    echo "💻 Running in local environment"
    
    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Install dependencies
    echo "Installing dependencies..."
    pip install -r requirements.txt
    
    # Run application
    echo "✅ Starting server on http://localhost:8001"
    uvicorn main:app --reload --host 0.0.0.0 --port 8001
fi

