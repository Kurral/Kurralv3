# MCP Proxy: Merge to Master Checklist

This document provides a comprehensive checklist and review guide for merging the `mcp-proxy` branch to `master`.

---

## 📋 Pre-Merge Checklist

### ✅ Code Quality

- [x] All tests passing (unit + integration)
- [x] No breaking changes to existing Kurral functionality
- [x] Optional dependencies (MCP features don't affect core)
- [x] Graceful degradation (CLI shows helpful errors if deps missing)
- [x] Type hints throughout (Pydantic V2 models)
- [x] Error handling with try/except and logging
- [x] Async/await for non-blocking operations

### ✅ Testing

- [x] **Unit Tests**: 5/5 passing (`test_sse_manual.py`)
- [x] **Integration Tests**: ALL passing (`run_integration_test.sh`)
- [x] **SSE Streaming**: Verified with real SSE mock server
- [x] **Performance Metrics**: Captured and validated
- [x] **Record Mode**: Captures all calls with events
- [x] **Replay Mode**: Returns identical responses
- [x] **Export**: Generates valid `.kurral` artifacts

### ✅ Documentation

- [x] **MCP_PROXY_README.md**: Comprehensive user guide
- [x] **kurral/mcp/README.md**: Technical documentation
- [x] **kurral/mcp/SSE_IMPLEMENTATION.md**: SSE architecture guide
- [x] **examples/mcp_test/README.md**: Integration test docs
- [x] **CLI help text**: `kurral mcp --help` works

### ✅ Backward Compatibility

- [x] Schema additions are backward compatible
- [x] New fields have defaults (`was_sse=False`, `events=[]`)
- [x] Old artifacts still load without errors
- [x] Core Kurral functionality untouched
- [x] No changes to existing dependencies

---

## 📝 Files to Update on Merge

### 1. Root README.md

Add MCP Proxy section after "When to Use Kurral":

```markdown
## MCP Proxy (NEW!) 🌊

Capture and replay MCP tool calls with full SSE streaming support.

Kurral now includes an HTTP/SSE proxy for the [Model Context Protocol](https://modelcontextprotocol.io), providing complete observability into MCP tool usage.

### Quick Start

\`\`\`bash
# Install with MCP support
pip install kurral[mcp]

# Start recording
kurral mcp start --mode record

# Export captured calls
kurral mcp export -o session.json

# Replay from cache
kurral mcp start --mode replay --artifact session.json
\`\`\`

### Key Features
- ✅ Record all MCP tool calls to `.kurral` artifacts
- ✅ Replay cached responses for deterministic testing
- ✅ Full SSE event-by-event capture
- ✅ Performance metrics (duration, event rates)
- ✅ Multi-server routing

**[📖 Full MCP Proxy Documentation →](MCP_PROXY_README.md)**

---
```

### 2. Table of Contents

Update TOC to include:
```markdown
- [MCP Proxy (NEW!)](#mcp-proxy-new-)
```

### 3. CHANGELOG.md (Create if doesn't exist)

```markdown
# Changelog

## [0.3.0] - 2025-12-15

### Added
- **MCP Proxy**: HTTP/SSE proxy for Model Context Protocol
  - Record mode: Capture all MCP tool calls
  - Replay mode: Deterministic testing with cached responses
  - SSE streaming: Full event-by-event capture and replay
  - Performance metrics: Duration, event rates, time-to-first-event
  - Multi-server routing: Route tools to different servers
  - See [MCP_PROXY_README.md](MCP_PROXY_README.md) for details

### Enhanced
- Schema expansion: Added SSE events, performance metrics, server attribution
- Artifact format now includes `mcp_session_id`, `mcp_servers_used`, `mcp_tool_calls`

## [0.2.2] - Previous release
...
```

---

## 📦 What's Being Merged

### New Files (26 files, ~3,700 lines)

```
kurral/mcp/
├── __init__.py                   # Module exports
├── models.py                     # Pydantic models (JSONRPCRequest, MCPEvent, PerformanceMetrics)
├── config.py                     # YAML configuration with env var substitution
├── capture.py                    # Record mode engine with SSE event capture
├── replay.py                     # Replay mode engine with SSE reconstruction
├── router.py                     # Multi-server routing with tool discovery
├── proxy.py                      # FastAPI proxy server (main entry point)
├── README.md                     # Technical documentation
└── SSE_IMPLEMENTATION.md         # SSE architecture deep dive

kurral/cli/
└── mcp_cmd.py                    # CLI commands (init, start, export)

kurral/tests/mcp/
├── __init__.py
├── test_models.py                # Model validation tests
├── test_config.py                # Config loading tests
└── test_sse.py                   # SSE integration tests (pytest)

examples/mcp_test/
├── README.md                     # Integration test documentation
├── kurral-mcp.yaml              # Sample configuration
├── mock_mcp_server.py           # Mock MCP server with SSE streaming
├── test_client.py               # Test client for validation
└── run_integration_test.sh      # Full integration test script

Documentation:
├── MCP_PROXY_README.md          # User guide (comprehensive)
├── MERGE_TO_MAIN.md             # This file
└── test_sse_manual.py           # Manual test runner (no pytest dependency)
```

### Modified Files (3 files)

```
pyproject.toml                   # Added [project.optional-dependencies.mcp]
kurral/__init__.py               # Conditional MCP exports
kurral/cli/__init__.py           # Conditional MCP command registration
```

### Schema Extensions

**New top-level artifact fields:**
```json
{
  "mcp_session_id": "uuid",
  "mcp_servers_used": ["server1", "server2"],
  "mcp_tool_calls": [...]
}
```

**New per-call fields:**
```json
{
  "server": "mock_server",
  "was_sse": true,
  "events": [...],
  "metrics": {
    "total_duration_ms": 2300,
    "time_to_first_event_ms": 100,
    "event_count": 5,
    "events_per_second": 2.17
  }
}
```

---

## 🚀 Merge Procedure

### Step 1: Final Verification

```bash
# Switch to mcp-proxy branch
cd /tmp/kurralv3
git checkout mcp-proxy

# Run all tests
python test_sse_manual.py
./examples/mcp_test/run_integration_test.sh

# Verify clean state
git status
```

### Step 2: Update README on Branch

```bash
# Read current master README
git show master:README.md > /tmp/master_readme.md

# Edit README.md to add MCP section (see above)
# Position: After "When to Use Kurral" section

# Commit updated README
git add README.md
git commit -m "Update README with MCP Proxy section for merge"
```

### Step 3: Merge to Master

```bash
# Switch to master
git checkout master

# Merge with no-ff to preserve history
git merge mcp-proxy --no-ff -m "Merge MCP Proxy: HTTP/SSE proxy with full capture and replay

- Add MCP (Model Context Protocol) HTTP/SSE proxy
- Record mode: Capture all tool calls with SSE events
- Replay mode: Deterministic testing from cached responses
- Performance metrics: Duration, event rates, TTFE
- Multi-server routing with semantic matching
- Optional dependencies (pip install kurral[mcp])
- Comprehensive documentation and integration tests
- Backward compatible schema extensions

See MCP_PROXY_README.md for full documentation."
```

### Step 4: Verify Merge

```bash
# Check files present
ls -la kurral/mcp/
ls -la examples/mcp_test/

# Verify optional deps
grep -A 10 "optional-dependencies" pyproject.toml

# Test installation
pip install -e ".[mcp]"
kurral mcp --help
```

### Step 5: Push to Remote

```bash
# Push master
git push origin master

# Push tags (if creating release)
git tag -a v0.3.0 -m "Release v0.3.0: Add MCP Proxy"
git push origin v0.3.0
```

---

## 🧪 Post-Merge Validation

### Test Core Kurral (Without MCP)

```bash
# Clean install without MCP deps
pip uninstall kurral -y
pip install kurral

# Verify core works
kurral --version
kurral --help

# Verify MCP gives helpful error
kurral mcp --help
# Expected: "MCP dependencies not installed. Run: pip install kurral[mcp]"
```

### Test MCP Features

```bash
# Install with MCP
pip install "kurral[mcp]"

# Verify CLI
kurral mcp init
kurral mcp --help

# Run integration test
cd examples/mcp_test
./run_integration_test.sh
# Expected: ✅ ALL INTEGRATION TESTS PASSED!
```

---

## 📊 Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking core Kurral | Very Low | High | ✅ Optional deps, no core changes |
| Performance regression | Very Low | Medium | ✅ Lazy loading, zero overhead |
| Installation failures | Medium | Low | ✅ Graceful errors, clear messages |
| Documentation outdated | Low | Low | ✅ Comprehensive docs included |
| Dependency conflicts | Low | Medium | ✅ Common deps (fastapi stable) |

**Overall Risk: LOW** ✅

---

## 🐛 Rollback Plan

If critical issues arise:

```bash
# Option 1: Revert merge commit
git checkout master
git revert -m 1 <merge-commit-sha>
git push origin master

# Option 2: Reset (if not released to PyPI)
git reset --hard <commit-before-merge>
git push origin master --force
```

**Safe because:**
- Optional dependencies (existing users unaffected)
- No core functionality changes
- Feature can be disabled by not installing `[mcp]`

---

## 📝 PyPI Release Procedure

### 1. Update Version

```python
# pyproject.toml
[project]
name = "kurral"
version = "0.3.0"  # Bump from 0.2.2
```

### 2. Build Distribution

```bash
# Clean old builds
rm -rf dist/ build/ *.egg-info

# Build
python -m build

# Verify contents
tar -tzf dist/kurral-0.3.0.tar.gz | grep mcp
```

### 3. Test on TestPyPI (Optional)

```bash
# Upload to test
python -m twine upload --repository testpypi dist/*

# Test install
pip install --index-url https://test.pypi.org/simple/ kurral[mcp]
```

### 4. Release to PyPI

```bash
python -m twine upload dist/*
```

### 5. Verify

```bash
pip install --upgrade kurral[mcp]
kurral --version  # Should show 0.3.0
kurral mcp --help
```

---

## 📢 Announcement Template

### GitHub Release Notes

```markdown
# Kurral v0.3.0: MCP Proxy with SSE Streaming

## 🌊 Major New Feature: MCP Proxy

Kurral now includes a complete HTTP/SSE proxy for the Model Context Protocol, enabling full observability and deterministic replay of MCP tool calls.

### Quick Start

\`\`\`bash
pip install kurral[mcp]
kurral mcp start --mode record
\`\`\`

### What's New

✅ **Record Mode** - Capture all MCP tool calls to `.kurral` artifacts
✅ **Replay Mode** - Return cached responses for deterministic testing
✅ **SSE Streaming** - Full event-by-event capture and replay
✅ **Performance Metrics** - Duration, event rates, time-to-first-event
✅ **Multi-Server Routing** - Route tools to different upstream servers
✅ **Semantic Matching** - Fuzzy argument matching for flexible replay

### Documentation

- [MCP Proxy User Guide](https://github.com/Kurral/Kurralv3/blob/master/MCP_PROXY_README.md)
- [SSE Implementation Details](https://github.com/Kurral/Kurralv3/blob/master/kurral/mcp/SSE_IMPLEMENTATION.md)
- [Integration Tests](https://github.com/Kurral/Kurralv3/tree/master/examples/mcp_test)

### Installation

\`\`\`bash
# Core Kurral (unchanged)
pip install kurral

# With MCP proxy support
pip install kurral[mcp]
\`\`\`

### Breaking Changes

None! This is a purely additive release. Existing Kurral functionality is unchanged.

### Contributors

Thanks to everyone who contributed to this release!

**Full Changelog**: https://github.com/Kurral/Kurralv3/compare/v0.2.2...v0.3.0
```

---

## ✅ Final Checklist

Before declaring merge complete:

- [ ] All tests passing on master
- [ ] README.md updated with MCP section
- [ ] CHANGELOG.md created/updated
- [ ] Version bumped to 0.3.0
- [ ] Merged to master and pushed
- [ ] Git tag v0.3.0 created
- [ ] PyPI package built and tested
- [ ] PyPI package released
- [ ] GitHub release created
- [ ] Documentation links verified
- [ ] Integration test passes from clean install

---

## 🎯 Success Metrics

After 1 week, check:

- [ ] No critical bugs reported
- [ ] Installation success rate > 95%
- [ ] Documentation clarity (user feedback)
- [ ] GitHub stars increase
- [ ] Community engagement (issues, discussions)

---

## 📞 Support Plan

- Monitor GitHub issues for MCP-related problems
- Respond to questions within 24 hours
- Prepare hotfix release if critical bugs found
- Update FAQ based on common questions
- Consider creating Discord/Slack for real-time support

---

**Prepared by:** Claude Code
**Date:** 2025-12-15
**Branch:** mcp-proxy → master
**Target Version:** 0.3.0

