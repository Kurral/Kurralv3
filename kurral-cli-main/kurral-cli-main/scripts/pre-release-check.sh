#!/bin/bash
# Pre-release checklist script
# Verifies package is ready for release

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo "======================================"
echo "   Kurral Pre-Release Checklist"
echo "======================================"
echo ""

PASS=0
FAIL=0

check_pass() {
    echo -e "${GREEN}✅ $1${NC}"
    ((PASS++))
}

check_fail() {
    echo -e "${RED}❌ $1${NC}"
    ((FAIL++))
}

check_warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Check 1: Required files exist
echo "📋 Checking required files..."
for file in pyproject.toml setup.py README.md LICENSE CHANGELOG.md MANIFEST.in; do
    if [ -f "$file" ]; then
        check_pass "$file exists"
    else
        check_fail "$file missing"
    fi
done

# Check 2: Python version
echo ""
echo "🐍 Checking Python version..."
PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
if [[ "$PYTHON_VERSION" > "3.11" ]]; then
    check_pass "Python $PYTHON_VERSION (>= 3.11)"
else
    check_fail "Python $PYTHON_VERSION (requires >= 3.11)"
fi

# Check 3: Required tools installed
echo ""
echo "🔧 Checking required tools..."
for tool in build twine git; do
    if command -v $tool >/dev/null 2>&1; then
        check_pass "$tool installed"
    else
        check_fail "$tool not installed"
    fi
done

# Check if build module is available
if python -c "import build" 2>/dev/null; then
    check_pass "build module available"
else
    check_fail "build module not installed (pip install build)"
fi

if python -c "import twine" 2>/dev/null; then
    check_pass "twine module available"
else
    check_fail "twine module not installed (pip install twine)"
fi

# Check 4: Git status
echo ""
echo "📦 Checking git status..."
if [ -z "$(git status --porcelain)" ]; then
    check_pass "No uncommitted changes"
else
    check_warn "You have uncommitted changes"
fi

BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$BRANCH" = "main" ] || [ "$BRANCH" = "master" ]; then
    check_pass "On main/master branch ($BRANCH)"
else
    check_warn "Not on main branch (current: $BRANCH)"
fi

# Check 5: Version format in pyproject.toml
echo ""
echo "🏷️  Checking version..."
VERSION=$(grep -m 1 'version = ' pyproject.toml | sed 's/.*= "\(.*\)"/\1/')
if [[ $VERSION =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    check_pass "Version format valid: $VERSION"
else
    check_fail "Version format invalid: $VERSION (should be X.Y.Z)"
fi

# Check 6: CHANGELOG updated
echo ""
echo "📝 Checking CHANGELOG..."
if grep -q "\[$VERSION\]" CHANGELOG.md; then
    check_pass "CHANGELOG has entry for v$VERSION"
else
    check_warn "CHANGELOG might not have entry for v$VERSION"
fi

# Check 7: Build test
echo ""
echo "🔨 Testing build..."
rm -rf build/ dist/ *.egg-info 2>/dev/null || true
if python -m build > /dev/null 2>&1; then
    check_pass "Package builds successfully"
    
    # Check build artifacts
    if [ -f "dist/kurral-${VERSION}-py3-none-any.whl" ]; then
        check_pass "Wheel created"
    else
        check_fail "Wheel not created"
    fi
    
    if [ -f "dist/kurral-${VERSION}.tar.gz" ]; then
        check_pass "Source distribution created"
    else
        check_fail "Source distribution not created"
    fi
    
    # Check with twine
    if python -m twine check dist/* > /dev/null 2>&1; then
        check_pass "Package passes twine check"
    else
        check_fail "Package fails twine check"
    fi
else
    check_fail "Package build failed"
fi

# Check 8: Import test
echo ""
echo "🧪 Testing package import..."
if python -c "import kurral" 2>/dev/null; then
    check_pass "Package imports successfully"
else
    check_warn "Package import test failed (install with: pip install -e .)"
fi

# Check 9: CLI test
echo ""
echo "⌨️  Testing CLI..."
if python -c "from kurral.cli.main import cli" 2>/dev/null; then
    check_pass "CLI imports successfully"
else
    check_fail "CLI import failed"
fi

# Check 10: Dependencies
echo ""
echo "📦 Checking dependencies..."
MISSING_DEPS=0
while IFS= read -r dep; do
    pkg=$(echo "$dep" | sed 's/[>=<].*//' | tr -d ' "')
    if python -c "import $pkg" 2>/dev/null || python -c "import ${pkg//-/_}" 2>/dev/null; then
        :  # Dependency found
    else
        check_warn "Dependency might be missing: $pkg"
        ((MISSING_DEPS++))
    fi
done < <(grep -A 100 'dependencies = \[' pyproject.toml | grep -B 100 '\]' | grep '    "' | head -20)

if [ $MISSING_DEPS -eq 0 ]; then
    check_pass "All dependencies appear to be available"
fi

# Summary
echo ""
echo "======================================"
echo "   Summary"
echo "======================================"
echo ""
echo -e "${GREEN}Passed: $PASS${NC}"
echo -e "${RED}Failed: $FAIL${NC}"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}✅ All critical checks passed!${NC}"
    echo ""
    echo "Ready to release? Run:"
    echo "  ./scripts/release.sh $VERSION"
    echo ""
    exit 0
else
    echo -e "${RED}❌ $FAIL check(s) failed${NC}"
    echo ""
    echo "Fix the issues above before releasing."
    exit 1
fi

