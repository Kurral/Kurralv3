# Kurral API

FastAPI backend for centralized Kurral artifact management with authentication, R2 storage, and analytics.

## Features

- 🔐 **API Key Authentication** - Secure API key management with scopes and rate limiting
- 📦 **Artifact Management** - Upload, download, and query LLM artifacts with enhanced schema
- ☁️ **Cloudflare R2 Storage** - Scalable object storage for full artifacts
- 📊 **Analytics & Statistics** - Real-time insights, time series, and aggregations
- 🔍 **Advanced Filtering** - Query by tenant, environment, semantic bucket, model, dates, and more
- 🔗 **Execution Graph Support** - Parent-child tool call relationships for nested operations
- ⏱️ **Precise Timing** - Start/end timestamps for concurrency analysis and external correlation
- 🚨 **Error Forensics** - Comprehensive error tracking with types, messages, and stack traces
- 🔮 **Extensible Metadata** - Future-proof schema with custom attributes
- 🚀 **High Performance** - Built with FastAPI and PostgreSQL with optimized indexes
- 🐳 **Docker Support** - Easy deployment with Docker Compose

## Quick Start

### Using Docker Compose (Recommended)

1. **Clone and navigate to the API directory:**
   ```bash
   git clone https://github.com/kurral/kurralv3.git
   cd kurralv3/kurral/storage
   ```

2. **Create `.env` file:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start services:**
   ```bash
   docker-compose up -d
   ```

4. **Access the API:**
   - API: http://localhost:8000
   - Docs: http://localhost:8000/docs
   - Health: http://localhost:8000/health

### Manual Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up PostgreSQL:**
   ```bash
   createdb kurral_db
   ```

3. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. **Run migrations:**
   ```bash
   alembic upgrade head
   ```

5. **Start the server:**
   ```bash
   uvicorn main:app --reload
   ```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `SECRET_KEY` | Secret key for JWT tokens | Yes |
| `R2_ACCOUNT_ID` | Cloudflare R2 account ID | Yes |
| `R2_ACCESS_KEY_ID` | R2 access key | Yes |
| `R2_SECRET_ACCESS_KEY` | R2 secret key | Yes |
| `R2_BUCKET_NAME` | R2 bucket name | Yes |
| `ENVIRONMENT` | Environment name | No |
| `DEBUG` | Enable debug mode | No |
| `CORS_ORIGINS` | Allowed CORS origins | No |

### Cloudflare R2 Setup

1. **Create an R2 bucket:**
   - Go to Cloudflare Dashboard > R2
   - Create a new bucket (e.g., `kurral-artifacts`)

2. **Generate API credentials:**
   - Go to R2 > Manage R2 API Tokens
   - Create API token with read/write permissions
   - Copy Account ID, Access Key, and Secret Key

3. **Update `.env`:**
   ```env
   R2_ACCOUNT_ID=your-account-id
   R2_ACCESS_KEY_ID=your-access-key
   R2_SECRET_ACCESS_KEY=your-secret-key
   R2_BUCKET_NAME=kurral-artifacts
   ```

## API Documentation

### Authentication

The API supports two authentication methods:

1. **JWT Tokens** (for web apps):
   ```bash
   # Register
   curl -X POST http://localhost:8000/api/v1/auth/register \
     -H "Content-Type: application/json" \
     -d '{
       "email": "user@example.com",
       "password": "securepassword",
       "tenant_id": "acme-corp",
       "full_name": "John Doe"
     }'
   
   # Login
   curl -X POST http://localhost:8000/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{
       "email": "user@example.com",
       "password": "securepassword"
     }'
   ```

2. **API Keys** (for CLI/scripts):
   ```bash
   # Create API key (requires JWT token)
   curl -X POST http://localhost:8000/api/v1/api-keys \
     -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Production Key",
       "scopes": ["read:artifacts", "write:artifacts"]
     }'
   
   # Use API key
   curl http://localhost:8000/api/v1/artifacts \
     -H "X-API-Key: kurral_YOUR_API_KEY"
   ```

### Artifact Management

**Upload an artifact:**
```bash
curl -X POST http://localhost:8000/api/v1/artifacts/upload \
  -H "X-API-Key: kurral_YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d @artifact.json
```

**List artifacts:**
```bash
curl "http://localhost:8000/api/v1/artifacts?page=1&page_size=50&environment=production" \
  -H "X-API-Key: kurral_YOUR_API_KEY"
```

**Get artifact:**
```bash
curl "http://localhost:8000/api/v1/artifacts/{kurral_id}" \
  -H "X-API-Key: kurral_YOUR_API_KEY"
```

**Query with filters:**
```bash
curl "http://localhost:8000/api/v1/artifacts?semantic_bucket=payment_processing&deterministic=true" \
  -H "X-API-Key: kurral_YOUR_API_KEY"
```

### Statistics

**Get overall stats:**
```bash
curl "http://localhost:8000/api/v1/stats" \
  -H "X-API-Key: kurral_YOUR_API_KEY"
```

**Get time series data:**
```bash
curl "http://localhost:8000/api/v1/stats/timeseries?days=7" \
  -H "X-API-Key: kurral_YOUR_API_KEY"
```

## API Endpoints

### Authentication (`/api/v1/auth`)
- `POST /register` - Register new user
- `POST /login` - Login and get JWT token
- `POST /refresh` - Refresh JWT token

### Users (`/api/v1/users`)
- `GET /me` - Get current user profile
- `PATCH /me` - Update current user
- `GET /` - List all users (admin only)

### API Keys (`/api/v1/api-keys`)
- `POST /` - Create new API key
- `GET /` - List user's API keys
- `GET /{key_id}` - Get API key details
- `PATCH /{key_id}` - Update API key
- `POST /{key_id}/revoke` - Revoke API key
- `DELETE /{key_id}` - Delete API key

### Artifacts (`/api/v1/artifacts`)
- `POST /upload` - Upload artifact
- `GET /` - List artifacts with filtering
- `GET /{kurral_id}` - Get full artifact
- `GET /{kurral_id}/metadata` - Get artifact metadata only
- `DELETE /{kurral_id}` - Delete artifact
- `GET /semantic-buckets/list` - List semantic buckets

### Statistics (`/api/v1/stats`)
- `GET /` - Get aggregated statistics
- `GET /timeseries` - Get time series data

## Integration with Kurral CLI

Configure Kurral to use the API:

```python
from kurral import configure

configure(
    storage_backend="api",
    api_url="http://localhost:8000/api/v1",
    api_key="kurral_YOUR_API_KEY"
)
```

Or via environment variables:

```bash
export KURRAL_STORAGE_BACKEND=api
export KURRAL_API_URL=http://localhost:8000/api/v1
export KURRAL_API_KEY=kurral_YOUR_API_KEY
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Kurral API Backend                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  FastAPI Application                                            │
│  ├─ Authentication (JWT + API Keys)                             │
│  ├─ Artifact Upload/Download                                    │
│  ├─ Advanced Query Engine                                       │
│  └─ Analytics & Statistics                                      │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  PostgreSQL (Metadata)           Cloudflare R2 (Artifacts)      │
│  ├─ Indexed queries              ├─ Full .kurral files          │
│  ├─ Fast filtering               ├─ Scalable storage            │
│  └─ Aggregations                 └─ Cost-effective              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Security

- All passwords are hashed with bcrypt
- JWT tokens for web authentication
- API keys hashed in database
- Scope-based access control
- Rate limiting per API key
- CORS configuration
- SQL injection protection (SQLAlchemy ORM)

## License

Apache 2.0

## Support

- **GitHub Issues**: [github.com/kurral/kurralv3/issues](https://github.com/kurral/kurralv3/issues)
- **Discord**: [discord.gg/pan6GRRV](https://discord.gg/pan6GRRV)
- **Email**: team@kurral.com
