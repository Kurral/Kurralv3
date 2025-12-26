# Kurral Repository Documentation

## Table of Contents

1. [Introduction](#introduction)
2. [Repository Structure](#repository-structure)
3. [Architecture Overview](#architecture-overview)
4. [Core Modules](#core-modules)
5. [Configuration](#configuration)
6. [Usage Patterns](#usage-patterns)
7. [Storage Backends](#storage-backends)
8. [CLI Tools](#cli-tools)
9. [API Integration](#api-integration)
10. [Testing](#testing)
11. [Development](#development)
12. [Security](#security)

---

## Introduction

### What is Kurral?

**Kurral** is a deterministic testing and replay framework for AI agents. It provides a comprehensive solution for capturing, storing, and replaying AI agent executions, enabling regression testing, debugging, and quantifiable A/B performance comparison.

**Version**: 0.2.1  
**License**: Apache 2.0  
**Python**: 3.9+

### Key Features

- **Automatic Artifact Generation**: Captures complete execution traces with zero configuration
- **Intelligent Replay System**: Automatically detects changes and switches between A/B replay modes
- **Side Effect Protection**: Prevents dangerous operations during replay
- **Quantifiable Regression Detection**: Agent Regression Score (ARS) measures replay fidelity
- **Multiple Storage Backends**: Local filesystem, Cloudflare R2, and optional PostgreSQL metadata
- **Semantic Tool Matching**: 85% similarity threshold for intelligent tool call caching
- **Session-Based Artifacts**: Accumulates all interactions within a single execution

### Use Cases

- ✅ Regression testing: Verify code changes don't break existing behavior
- ✅ Model upgrades: Test if new models behave better than previous versions
- ✅ Prompt engineering: Compare different prompt variations quantitatively
- ✅ Debugging failures: Reproduce and analyze production issues locally
- ✅ CI/CD integration: Fail builds if ARS drops below threshold

---

## Repository Structure

### Root Directory

```
Kurralv3/
├── kurral/                    # Main package
│   ├── __init__.py            # Package exports
│   ├── agent_decorator.py     # @trace_agent decorator and trace_agent_invoke
│   ├── agent_replay.py        # Replay functionality
│   ├── ars_scorer.py          # Agent Regression Score calculation
│   ├── artifact_generator.py  # Artifact creation
│   ├── artifact_manager.py    # Storage management
│   ├── cache.py               # Caching backend
│   ├── config.py              # Configuration management
│   ├── decorator.py           # Legacy decorator (deprecated)
│   ├── langchain_integration.py # LangChain integration utilities
│   ├── replay_detector.py     # Change detection and replay type determination
│   ├── replay_executor.py     # A/B replay execution
│   ├── replay.py              # Replay module
│   ├── side_effect_config.py  # Side effect configuration management
│   ├── tool_stubber.py        # Semantic tool matching and stubbing
│   ├── cli/                   # Command-line interface
│   │   ├── __init__.py
│   │   ├── agent_replay.py
│   │   └── replay_cmd.py      # Main replay CLI command
│   ├── database/              # Database models and services
│   │   ├── __init__.py
│   │   ├── connection.py      # Database connection management
│   │   ├── metadata_service.py # Metadata service
│   │   └── models.py          # SQLAlchemy models
│   ├── models/                # Pydantic data models
│   │   ├── __init__.py
│   │   └── kurral.py          # Core artifact models
│   ├── storage/               # Storage backends
│   │   ├── __init__.py
│   │   ├── storage_backend.py # Abstract base class
│   │   ├── local_storage.py   # Local filesystem storage
│   │   ├── r2_storage.py      # Cloudflare R2 storage
│   │   └── README-API.md      # API service documentation
│   ├── tests/                 # Test suite
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_artifact_manager.py
│   │   └── test_replay_detector.py
│   ├── README.md              # Package README
│   └── REPLAY_GUIDE.md        # Replay guide
├── examples/                  # Example agents
│   ├── Kurral/               # Kurral-integrated examples
│   │   ├── level1agentK/
│   │   ├── level2agentK/
│   │   └── level3agentK/
│   └── original/             # Original examples (without Kurral)
│       ├── level1agent/
│       ├── level2agent/
│       └── level3agent/
├── dist/                     # Distribution files
├── kurral.egg-info/          # Package metadata
├── venv/                     # Virtual environment (gitignored)
├── .gitignore               # Git ignore rules
├── LICENSE                   # Apache 2.0 license
├── pyproject.toml            # Project configuration
├── README.md                 # Main README
└── ENV_EXAMPLE_TEMPLATE.md   # Environment variable template
```

### Key Directories

- **`kurral/`**: Main package containing all core functionality
- **`examples/`**: Example agents demonstrating Kurral integration
- **`kurral/cli/`**: Command-line interface for replay operations
- **`kurral/storage/`**: Storage backend implementations
- **`kurral/models/`**: Pydantic data models for artifacts
- **`kurral/database/`**: Optional PostgreSQL metadata storage

---

## Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent Execution                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  @trace_agent() decorator                             │  │
│  │  └─> trace_agent_invoke() wrapper                     │  │
│  │      ├─> ToolCallCaptureHandler (captures tool calls)│  │
│  │      ├─> extract_llm_config_from_langchain()         │  │
│  │      ├─> extract_resolved_prompt()                    │  │
│  │      └─> compute_graph_version()                      │  │
│  └──────────────────────────────────────────────────────┘  │
│                          │                                   │
│                          ▼                                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  ArtifactGenerator                                     │  │
│  │  └─> Generates KurralArtifact (JSON)                  │  │
│  └──────────────────────────────────────────────────────┘  │
│                          │                                   │
│                          ▼                                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  ArtifactManager                                       │  │
│  │  ├─> LocalStorage (default)                            │  │
│  │  ├─> R2Storage (if configured)                         │  │
│  │  └─> MetadataService (optional PostgreSQL)              │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    Replay System                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  ReplayDetector                                        │  │
│  │  ├─> calculate_determinism_score()                     │  │
│  │  ├─> detect_changes()                                 │  │
│  │  └─> determine_replay_type() → A or B                 │  │
│  └──────────────────────────────────────────────────────┘  │
│                          │                                   │
│                          ▼                                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  ReplayExecutor                                       │  │
│  │  ├─> A Replay: Return artifact outputs directly       │  │
│  │  └─> B Replay: Re-execute LLM with cached tools       │  │
│  │      └─> ToolStubber (semantic matching, 85% threshold)│ │
│  └──────────────────────────────────────────────────────┘  │
│                          │                                   │
│                          ▼                                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  ARSScorer                                            │  │
│  │  └─> calculate_ars() → Regression score (0.0-1.0)    │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Artifact Generation**:
   - Agent execution → `@trace_agent()` decorator
   - `trace_agent_invoke()` captures execution
   - Tool calls, LLM config, prompts extracted
   - `ArtifactGenerator` creates `KurralArtifact`
   - `ArtifactManager` saves to storage

2. **Replay Flow**:
   - Load artifact from storage
   - `ReplayDetector` analyzes changes
   - Determines A or B replay type
   - `ReplayExecutor` executes replay
   - `ARSScorer` calculates regression score
   - Save replay artifact

### A/B Replay System

**A Replay (Deterministic)**:
- **When**: Determinism score < 0.8 AND no changes detected
- **Behavior**: Returns artifact outputs directly
- **Cost**: Zero API costs
- **Use Case**: Regression testing, verifying identical behavior

**B Replay (Non-Deterministic)**:
- **When**: Determinism score >= 0.8 OR changes detected
- **Behavior**: Re-executes LLM with semantic tool call matching
- **Cost**: Reduced API costs via tool caching
- **Use Case**: Testing different models, A/B testing, prompt variations

### Side Effect Management

- **Auto-Generation**: Analyzes tool names/descriptions for keywords ("update", "send", "write")
- **Configuration**: YAML file in `side_effect/side_effects.yaml`
- **Protection**: Blocks side effect tools during replay (uses cached outputs)
- **Manual Review**: Requires `done: true` flag after configuration review

---

## Core Modules

### `agent_decorator.py`

**Purpose**: Provides decorator and wrapper functions for automatic artifact generation.

**Key Functions**:
- `@trace_agent()`: Decorator that wraps agent's main function
- `trace_agent_invoke()`: Wrapper for `agent_executor.invoke()` that captures traces

**Features**:
- Session-based artifact accumulation
- Automatic LLM config extraction
- Tool call capture via callbacks
- Prompt extraction and hashing
- Graph version computation

**Usage**:
```python
from kurral import trace_agent, trace_agent_invoke

@trace_agent()
def main():
    llm = ChatOpenAI(model="gpt-4")
    agent_executor = AgentExecutor(...)
    result = trace_agent_invoke(agent_executor, {"input": user_input}, llm=llm)
    return result
```

### `replay_detector.py`

**Purpose**: Detects changes between artifact and current execution context to determine replay type.

**Key Classes**:
- `ReplayDetector`: Main detection logic
- `ChangeDetectionResult`: Result of change detection
- `ReplayType`: Enum for A/B replay types

**Key Methods**:
- `calculate_determinism_score()`: Calculates determinism score (0.0-1.0)
- `determine_replay_type()`: Determines A or B replay based on score and changes
- `detect_changes()`: Compares artifact with current context

**Change Detection**:
- LLM config (model, provider, parameters)
- Prompt (template hash, final text hash)
- Graph version (tool schemas, graph structure)
- Inputs (hash comparison)

### `replay_executor.py`

**Purpose**: Executes A or B replay based on detection result.

**Key Classes**:
- `ReplayExecutor`: Main executor class

**Key Methods**:
- `execute_replay()`: Main entry point for replay execution
- `_execute_a_replay()`: A replay implementation
- `_execute_b_replay()`: B replay implementation

**Features**:
- Tool call caching via `ToolStubber`
- Semantic matching (85% threshold)
- Cache hit/miss tracking
- Replay artifact generation

### `artifact_manager.py`

**Purpose**: Manages storage and retrieval of kurral artifacts.

**Key Classes**:
- `ArtifactManager`: Main manager class

**Key Methods**:
- `save()`: Save artifact to storage
- `load()`: Load artifact by kurral_id
- `load_by_run_id()`: Load artifact by run_id
- `list_artifacts()`: List all artifacts
- `migrate_local_to_r2()`: Migrate local artifacts to R2

**Storage Backends**:
- `LocalStorage`: Local filesystem storage
- `R2Storage`: Cloudflare R2 storage
- `MetadataService`: Optional PostgreSQL metadata

### `tool_stubber.py`

**Purpose**: Semantic tool matching and stubbing for B replay.

**Key Functions**:
- `_calculate_semantic_similarity()`: Calculates similarity between texts
- `_compare_tool_inputs()`: Compares tool input dictionaries
- `match_tool_call()`: Matches tool calls with 85% similarity threshold

**Features**:
- Exact match (100% similarity)
- Semantic match (≥85% similarity)
- Levenshtein distance for typo handling
- Word-level similarity

### `ars_scorer.py`

**Purpose**: Calculates Agent Regression Score (ARS) for replay fidelity.

**Key Function**:
- `calculate_ars()`: Main ARS calculation function

**ARS Formula**:
```
ARS = (Output Similarity × 0.7) + (Tool Accuracy × 0.3)
```

**Components**:
- **Output Similarity**: Semantic/text similarity between outputs
- **Tool Accuracy**: Ratio of correctly matched tool calls

**Score Range**: 0.0 to 1.0 (1.0 = perfect match)

### `side_effect_config.py`

**Purpose**: Manages side effect configuration for agents.

**Key Classes**:
- `SideEffectConfig`: Configuration manager

**Key Methods**:
- `load()`: Load configuration from YAML
- `save()`: Save configuration to YAML
- `generate_config()`: Auto-generate configuration with suggestions
- `is_side_effect()`: Check if tool is a side effect
- `is_done()`: Check if configuration is complete

**Features**:
- Auto-discovery of tools
- Keyword-based suggestions ("update", "send", "write")
- Manual review requirement (`done: true`)

### `models/kurral.py`

**Purpose**: Core Pydantic models for artifact schema.

**Key Models**:
- `KurralArtifact`: Main artifact model
- `ModelConfig`: LLM configuration
- `ResolvedPrompt`: Prompt with hashing
- `ToolCall`: Tool call record
- `GraphVersion`: Graph/tool schema version
- `ReplayResult`: Replay execution result
- `LLMParameters`: Detailed LLM parameters
- `TokenUsage`: Token usage and cost metrics

**Features**:
- Automatic hash computation
- JSON serialization
- Validation via Pydantic
- Type safety

### `storage/` Module

**Purpose**: Storage backend implementations.

**Backends**:
- **`local_storage.py`**: Local filesystem storage (default)
- **`r2_storage.py`**: Cloudflare R2 storage (S3-compatible)
- **`storage_backend.py`**: Abstract base class

**Features**:
- Unified interface via `StorageBackend`
- Automatic backend selection based on config
- R2 migration support
- Path-based organization (tenant/agent/artifacts/year/month/)

### `database/` Module

**Purpose**: Optional PostgreSQL metadata storage.

**Components**:
- **`models.py`**: SQLAlchemy models for metadata
- **`connection.py`**: Database connection management
- **`metadata_service.py`**: Metadata service

**Features**:
- Fast querying and filtering
- Indexed searches
- Aggregations and statistics
- Lightweight metadata (full artifacts in R2/local)

### `cli/replay_cmd.py`

**Purpose**: Command-line interface for replay operations.

**Key Features**:
- Replay by file path, run_id, or latest artifact
- Automatic A/B replay detection
- Change detection and reporting
- ARS score calculation
- Verbose and debug modes

**Usage**:
```bash
# Replay by file
kurral replay artifact.kurral

# Replay by run_id
kurral replay --run-id my_run_123

# Replay latest
kurral replay --latest

# With debug output
kurral replay artifact.kurral --debug --verbose
```

---

## Configuration

### Environment Variables

#### Storage Configuration

```bash
# Storage backend type (local or r2)
STORAGE_BACKEND=local

# Cloudflare R2 Configuration
R2_ACCOUNT_ID=your-account-id
R2_ACCESS_KEY_ID=your-access-key
R2_SECRET_ACCESS_KEY=your-secret-key
R2_BUCKET_NAME=your-bucket-name

# Local storage path
LOCAL_STORAGE_PATH=./artifacts

# Tenant ID
TENANT_ID=default

# Optional: PostgreSQL metadata
DATABASE_URL=postgresql://user:password@localhost:5432/kurral_db
```

#### LLM API Keys

```bash
# OpenAI
OPENAI_API_KEY=sk-...

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Google
GEMINI_API_KEY=...

# Groq
GROQ_API_KEY=...

# Tavily
TAVILY_API_KEY=...
```

### Storage Configuration

**Local Storage (Default)**:
- No configuration required
- Artifacts stored in `./artifacts/` directory
- Organized by date: `artifacts/YYYY/MM/{kurral_id}.kurral`

**R2 Storage**:
- Configure via environment variables
- Automatic migration from local to R2
- Path format: `{tenant_id}/{agent_name}/artifacts/YYYY/MM/{kurral_id}.kurral`

**PostgreSQL Metadata (Optional)**:
- Stores lightweight metadata for fast querying
- Full artifacts remain in R2 or local storage
- Enables advanced filtering and analytics

### Side Effect Configuration

**Location**: `{agent_dir}/side_effect/side_effects.yaml`

**Format**:
```yaml
tools:
  send_email: false    # Side effect - blocked during replay
  tavily_search: true   # Safe - allowed during replay
  write_file: false     # Side effect - blocked
done: false             # Must be set to true after review
```

**Auto-Generation**:
- Generated on first replay
- Analyzes tool names, descriptions, docstrings
- Suggests based on keywords ("update", "send", "write")
- Requires manual review before replay

### LLM Configuration

LLM configuration is automatically extracted from LangChain agents:
- Model name and version
- Provider (OpenAI, Anthropic, etc.)
- Parameters (temperature, seed, top_p, etc.)
- Stop sequences
- Additional provider-specific params

---

## Usage Patterns

### Basic Integration

```python
from langchain.agents import AgentExecutor, create_react_agent
from langchain_openai import ChatOpenAI
from kurral import trace_agent, trace_agent_invoke

@trace_agent()
def main():
    # Setup agent
    llm = ChatOpenAI(model="gpt-4", temperature=0)
    tools = create_tools()
    agent = create_react_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools)
    
    # Execute with tracing
    user_input = input("You: ")
    result = trace_agent_invoke(
        agent_executor, 
        {"input": user_input}, 
        llm=llm
    )
    print(f"Agent: {result['output']}")
    return result

if __name__ == "__main__":
    main()
```

### Multiple Interactions

```python
@trace_agent()
def main():
    # ... setup agent ...
    
    while True:
        user_input = input("You: ")
        if user_input.lower() == 'exit':
            break
        
        result = trace_agent_invoke(
            agent_executor, 
            {"input": user_input}, 
            llm=llm
        )
        print(f"Agent: {result['output']}")
    
    # All interactions saved in one artifact when main() exits
```

### Replay Workflow

```python
from kurral.artifact_manager import ArtifactManager
from kurral.replay_detector import ReplayDetector
from kurral.replay_executor import ReplayExecutor

# Load artifact
manager = ArtifactManager(storage_path="./artifacts")
artifact = manager.load_by_run_id("my_run_123")

# Detect changes
detector = ReplayDetector()
detection_result = detector.determine_replay_type(
    artifact=artifact,
    current_llm_config=current_llm_config,
    current_prompt=current_prompt,
    current_graph_version=current_graph_version,
)

# Execute replay
executor = ReplayExecutor()
result = await executor.execute_replay(
    artifact=artifact,
    detection_result=detection_result,
    llm_client=llm_client,  # Required for B replay
)

# Calculate ARS
from kurral.ars_scorer import calculate_ars
ars = calculate_ars(
    original_outputs=artifact.outputs,
    replayed_outputs=result.outputs,
    original_tool_calls=artifact.tool_calls,
    replayed_tool_calls=result.tool_calls,
    new_tool_calls=result.new_tool_calls,
    unused_tool_calls=result.unused_tool_calls,
)
print(f"ARS Score: {ars['ars_score']}")
```

### Storage Options

**Local Storage**:
```python
from kurral.artifact_manager import ArtifactManager

manager = ArtifactManager(storage_path="./artifacts")
artifact = manager.load(kurral_id)
```

**R2 Storage**:
```python
import os
from kurral.artifact_manager import ArtifactManager

# Set environment variables
os.environ["R2_ACCOUNT_ID"] = "your-account-id"
os.environ["R2_ACCESS_KEY_ID"] = "your-access-key"
os.environ["R2_SECRET_ACCESS_KEY"] = "your-secret-key"
os.environ["R2_BUCKET_NAME"] = "your-bucket-name"

manager = ArtifactManager(storage_path="./artifacts")
# Automatically uses R2 if credentials are configured
```

---

## Storage Backends

### Local Storage

**Implementation**: `kurral/storage/local_storage.py`

**Features**:
- Default storage backend
- No configuration required
- Organized by date: `artifacts/YYYY/MM/{kurral_id}.kurral`
- Fast local access

**Path Structure**:
```
artifacts/
├── 2024/
│   ├── 01/
│   │   ├── {kurral_id_1}.kurral
│   │   └── {kurral_id_2}.kurral
│   └── 02/
│       └── {kurral_id_3}.kurral
└── index.json
```

### Cloudflare R2 Storage

**Implementation**: `kurral/storage/r2_storage.py`

**Features**:
- S3-compatible API
- Scalable object storage
- Automatic migration from local
- Path-based organization

**Path Structure**:
```
{tenant_id}/{agent_name}/artifacts/YYYY/MM/{kurral_id}.kurral
```

**Configuration**:
```bash
export R2_ACCOUNT_ID=your-account-id
export R2_ACCESS_KEY_ID=your-access-key
export R2_SECRET_ACCESS_KEY=your-secret-key
export R2_BUCKET_NAME=your-bucket-name
```

### PostgreSQL Metadata (Optional)

**Implementation**: `kurral/database/metadata_service.py`

**Features**:
- Fast querying and filtering
- Indexed searches
- Aggregations and statistics
- Lightweight metadata only (full artifacts in R2/local)

**Schema**: See `kurral/database/models.py` for `ArtifactMetadata` model

**Configuration**:
```bash
export DATABASE_URL=postgresql://user:password@localhost:5432/kurral_db
```

---

## CLI Tools

### Replay Command

**Module**: `kurral/cli/replay_cmd.py`

**Usage**:
```bash
# Replay by file path
kurral replay artifact.kurral

# Replay by run_id
kurral replay --run-id my_run_123

# Replay latest artifact
kurral replay --latest

# With debug output
kurral replay artifact.kurral --debug --verbose

# Show diff
kurral replay artifact.kurral --diff

# Specify current model for change detection
kurral replay artifact.kurral --current-model gpt-4-turbo
```

**Options**:
- `--run-id`: Replay by run_id
- `--latest`: Replay latest artifact
- `--storage-path`: Custom storage path
- `--llm-client`: LLM client type (for B replay)
- `--diff`: Show diff between original and replay
- `--debug`: Enable debug mode
- `--verbose`: Verbose output
- `--current-model`: Current model name
- `--current-temperature`: Current temperature

**Output**:
- Replay type (A or B)
- Determinism score
- Changes detected
- ARS score
- Cache hits/misses
- Replay artifact path

---

## API Integration

### Kurral API Service

**Location**: `kurral/storage/README-API.md`

**Purpose**: Separate FastAPI service for centralized artifact management.

**Features**:
- API key authentication
- Artifact upload/download
- Advanced querying and filtering
- Analytics and statistics
- Multi-user support
- Web-based dashboard

**Note**: The Kurral Python library works standalone with R2 or local storage. The API is an optional centralized service for teams.

### Integration Patterns

**Direct R2 Access**:
- Library and API can share the same R2 bucket
- Both use S3-compatible API
- No API calls required for storage

**PostgreSQL Metadata**:
- Both library and API can use the same database
- Fast querying via metadata service
- Full artifacts remain in R2

**API Endpoints** (from API service):
- `POST /api/v1/artifacts/upload` - Upload artifact
- `GET /api/v1/artifacts` - List artifacts
- `GET /api/v1/artifacts/{kurral_id}` - Get artifact
- `GET /api/v1/stats` - Get statistics

---

## Testing

### Test Structure

**Location**: `kurral/tests/`

**Test Files**:
- `test_artifact_manager.py`: Artifact storage tests
- `test_replay_detector.py`: Change detection tests
- `conftest.py`: Test fixtures

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=kurral --cov-report=term-missing

# Run specific test file
pytest kurral/tests/test_replay_detector.py

# Run with verbose output
pytest -v
```

### Test Coverage

Tests cover:
- Artifact generation and storage
- Change detection logic
- Replay type determination
- Tool call matching
- ARS calculation

---

## Development

### Setup Instructions

**1. Clone Repository**:
```bash
git clone https://github.com/kurral/kurralv3.git
cd kurralv3
```

**2. Create Virtual Environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

**3. Install Dependencies**:
```bash
# Install package in development mode
pip install -e .

# Or install with optional dependencies
pip install -e ".[all]"

# Install development dependencies
pip install -e ".[dev]"
```

**4. Configure Environment**:
```bash
# Copy environment template
cp ENV_EXAMPLE_TEMPLATE.md .env

# Edit .env with your configuration
```

### Dependencies

**Core Dependencies** (from `pyproject.toml`):
- `pydantic>=2.5.0`
- `click>=8.1.7`
- `rich>=13.7.0`
- `pyyaml>=6.0`

**Optional Dependencies**:
- `langchain>=0.1.0` (for LangChain integration)
- `openai>=1.0.0` (for OpenAI LLMs)
- `anthropic>=0.18.0` (for Anthropic LLMs)
- `groq>=0.4.0` (for Groq LLMs)
- `google-generativeai>=0.3.0` (for Google LLMs)
- `boto3` (for R2 storage)

**Development Dependencies**:
- `pytest>=7.4.3`
- `pytest-asyncio>=0.23.0`
- `pytest-cov>=4.1.0`
- `black>=23.12.0`
- `ruff>=0.1.9`
- `mypy>=1.8.0`

### Code Quality

**Formatting**:
```bash
black kurral/
```

**Linting**:
```bash
ruff check kurral/
```

**Type Checking**:
```bash
mypy kurral/
```

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

---

## Security

### Recent Updates

**`.gitignore` Update** (2024):
- Added `kurral-api-main/` to `.gitignore` to prevent accidental commits
- Ensures sensitive API code is not pushed to repository

### API Key Management

**Best Practices**:
- ✅ Always use environment variables for API keys
- ✅ Never hardcode API keys in source files
- ✅ Use `.env` files (already in `.gitignore`)
- ✅ Rotate keys if exposed
- ✅ Use secret management tools in production

**Current Status**:
- All code uses `os.getenv()` for API keys (safe)
- `.env` files are gitignored
- No hardcoded secrets in current codebase

### Security Incident (Historical)

**Issue**: API keys were leaked in git commit history when repository was made public.

**Remediation Required**:
1. Clean git history using `git-filter-repo` or `git filter-branch`
2. Rotate all exposed API keys immediately
3. Force-push cleaned history to remote
4. Notify collaborators to re-clone repository

**Prevention**:
- `.gitignore` properly configured
- Pre-commit hooks recommended
- Secret scanning tools recommended
- Code review for sensitive data

### Configuration Security

**Environment Variables**:
- Store in `.env` files (gitignored)
- Never commit `.env` files
- Use different keys for dev/staging/production

**R2 Credentials**:
- Store in environment variables
- Use IAM roles when possible
- Rotate keys regularly

**Database Credentials**:
- Use connection strings in environment variables
- Enable SSL/TLS for database connections
- Use read-only users for queries when possible

---

## Additional Resources

### Documentation Files

- **`README.md`**: Main project README with quick start
- **`kurral/README.md`**: Package-specific documentation
- **`kurral/REPLAY_GUIDE.md`**: Detailed replay guide
- **`kurral/storage/README-API.md`**: API service documentation
- **`ENV_EXAMPLE_TEMPLATE.md`**: Environment variable template

### Community

- **GitHub**: [github.com/kurral/kurralv3](https://github.com/kurral/kurralv3)
- **Discord**: [discord.gg/pan6GRRV](https://discord.gg/pan6GRRV)
- **Email**: team@kurral.com

### License

Apache 2.0 - See `LICENSE` file for details.

---

**Last Updated**: 2025  
**Version**: 0.2.1  
**Maintainer**: Kurral Team

