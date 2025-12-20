# Code Review Agent - Kurral Production Example

AI-powered code reviewer demonstrating Kurral's value for testing code analysis agents.

## 🎯 What This Demonstrates

**Use Case:** Automated code review with security checks, style suggestions, and best practices

**Kurral Value:**
- Test review logic changes without re-running expensive LLM calls
- Validate security pattern detection
- Regression test code quality rules
- Compare review quality across LLM models

## 💰 Cost Savings

Testing 50 code files for review logic changes:
- **Without Kurral:** 50 files × $0.15/file = $7.50 per test run
- **With Kurral:** Initial capture $7.50, unlimited replays = $0

Annual testing (weekly): **$390 → $7.50** (98% savings)

## 🚀 Quick Start

```bash
# Install
pip install -r requirements.txt
cp .env.example .env

# Review a file
python agent.py path/to/your/code.py

# Replay for free
kurral replay --latest
```

## 🛠️ Tools

1. **read_file** - Load code to review
2. **check_security** - Detect common vulnerabilities (SQL injection, XSS, etc.)
3. **check_style** - PEP 8, naming conventions, complexity
4. **suggest_improvements** - Best practices, refactoring opportunities

## 📊 Example Output

```
Security Issues: 2 found
  - SQL injection risk (line 45)
  - Hardcoded credentials (line 12)

Style Issues: 5 found
  - Line too long (lines 23, 67, 89)
  - Missing docstrings (functions: process_data, validate_input)

Suggestions:
  ✓ Consider using prepared statements for database queries
  ✓ Move credentials to environment variables
  ✓ Add type hints for better code clarity
```

---

**Generated from:** `kurral init` (vanilla template)
