# Changelog

All notable changes to Kurral will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2024-11-21

### Fixed
- Fixed import error in `kurral.cli.ab_test` module (`get_storage` not found)
- Removed unused import that caused CLI to fail on startup

## [0.1.0] - 2024-11-20

### Added

#### Core Features
- **Deterministic LLM Tracing**: Capture complete agent execution with `@trace_llm` decorator
- **Replay Engine**: Deterministically replay captured traces with stubbed tool calls
- **A/B Testing**: Compare agent versions (model migration, prompt changes, config tweaks)
- **ARS (Agent Regression Score)**: Quantify behavioral differences between versions
- **Semantic Buckets**: Organize traces by business logic (e.g., `customer_support`, `refund_flow`)
- **Stream Capture**: Record streaming LLM outputs with timing information

#### CLI Commands
- `kurral auth register` - Register and get API key automatically
- `kurral auth login` - Login to existing account
- `kurral auth status` - Show authentication status
- `kurral config init` - Interactive configuration setup
- `kurral config show` - Display current configuration
- `kurral ab model-migration` - Test model migrations
- `kurral ab prompt-test` - Test prompt changes
- `kurral ab compare` - Compare custom configurations
- `kurral export` - Export traces from LangSmith
- `kurral replay` - Replay artifacts with diff comparison
- `kurral backtest` - Run regression tests on artifact buckets
- `kurral buckets list` - List semantic buckets
- `kurral memory` - Manage in-memory artifact storage

#### Storage Backends
- **Local**: Save artifacts to disk (`./artifacts/`)
- **Memory**: Store artifacts in RAM (zero I/O overhead)
- **API**: Upload to Kurral Cloud (managed service)
- **Custom Bucket**: Use your own R2/S3 bucket
- **Legacy R2**: Shared Kurral R2 bucket (deprecated)

#### Integrations
- **LangSmith**: Import existing traces from LangSmith
- **LangGraph**: Capture LangGraph execution graphs
- **OpenAI**: Full support for OpenAI models
- **Anthropic**: Full support for Claude models

#### Data Capture
- Complete LLM configuration (model, temperature, seed, etc.)
- Resolved prompts with variable substitution
- Tool calls with inputs, outputs, and timing
- Execution graph hashing for version tracking
- Environment capture (timestamp, timezone, env vars)
- Token usage and cost tracking
- Error forensics with full stack traces

#### Determinism Analysis
- Determinism scoring (0.0-1.0) - for analytics only
- Replay level classification (A/B/C) - **metadata only, not used for replay decisions**
- Missing field detection
- Reproducibility warnings

#### Documentation
- Comprehensive README with examples
- Quick start guide with authentication
- Environment configuration guide
- Complete A/B testing documentation
- Publishing guide for PyPI
- Example scripts for common use cases

#### Authentication & Registration
- `kurral auth register` - One-command registration with auto API key generation
- `kurral auth login` - Login to existing account
- `kurral auth status` - Show authentication status
- Automatic config save to `~/.kurral/config.json`

### Changed
- **ABC Classification**: Now **metadata-only** (not used for replay decisions or gating)
- **Focus on A/B Testing**: Primary use case is version comparison for deployment decisions
- All artifacts are replayed the same way regardless of ABC level

### Technical Details
- Python 3.11+ required
- Full type hints with Pydantic v2
- Rich CLI with beautiful terminal output
- Async/await support for concurrent operations
- Comprehensive test coverage

### Notes
This is the initial public release of Kurral. The API is considered alpha and may change in future versions. Please report any issues on GitHub.

---

## [Unreleased]

### Planned Features
- Statistical significance testing for A/B tests
- Web UI for artifact browsing and analysis
- CI/CD integration examples
- Multi-language support (TypeScript, Go)
- Enterprise SSO integration
- Advanced analytics dashboard

---

[0.1.0]: https://github.com/kurral-dev/kurral-cli/releases/tag/v0.1.0

