# Security Features Integration Guide

This document explains how to integrate Kurral's proprietary security features with the public Kurralv3 framework.

## Architecture

Kurral uses a **dual-package architecture**:

1. **Public Package (`kurral`)**: Open-source MCP proxy infrastructure
   - Repository: https://github.com/Kurral/Kurralv3
   - Contains: MCP proxy, record/replay, routing, artifacts

2. **Private Package (`kurral-security`)**: Proprietary security features
   - Repository: https://github.com/Kurral/kurral-security-private (PRIVATE)
   - Contains: Security monitoring, adversarial assessment, attack payloads

## Team Setup

### Prerequisites

- Access to private repository (request from team lead)
- Python 3.9+
- Git

### Installation

```bash
# 1. Clone both repositories
git clone https://github.com/Kurral/Kurralv3.git
git clone https://github.com/Kurral/kurral-security-private.git

# 2. Install public package
cd Kurralv3
pip install -e .

# 3. Install private security package
cd ../kurral-security-private
pip install -e .

# 4. Verify installation
python -c "from kurral.mcp import KurralMCPProxy; print('✓ Public package ready')"
python -c "from kurral_security.assessment import AttackInjector; print('✓ Security package ready')"
```

## Usage Examples

### Basic MCP Proxy (Public Features Only)

```python
from kurral.mcp import KurralMCPProxy, MCPConfig

# Basic record/replay without security
config = MCPConfig(mode="record")
proxy = KurralMCPProxy(config)
await proxy.start()
```

### With Security Monitoring (Requires Private Package)

```python
from kurral_security import KurralSecurityProxy
from kurral.mcp.config import MCPConfig

# Enable passive security monitoring
config = MCPConfig(
    mode="record",
    security={
        "enabled": True,
        "pii_detection": True,
        "baseline_tracking": True
    }
)
proxy = KurralSecurityProxy(config)
await proxy.start()
```

### Adversarial Assessment Mode (Requires Private Package)

```python
from kurral_security import KurralSecurityProxy
from kurral.mcp.config import MCPConfig

# Run full security assessment
config = MCPConfig(
    mode="assessment",
    assessment={
        "enabled": True,
        "duration_minutes": 30,
        "max_payloads": 50,
        "enable_safety_gate": True,
        "report_format": "html",
        "report_output": "./security_report.html"
    }
)
proxy = KurralSecurityProxy(config)
await proxy.start()

# After assessment completes, check ./security_report.html
```

### Using Security Modules Directly

```python
# Import from private package
from kurral_security.core import SecurityInspector, PIIDetector
from kurral_security.assessment import (
    AttackInjector,
    SafetyGate,
    BehaviorualAnalyzer,
    SecurityReporter
)

# Use security components
pii_detector = PIIDetector()
matches = pii_detector.scan_json({"email": "user@example.com"})
print(matches)  # [PIIMatch(type='email', value='user@example.com', ...)]

# Inject attack payloads for testing
injector = AttackInjector()
payload = injector.next_payload()
print(payload.category)  # 'sql_injection', 'path_traversal', etc.
```

## Testing

### Run Public Package Tests

```bash
cd Kurralv3
pytest tests/
```

### Run Security Package Tests

```bash
cd kurral-security-private
pytest tests/
```

### Integration Testing

```bash
# Test both packages together
cd Kurralv3
pytest tests/ --security  # Runs extended tests with security features
```

## Configuration

### Public-Only Configuration (config.yaml)

```yaml
mode: record
artifact_path: ./artifacts
capture:
  enabled: true
  format: json
```

### With Security Features (config.yaml)

```yaml
mode: record

# Passive security monitoring (optional)
security:
  enabled: true
  pii_detection: true
  baseline_tracking: true
  violation_logging: true

# Active adversarial testing (optional)
assessment:
  enabled: false  # Enable only for security assessments
  duration_minutes: 30
  max_payloads: 50
  enable_safety_gate: true
  report_format: html
```

## Development Workflow

### Working on Public Features

```bash
cd Kurralv3
git checkout -b feature/my-public-feature
# Make changes to MCP infrastructure
git commit -m "feat: Add new MCP routing feature"
git push origin feature/my-public-feature
# Create PR to public repo
```

### Working on Security Features

```bash
cd kurral-security-private
git checkout -b feature/my-security-feature
# Make changes to security modules
git commit -m "feat: Add new attack payload detection"
git push origin feature/my-security-feature
# Create PR to PRIVATE repo
```

## Why Two Repositories?

**Benefits:**
- ✅ Protect proprietary security IP
- ✅ Allow community contributions to public MCP infrastructure
- ✅ Easy to sync public updates (just `git pull`)
- ✅ Clear separation: open source vs proprietary
- ✅ Security features are optional "premium" layer

**Trade-offs:**
- ⚠️ Need to install both packages
- ⚠️ Manage dependencies between two packages

## Troubleshooting

### "ModuleNotFoundError: No module named 'kurral_security'"

**Solution**: Install the private security package:
```bash
cd kurral-security-private
pip install -e .
```

### "ImportError: cannot import name 'KurralSecurityProxy'"

**Cause**: You don't have access to the private repository, or haven't installed it.

**Solution**: Request access from your team lead, then clone and install:
```bash
git clone https://github.com/Kurral/kurral-security-private.git
cd kurral-security-private
pip install -e .

# Verify installation
python -c "from kurral_security import KurralSecurityProxy; print('✓ Security proxy ready')"
```

### Security features not working

**Check installation**:
```bash
python -c "import kurral_security; print(kurral_security.__version__)"
```

If this fails, reinstall the private package.

## Support

- **Public features**: https://github.com/Kurral/Kurralv3/issues
- **Security features**: Contact security team (private repo only)
- **Access requests**: team@kurral.com

---

**Remember**: The `kurral-security-private` repository is PRIVATE. Do not share code, payloads, or detection logic publicly.
