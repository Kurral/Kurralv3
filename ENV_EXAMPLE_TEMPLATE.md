# .env.example Files Template

Since .env files are in .gitignore, you need to manually create `.env.example` files in each agent directory. Here's the template:

## For level1agentK/.env.example

```env
# ============================================
# LLM API Keys (at least one required)
# ============================================
# OpenAI API Key
OPENAI_API_KEY=

# Google Gemini API Key
GEMINI_API_KEY=

# Groq API Key
GROQ_API_KEY=

# ============================================
# Cloudflare R2 Storage (optional)
# ============================================
# If provided, artifacts will be stored in R2 bucket
# Leave empty to use local storage only
R2_ACCOUNT_ID=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET_NAME=

# ============================================
# PostgreSQL/Supabase (optional - for metadata storage)
# ============================================
# PostgreSQL connection string (from Supabase or other PostgreSQL provider)
# Format: postgresql://user:password@host:port/database
DATABASE_URL=

# ============================================
# Storage Configuration
# ============================================
# Storage backend: local or r2
# - local: Store only locally (default when R2 not configured)
# - r2: Store only in R2 (no local backup) - automatically used when R2 credentials provided
# Note: When R2 credentials are provided, R2-only mode is used automatically
STORAGE_BACKEND=local

# Tenant ID for organizing artifacts (default: "default")
TENANT_ID=default

# Local storage path (optional, defaults to ./artifacts)
# LOCAL_STORAGE_PATH=./artifacts
```

## For level2agentK/.env.example

Same as above, plus:

```env
# ============================================
# Tool API Keys
# ============================================
# Tavily API Key for internet search
TAVILY_API_KEY=
```

## For level3agentK/.env.example

Same as level2agentK, plus:

```env
# Email Configuration (for send_email tool)
# SMTP_SERVER=
# SMTP_PORT=
# SMTP_USERNAME=
# SMTP_PASSWORD=
# FROM_EMAIL=
```

## How to Use

1. Copy the template above to create `.env.example` files in each agent directory
2. Create actual `.env` files (copied from .env.example) and fill in your credentials
3. The system will automatically:
   - Use R2-only storage if R2 credentials are provided (no local backup)
   - Migrate existing local artifacts to R2 on first run after adding R2 config
   - Use local storage only if R2 credentials are missing
   - Fetch artifacts from R2 during replay if R2 is configured
   - Organize artifacts by agent name in R2 (each agent gets its own folder)

## SECRET_KEY

**Note**: SECRET_KEY is NOT needed for agent usage. It's only used by the kurral-api backend for JWT token signing. Agents don't need it.

