# Release Scripts

This directory contains scripts for releasing Kurral to PyPI.

## Scripts

### `pre-release-check.sh`

Runs a comprehensive pre-release checklist to verify the package is ready for release.

```bash
chmod +x scripts/pre-release-check.sh
./scripts/pre-release-check.sh
```

Checks:
- ✅ Required files exist
- ✅ Python version >= 3.11
- ✅ Required tools installed (build, twine, git)
- ✅ No uncommitted changes
- ✅ Version format valid
- ✅ CHANGELOG updated
- ✅ Package builds successfully
- ✅ Package passes twine check
- ✅ Package imports correctly
- ✅ CLI works
- ✅ Dependencies available

### `release.sh`

Automated release pipeline that handles the complete release process.

```bash
chmod +x scripts/release.sh
./scripts/release.sh 0.1.0
```

Steps:
1. Validates version format
2. Checks git status
3. Updates version in `pyproject.toml`
4. Cleans build artifacts
5. Builds package
6. Checks package integrity
7. Uploads to TestPyPI (optional)
8. Uploads to PyPI (with confirmation)
9. Creates git tag
10. Pushes to remote (optional)

## Usage

**Before first release:**

```bash
# Make scripts executable
chmod +x scripts/*.sh

# Run pre-release checks
./scripts/pre-release-check.sh

# If all checks pass, release
./scripts/release.sh 0.1.0
```

**For subsequent releases:**

```bash
# Update CHANGELOG.md with new version

# Run checks
./scripts/pre-release-check.sh

# Release
./scripts/release.sh 0.1.1
```

## Manual Release

If you prefer manual control, see [../PUBLISHING.md](../PUBLISHING.md) for step-by-step instructions.

