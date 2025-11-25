#!/bin/bash
# Kurral Release Script
# Usage: ./scripts/release.sh <version>
# Example: ./scripts/release.sh 0.1.0

set -e  # Exit on error

VERSION=$1

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
error() {
    echo -e "${RED}❌ Error: $1${NC}" >&2
    exit 1
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Validate input
if [ -z "$VERSION" ]; then
    error "Version not specified\nUsage: $0 <version>\nExample: $0 0.1.0"
fi

# Validate version format (semver)
if ! [[ $VERSION =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    error "Invalid version format. Use semantic versioning (e.g., 0.1.0)"
fi

echo ""
echo "======================================"
echo "   Kurral Release Pipeline v$VERSION"
echo "======================================"
echo ""

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    error "pyproject.toml not found. Run this script from the project root."
fi

# Check if required tools are installed
info "Checking required tools..."
command -v python3 >/dev/null 2>&1 || error "python3 not found"
command -v git >/dev/null 2>&1 || error "git not found"

# Check if build and twine are installed
python3 -c "import build" 2>/dev/null || error "build not installed. Run: pip install build"
python3 -c "import twine" 2>/dev/null || error "twine not installed. Run: pip install twine"

success "All required tools found"

# Check git status
info "Checking git status..."
if [ -n "$(git status --porcelain)" ]; then
    warning "You have uncommitted changes"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if tag already exists
if git rev-parse "v$VERSION" >/dev/null 2>&1; then
    error "Tag v$VERSION already exists"
fi

# Update version in pyproject.toml
info "Updating version in pyproject.toml to $VERSION..."
sed -i.bak "s/^version = .*/version = \"$VERSION\"/" pyproject.toml
rm pyproject.toml.bak
success "Version updated"

# Clean previous builds
info "Cleaning previous builds..."
rm -rf build/ dist/ *.egg-info
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete
success "Build artifacts cleaned"

# Build package
info "Building package..."
python3 -m build
success "Package built successfully"

# Check package
info "Checking package integrity..."
python3 -m twine check dist/*
success "Package check passed"

# Show what will be uploaded
echo ""
info "Package contents:"
ls -lh dist/
echo ""

# Upload to TestPyPI
info "Uploading to TestPyPI..."
read -p "Proceed with TestPyPI upload? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if python3 -m twine upload --repository testpypi dist/* 2>&1; then
        success "Uploaded to TestPyPI"
        info "Test installation with:"
        echo "  pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ kurral"
        echo ""
    else
        error "TestPyPI upload failed"
    fi
else
    warning "TestPyPI upload skipped"
fi

# Upload to Production PyPI
echo ""
warning "Ready to upload to PRODUCTION PyPI"
info "This cannot be undone. Version $VERSION will be permanent."
read -p "Upload to PyPI? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    warning "Production upload cancelled"
    exit 0
fi

info "Uploading to PyPI..."
if python3 -m twine upload dist/* 2>&1; then
    success "Uploaded to PyPI"
else
    error "PyPI upload failed"
fi

# Create git tag
info "Creating git tag v$VERSION..."
git add pyproject.toml
git commit -m "Release v$VERSION" || true
git tag -a "v$VERSION" -m "Release v$VERSION"
success "Git tag created"

# Push to remote
read -p "Push tag to remote? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    git push origin "v$VERSION"
    git push origin main || git push origin master
    success "Tag pushed to remote"
fi

# Final summary
echo ""
echo "======================================"
echo "   Release v$VERSION Complete! 🎉"
echo "======================================"
echo ""
success "Package published to PyPI"
info "PyPI URL: https://pypi.org/project/kurral/$VERSION/"
info "Installation: pip install kurral"
echo ""
info "Next steps:"
echo "  1. Create GitHub release: https://github.com/kurral-dev/kurral-cli/releases/new"
echo "  2. Update documentation"
echo "  3. Announce release"
echo ""

