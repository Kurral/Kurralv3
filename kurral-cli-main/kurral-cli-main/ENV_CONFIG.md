# Kurral Environment Configuration Guide

Complete reference for configuring Kurral using environment variables.

## Storage Backend Options

Choose one of the following storage modes:

### Option 1: Kurral Cloud API (Recommended for Production)

Upload artifacts to Kurral's managed cloud storage via API authentication.

```bash
# Storage mode
export KURRAL_STORAGE_BACKEND=api

# API credentials (get from https://app.kurral.io/settings/api-keys)
export KURRAL_API_KEY=kurral_live_1234567890abcdef
export KURRAL_API_URL=https://api.kurral.io
```

**Benefits:**
- ✅ No R2 credentials needed
- ✅ Multi-tenant isolation
- ✅ Metadata indexing & fast queries
- ✅ Cost tracking & analytics
- ✅ Automatic backup & versioning

**Flow:**
```
Your Agent → Kurral SDK → HTTP POST → Kurral API → PostgreSQL + R2
```

---

### Option 2: Custom Bucket (Your Own R2/S3)

Store artifacts in your own cloud storage bucket. Supports Cloudflare R2, AWS S3, or S3-compatible services.

#### For Cloudflare R2:

```bash
# Enable custom bucket
export KURRAL_CUSTOM_BUCKET_ENABLED=true

# Bucket details
export KURRAL_CUSTOM_BUCKET_NAME=my-artifacts-bucket
export KURRAL_CUSTOM_BUCKET_ACCOUNT_ID=your_cloudflare_account_id
export KURRAL_CUSTOM_BUCKET_REGION=auto

# Access credentials
export KURRAL_CUSTOM_BUCKET_ACCESS_KEY_ID=your_access_key_id
export KURRAL_CUSTOM_BUCKET_SECRET_ACCESS_KEY=your_secret_access_key
```

#### For AWS S3:

```bash
# Enable custom bucket
export KURRAL_CUSTOM_BUCKET_ENABLED=true

# Bucket details
export KURRAL_CUSTOM_BUCKET_NAME=my-s3-bucket
export KURRAL_CUSTOM_BUCKET_REGION=us-east-1

# Access credentials
export KURRAL_CUSTOM_BUCKET_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
export KURRAL_CUSTOM_BUCKET_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

#### For S3-Compatible Services (MinIO, DigitalOcean Spaces, etc.):

```bash
# Enable custom bucket
export KURRAL_CUSTOM_BUCKET_ENABLED=true

# Bucket details
export KURRAL_CUSTOM_BUCKET_NAME=my-bucket
export KURRAL_CUSTOM_BUCKET_ENDPOINT=https://nyc3.digitaloceanspaces.com
export KURRAL_CUSTOM_BUCKET_REGION=us-east-1

# Access credentials
export KURRAL_CUSTOM_BUCKET_ACCESS_KEY_ID=your_access_key
export KURRAL_CUSTOM_BUCKET_SECRET_ACCESS_KEY=your_secret_key
```

**Benefits:**
- ✅ Full control over storage
- ✅ Direct bucket access
- ✅ No API dependency
- ✅ Use existing infrastructure

**Flow:**
```
Your Agent → Kurral SDK → boto3 → Your R2/S3 Bucket (direct)
```

---

### Option 3: Local Storage (Default)

Save artifacts to local disk.

```bash
# Storage mode (default)
export KURRAL_STORAGE_BACKEND=local

# Optional: custom path (default: ./artifacts)
export KURRAL_LOCAL_STORAGE_PATH=./my-artifacts
```

**Use cases:**
- Development and testing
- Local debugging
- Offline workflows

---

### Option 4: Memory Storage

Store artifacts in RAM for fast access with zero I/O overhead.

```bash
# Storage mode
export KURRAL_STORAGE_BACKEND=memory

# Optional: limits
export KURRAL_MEMORY_MAX_ARTIFACTS=1000
export KURRAL_MEMORY_MAX_SIZE_MB=500
```

**Use cases:**
- Unit testing
- CI/CD pipelines
- Performance testing
- Development

**Commands:**
```bash
kurral memory stats              # Show memory usage
kurral memory list               # List artifacts in memory
kurral memory get <id>           # Get artifact details
kurral memory export <id> <path> # Export to disk
kurral memory clear              # Clear all artifacts
```

---

### Option 5: Legacy R2 Mode (Deprecated)

Direct upload to Kurral's shared R2 bucket.

⚠️ **DEPRECATED:** Use Option 1 (api mode) instead.

```bash
export KURRAL_STORAGE_BACKEND=r2
export KURRAL_R2_BUCKET=kurral-artifacts
export KURRAL_R2_ACCOUNT_ID=your_cloudflare_account_id
export KURRAL_R2_ACCESS_KEY_ID=your_r2_access_key_id
export KURRAL_R2_SECRET_ACCESS_KEY=your_r2_secret_access_key
```

---

## LangSmith Integration (Optional)

Enable LangSmith for trace enrichment and parallel logging.

```bash
# Enable LangSmith
export KURRAL_LANGSMITH_ENABLED=true
export KURRAL_LANGSMITH_API_KEY=lsv2_sk_...
export KURRAL_LANGSMITH_PROJECT=default
```

Or use standard LangSmith environment variables (auto-detected):

```bash
export LANGSMITH_API_KEY=lsv2_sk_...
export LANGSMITH_PROJECT=default
```

---

## General Configuration

```bash
# Environment name (for artifact tagging)
export KURRAL_ENVIRONMENT=production  # or development, staging, etc.

# Debug mode (verbose logging)
export KURRAL_DEBUG=true

# Log level
export KURRAL_LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR

# Auto-export artifacts after each trace
export KURRAL_AUTO_EXPORT=true
```

---

## Advanced Configuration

```bash
# Replay settings
export KURRAL_REPLAY_CACHE_TTL=3600
export KURRAL_REPLAY_MAX_RETRIES=3

# Backtest settings
export KURRAL_BACKTEST_DEFAULT_THRESHOLD=0.90
export KURRAL_BACKTEST_MAX_REPLAYS=100
export KURRAL_DETERMINISM_THRESHOLD=0.90

# Redis (optional - for distributed caching)
export KURRAL_REDIS_URL=redis://localhost:6379/0

# Database (optional - for metadata storage)
export KURRAL_DATABASE_URL=postgresql://kurral:kurral@localhost:5432/kurral
```

---

## Complete Examples

### Example 1: Quick Start (Local Development)

```bash
# .env
KURRAL_STORAGE_BACKEND=local
KURRAL_AUTO_EXPORT=true
KURRAL_DEBUG=true
KURRAL_ENVIRONMENT=development
```

### Example 2: Production with Kurral Cloud API

```bash
# .env
KURRAL_STORAGE_BACKEND=api
KURRAL_API_KEY=kurral_live_abc123...
KURRAL_API_URL=https://api.kurral.io
KURRAL_ENVIRONMENT=production

# Optional: Enable LangSmith
KURRAL_LANGSMITH_ENABLED=true
KURRAL_LANGSMITH_API_KEY=lsv2_sk_...
KURRAL_LANGSMITH_PROJECT=production-agents

# General settings
KURRAL_AUTO_EXPORT=true
KURRAL_DEBUG=false
```

### Example 3: Custom R2 Bucket

```bash
# .env
KURRAL_CUSTOM_BUCKET_ENABLED=true
KURRAL_CUSTOM_BUCKET_NAME=acme-ai-artifacts
KURRAL_CUSTOM_BUCKET_ACCOUNT_ID=abc123...
KURRAL_CUSTOM_BUCKET_REGION=auto
KURRAL_CUSTOM_BUCKET_ACCESS_KEY_ID=key123...
KURRAL_CUSTOM_BUCKET_SECRET_ACCESS_KEY=secret123...

KURRAL_ENVIRONMENT=production
KURRAL_AUTO_EXPORT=true
```

### Example 4: Custom S3 Bucket (AWS)

```bash
# .env
KURRAL_CUSTOM_BUCKET_ENABLED=true
KURRAL_CUSTOM_BUCKET_NAME=my-company-artifacts
KURRAL_CUSTOM_BUCKET_REGION=us-west-2
KURRAL_CUSTOM_BUCKET_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
KURRAL_CUSTOM_BUCKET_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY

KURRAL_ENVIRONMENT=production
```

### Example 5: Development with Memory Storage

```bash
# .env
KURRAL_STORAGE_BACKEND=memory
KURRAL_MEMORY_MAX_ARTIFACTS=100
KURRAL_DEBUG=true
KURRAL_ENVIRONMENT=development
```

### Example 6: Testing in CI/CD

```bash
# .env
KURRAL_STORAGE_BACKEND=memory
KURRAL_MEMORY_MAX_ARTIFACTS=50
KURRAL_AUTO_EXPORT=false
KURRAL_DEBUG=false
```

---

## Interactive Configuration

Instead of manually setting environment variables, use the interactive configuration wizard:

```bash
# User-wide configuration
kurral config init

# Project-specific configuration
kurral config init --local
```

This will guide you through:
1. Choosing storage backend
2. Entering credentials
3. Configuring LangSmith (optional)
4. Setting debug mode

Configuration is saved to:
- **User-wide:** `~/.config/kurral/config.json`
- **Project-specific:** `./.kurral/config.json`

---

## Verify Your Configuration

```bash
# Show current configuration
kurral config show

# Check config file locations
kurral config path

# Test API connection (if using api mode)
python -c "
from kurral.storage.api import KurralAPIClient
import os

client = KurralAPIClient(
    api_key=os.getenv('KURRAL_API_KEY'),
    api_url=os.getenv('KURRAL_API_URL', 'https://api.kurral.io')
)
print('✅ API connection successful' if client.health_check() else '❌ API connection failed')
"
```

---

## Usage in Code

After configuring, use Kurral in your agent code:

```python
from kurral import trace_llm
from openai import OpenAI

client = OpenAI()

@trace_llm(semantic_bucket="customer_support", tenant_id="acme_prod")
def handle_query(query: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": query}],
        seed=12345,  # Important for determinism
    )
    return response.choices[0].message.content

# Artifacts are automatically saved/uploaded based on your configuration
result = handle_query("I need a refund")
```

---

## Priority Order

Configuration is loaded in this order (highest to lowest priority):

1. **Environment variables** (`KURRAL_*`)
2. **Project config file** (`./.kurral/config.json`)
3. **User config file** (`~/.config/kurral/config.json`)
4. **Legacy user config** (`~/.kurral/config.json`)
5. **Defaults**

---

## Troubleshooting

### API Mode Issues

```bash
# Check if API key is set
echo $KURRAL_API_KEY

# Verify API connection
curl -H "X-API-Key: $KURRAL_API_KEY" https://api.kurral.io/health

# Enable debug mode to see detailed logs
export KURRAL_DEBUG=true
```

### Custom Bucket Issues

```bash
# Test bucket access with AWS CLI
aws s3 ls s3://my-bucket --endpoint-url=$KURRAL_CUSTOM_BUCKET_ENDPOINT

# Or with boto3
python -c "
import boto3
s3 = boto3.client(
    's3',
    endpoint_url='$KURRAL_CUSTOM_BUCKET_ENDPOINT',
    aws_access_key_id='$KURRAL_CUSTOM_BUCKET_ACCESS_KEY_ID',
    aws_secret_access_key='$KURRAL_CUSTOM_BUCKET_SECRET_ACCESS_KEY',
)
print(s3.list_buckets())
"
```

### Memory Storage Issues

```bash
# Check current memory usage
kurral memory stats

# Clear memory if full
kurral memory clear
```

---

## Security Best Practices

1. **Never commit `.env` files** - Add to `.gitignore`
2. **Use API keys in production** - Avoid sharing R2 credentials
3. **Rotate keys regularly** - Especially for production environments
4. **Use least privilege** - Only grant necessary bucket permissions
5. **Use project-specific configs** - Avoid storing secrets in user-wide configs

---

## Need Help?

- Documentation: https://drive.google.com/file/d/1iixtUYjMsFKsTp8PUgdI_TNG3XrRxpED/view
- Run: `kurral --help`
- Config help: `kurral config --help`

