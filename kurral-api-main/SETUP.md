# Kurral API Setup Guide

## 🚀 Quick Start

### 1. Create Environment File

Copy the template and fill in your credentials:

```bash
cp .env.template .env
```

Edit `.env` with your actual values:

```env
# Required - Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
SECRET_KEY=your-generated-secret-key

# Required - PostgreSQL connection
DATABASE_URL=postgresql://kurral:password@localhost:5432/kurral_db

# Required - Cloudflare R2 credentials
R2_ACCOUNT_ID=your-cloudflare-account-id
R2_ACCESS_KEY_ID=your-r2-access-key
R2_SECRET_ACCESS_KEY=your-r2-secret-key
R2_BUCKET_NAME=kurral-artifacts
```

### 2. Start with Docker (Easiest)

```bash
# Start all services (PostgreSQL + API)
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

### 3. Or Start Manually

```bash
# Use the startup script
./start.sh

# Or manually:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

## 📊 Access Points

- **API**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## 🔑 Initial Setup

### Create Your First User

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your@email.com",
    "password": "secure-password",
    "tenant_id": "my-company",
    "full_name": "Your Name"
  }'
```

### Login to Get JWT Token

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your@email.com",
    "password": "secure-password"
  }'
```

Response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

### Create an API Key

```bash
curl -X POST http://localhost:8000/api/v1/api-keys \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My First API Key",
    "description": "For testing",
    "scopes": ["read:artifacts", "write:artifacts"]
  }'
```

**Save the API key!** It's only shown once:
```json
{
  "api_key": "kurral_abc123def456...",
  "name": "My First API Key",
  ...
}
```

## 📦 Upload Your First Artifact

```bash
# Example artifact
cat > artifact.json << 'EOF'
{
  "artifact_data": {
    "kurral_id": "550e8400-e29b-41d4-a716-446655440000",
    "run_id": "test_run_001",
    "tenant_id": "my-company",
    "semantic_buckets": ["test"],
    "environment": "development",
    "created_at": "2024-01-15T10:30:00Z",
    "deterministic": true,
    "replay_level": "A",
    "llm_config": {
      "model_name": "gpt-4",
      "provider": "openai",
      "parameters": {
        "temperature": 0.0
      }
    },
    "resolved_prompt": {
      "template": "Test prompt",
      "variables": {},
      "final_text": "Test prompt"
    },
    "inputs": {"query": "test"},
    "outputs": {"response": "test response"},
    "tool_calls": [],
    "time_env": {
      "timestamp": "2024-01-15T10:30:00Z",
      "timezone": "UTC"
    },
    "token_usage": {
      "prompt_tokens": 10,
      "completion_tokens": 20,
      "total_tokens": 30
    },
    "duration_ms": 1500,
    "determinism_report": {
      "overall_score": 0.95,
      "breakdown": {},
      "missing_fields": [],
      "warnings": []
    }
  }
}
EOF

# Upload
curl -X POST http://localhost:8000/api/v1/artifacts/upload \
  -H "X-API-Key: kurral_YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d @artifact.json
```

## 🔍 Query Artifacts

```bash
# List all artifacts
curl "http://localhost:8000/api/v1/artifacts?page=1&page_size=10" \
  -H "X-API-Key: kurral_YOUR_API_KEY"

# Filter by environment
curl "http://localhost:8000/api/v1/artifacts?environment=production&deterministic=true" \
  -H "X-API-Key: kurral_YOUR_API_KEY"

# Get specific artifact
curl "http://localhost:8000/api/v1/artifacts/550e8400-e29b-41d4-a716-446655440000" \
  -H "X-API-Key: kurral_YOUR_API_KEY"
```

## 📈 View Statistics

```bash
# Overall stats
curl "http://localhost:8000/api/v1/stats" \
  -H "X-API-Key: kurral_YOUR_API_KEY"

# Time series (last 7 days)
curl "http://localhost:8000/api/v1/stats/timeseries?days=7" \
  -H "X-API-Key: kurral_YOUR_API_KEY"
```

## 🔧 Cloudflare R2 Setup

### 1. Create R2 Bucket

1. Go to [Cloudflare Dashboard](https://dash.cloudflare.com/) → R2
2. Click "Create bucket"
3. Name it `kurral-artifacts` (or your preferred name)
4. Click "Create bucket"

### 2. Generate API Token

1. In R2, click "Manage R2 API Tokens"
2. Click "Create API token"
3. Name: "Kurral API Access"
4. Permissions: "Object Read & Write"
5. Click "Create API Token"
6. **Copy these values** and add to your `.env`:
   - Account ID
   - Access Key ID
   - Secret Access Key

### 3. Update .env

```env
R2_ACCOUNT_ID=abc123def456
R2_ACCESS_KEY_ID=789ghi012jkl
R2_SECRET_ACCESS_KEY=mno345pqr678stu901vwx234yz
R2_BUCKET_NAME=kurral-artifacts
```

## 🐛 Troubleshooting

### Database Connection Error

```bash
# Check if PostgreSQL is running
docker-compose ps

# Check logs
docker-compose logs postgres

# Restart database
docker-compose restart postgres
```

### R2 Upload Failed

- Verify R2 credentials in `.env`
- Check bucket name matches
- Test R2 connection:
  ```bash
  aws s3 ls --endpoint-url https://YOUR_ACCOUNT_ID.r2.cloudflarestorage.com
  ```

### API Key Not Working

- Ensure it starts with `kurral_`
- Check it hasn't been revoked
- Verify scopes include required permissions
- Check expiration date

## 🧪 Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=app --cov-report=html

# Specific test file
pytest tests/test_artifacts.py -v
```

## 📚 Next Steps

1. ✅ Set up Cloudflare R2
2. ✅ Create your user account
3. ✅ Generate API key
4. ✅ Upload first artifact
5. 🎯 Integrate with Kurral CLI
6. 📊 Set up monitoring/alerting
7. 🚀 Deploy to production

## 🔐 Security Checklist

- [ ] Change `SECRET_KEY` to a strong random value
- [ ] Use environment-specific `.env` files
- [ ] Enable HTTPS in production
- [ ] Set up rate limiting
- [ ] Configure CORS for your domains
- [ ] Rotate API keys regularly
- [ ] Monitor failed auth attempts
- [ ] Enable database backups
- [ ] Set up R2 bucket policies

## 📞 Support

For issues or questions:
- Check logs: `docker-compose logs -f api`
- Review documentation: `README.md`
- Check API docs: http://localhost:8000/docs

