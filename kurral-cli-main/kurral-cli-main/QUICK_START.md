# Kurral Quick Start Guide

## Get Started in 2 Minutes

### Step 1: Install

```bash
pip install kurral
```

### Step 2: Register (One Command!)

```bash
kurral auth register
```

This automatically:
- Creates your account
- Logs you in
- Generates API key
- Saves config to `~/.config/kurral/config.json`

Done! You're ready to trace. 🚀

---

## 3 Ways to Store Artifacts

### 1. Kurral Cloud API (Easiest) ⭐

**Best for:** Production, teams, multi-tenant setups

**Setup:**
```bash
# Register automatically
kurral auth register

# Or configure manually
export KURRAL_STORAGE_BACKEND=api
export KURRAL_API_KEY=kurral_live_abc123...
export KURRAL_API_URL=https://api.kurral.io
```

**Usage:**
```python
# Your code (automatically uploads to Kurral Cloud)
python my_agent.py
```

**Flow:** Your Agent → HTTP POST → Kurral API → R2 Bucket

---

### 2. Your Own Bucket (Full Control) 🪣

**Best for:** Companies with existing infrastructure, compliance requirements

**Cloudflare R2:**
```bash
export KURRAL_CUSTOM_BUCKET_ENABLED=true
export KURRAL_CUSTOM_BUCKET_NAME=my-bucket
export KURRAL_CUSTOM_BUCKET_ACCOUNT_ID=abc123...
export KURRAL_CUSTOM_BUCKET_REGION=auto
export KURRAL_CUSTOM_BUCKET_ACCESS_KEY_ID=key...
export KURRAL_CUSTOM_BUCKET_SECRET_ACCESS_KEY=secret...
```

**AWS S3:**
```bash
export KURRAL_CUSTOM_BUCKET_ENABLED=true
export KURRAL_CUSTOM_BUCKET_NAME=my-s3-bucket
export KURRAL_CUSTOM_BUCKET_REGION=us-west-2
export KURRAL_CUSTOM_BUCKET_ACCESS_KEY_ID=AKIA...
export KURRAL_CUSTOM_BUCKET_SECRET_ACCESS_KEY=wJal...
```

**Flow:** Your Agent → boto3 SDK → Your Bucket (direct)

---

### 3. Local Storage (Development) 💾

**Best for:** Development, testing, offline work

```bash
export KURRAL_STORAGE_BACKEND=local
export KURRAL_LOCAL_STORAGE_PATH=./artifacts
```

---

## Complete Examples

### Example 1: Production with Kurral Cloud

```bash
# .env
KURRAL_STORAGE_BACKEND=api
KURRAL_API_KEY=kurral_live_xyz789...
KURRAL_ENVIRONMENT=production
KURRAL_AUTO_EXPORT=true
```

```python
from kurral import trace_llm
from openai import OpenAI

client = OpenAI()

@trace_llm(semantic_bucket="support", tenant_id="acme")
def handle_support(query: str):
    return client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": query}],
        seed=42
    ).choices[0].message.content

# Automatically uploads to Kurral Cloud ✅
result = handle_support("Help with refund")
```

---

### Example 2: Your Own R2 Bucket

```bash
# .env
KURRAL_CUSTOM_BUCKET_ENABLED=true
KURRAL_CUSTOM_BUCKET_NAME=acme-ai-traces
KURRAL_CUSTOM_BUCKET_ACCOUNT_ID=cf123abc...
KURRAL_CUSTOM_BUCKET_REGION=auto
KURRAL_CUSTOM_BUCKET_ACCESS_KEY_ID=r2_key_...
KURRAL_CUSTOM_BUCKET_SECRET_ACCESS_KEY=r2_secret_...
KURRAL_ENVIRONMENT=production
```

```python
from kurral import trace_llm

@trace_llm(semantic_bucket="data_ops", tenant_id="acme")
def process_data(data):
    # Your agent code
    return result

# Automatically uploads to YOUR R2 bucket ✅
process_data({"records": 100})
```

---

### Example 3: Local Development

```bash
# .env
KURRAL_STORAGE_BACKEND=local
KURRAL_DEBUG=true
KURRAL_ENVIRONMENT=development
```

```python
from kurral import trace_llm

@trace_llm(semantic_bucket="test", tenant_id="dev")
def my_agent(query):
    return f"Response to: {query}"

# Saves to ./artifacts/ ✅
my_agent("test query")
```

---

## Interactive Setup

Instead of manual configuration, use the wizard:

```bash
kurral config init
```

Choose:
1. Storage backend (local, memory, api, custom-bucket, r2)
2. Enter credentials
3. Configure LangSmith (optional)
4. Set debug mode

---

## Verify Setup

```bash
# Show current config
kurral config show

# Test your agent
python my_agent.py

# List artifacts
kurral buckets list

# Replay a trace
kurral replay artifacts/*.kurral
```

---

## Key Differences

| Feature | Kurral Cloud API | Custom Bucket | Local |
|---------|-----------------|---------------|-------|
| Setup Complexity | ⭐ Easy | ⭐⭐ Medium | ⭐⭐⭐ Easiest |
| Credentials Needed | API key only | Bucket + credentials | None |
| Multi-tenant | ✅ Yes | Manual | Manual |
| Metadata Queries | ✅ Fast (PostgreSQL) | No | No |
| Cost Tracking | ✅ Built-in | Manual | N/A |
| Offline Support | ❌ No | ❌ No | ✅ Yes |
| Data Control | Shared | ✅ Full control | ✅ Full control |

---

## A/B Testing Your Agent

**Test changes before deploying to production:**

```bash
# Test model migration
kurral ab model-migration \
  --baseline ./prod-traces/ \
  --model-a gpt-4 \
  --model-b gpt-4-turbo \
  --threshold 0.90

# Test prompt changes
kurral ab prompt-test \
  --baseline ./traces/ \
  --prompt-a current.txt \
  --prompt-b new.txt
```

**In Python:**

```python
from kurral.core.ab_test import ComparativeABTest

engine = ComparativeABTest()

# Test model migration
result = await engine.test_model_migration(
    baseline_artifacts=prod_traces,
    from_model="gpt-4",
    to_model="gpt-4-turbo",
    threshold=0.90
)

if result.recommendation == "deploy":
    print(f"✅ Safe to migrate (ARS: {result.b_mean_ars:.2f})")
```

---

## Next Steps

1. **Register & configure** (`kurral auth register`)
2. **Add decorator to your agent** (`@trace_llm`)
3. **Run and capture traces** (`python my_agent.py`)
4. **A/B test changes** (`kurral ab model-migration ...`)
5. **Query artifacts** (`kurral buckets list`)
6. **Replay traces** (`kurral replay artifact.kurral`)

---

## CLI Commands

```bash
# Authentication
kurral auth register
kurral auth status

# Configuration
kurral config init
kurral config show

# A/B Testing
kurral ab model-migration --model-a gpt-4 --model-b gpt-4-turbo
kurral ab prompt-test --prompt-a old.txt --prompt-b new.txt

# Replay
kurral replay artifact.kurral --diff

# Artifacts
kurral buckets list
```

---

## Need Help?

- README: `README.md`
- Full docs: `ENV_CONFIG.md`
- CLI help: `kurral --help`
- Publishing: `PUBLISHING.md`

