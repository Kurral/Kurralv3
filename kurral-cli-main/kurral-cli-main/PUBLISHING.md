# Publishing Kurral to PyPI

This guide walks through the complete process of publishing Kurral to PyPI.

## One-Time Setup

### 1. Install Build Tools

```bash
pip install --upgrade pip build twine
```

### 2. Create PyPI Accounts

- **TestPyPI** (for testing): https://test.pypi.org/account/register/
- **PyPI** (production): https://pypi.org/account/register/

### 3. Enable 2FA and Get API Tokens

**On PyPI:**
1. Go to https://pypi.org/manage/account/
2. Enable Two-Factor Authentication (required)
3. Go to https://pypi.org/manage/account/token/
4. Click "Add API token"
5. Token name: "kurral-cli-uploads"
6. Scope: "Entire account" (or specific to kurral after first upload)
7. Copy the token (starts with `pypi-`)

**On TestPyPI:**
1. Repeat for https://test.pypi.org/manage/account/token/

### 4. Configure Credentials

```bash
# Copy template
cp .pypirc.template ~/.pypirc

# Edit with your tokens
nano ~/.pypirc

# Secure it
chmod 600 ~/.pypirc
```

Your `~/.pypirc` should look like:

```ini
[distutils]
index-servers =
    pypi
    testpypi

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-AgENdGVzdC5weXBpLm9yZ...  # Your TestPyPI token

[pypi]
repository = https://upload.pypi.org/legacy/
username = __token__
password = pypi-AgEIcHlwaS5vcmc...  # Your PyPI token
```

## Release Process

### Quick Release (Using Script)

```bash
# Make sure you're on main branch and everything is committed
git checkout main
git pull

# Run release script
./scripts/release.sh 0.1.0
```

The script will:
1. ✅ Validate version format
2. ✅ Check for uncommitted changes
3. ✅ Update version in `pyproject.toml`
4. ✅ Clean previous builds
5. ✅ Build package (wheel + source dist)
6. ✅ Check package integrity
7. ✅ Upload to TestPyPI
8. ✅ Upload to PyPI (after confirmation)
9. ✅ Create git tag
10. ✅ Push to remote

### Manual Release (Step by Step)

If you prefer manual control:

#### 1. Prepare Release

```bash
# Update version in pyproject.toml
version = "0.1.0"  # Set your version

# Update CHANGELOG.md
# Add release notes for this version

# Commit changes
git add pyproject.toml CHANGELOG.md
git commit -m "Prepare release v0.1.0"
git push
```

#### 2. Clean and Build

```bash
# Clean previous builds
rm -rf build/ dist/ *.egg-info

# Build package
python -m build

# Verify contents
ls -lh dist/
```

You should see:
- `kurral-0.1.0-py3-none-any.whl` (wheel)
- `kurral-0.1.0.tar.gz` (source distribution)

#### 3. Check Package

```bash
# Check for errors
python -m twine check dist/*
```

Should show: `Checking dist/... PASSED`

#### 4. Test on TestPyPI

```bash
# Upload to TestPyPI
python -m twine upload --repository testpypi dist/*

# Test installation
pip install --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  kurral

# Verify it works
kurral --version
kurral --help
```

#### 5. Upload to Production PyPI

```bash
# Upload to PyPI (THIS IS PERMANENT!)
python -m twine upload dist/*
```

#### 6. Create Git Tag

```bash
# Tag the release
git tag -a v0.1.0 -m "Release v0.1.0"

# Push tag
git push origin v0.1.0
```

#### 7. Create GitHub Release

1. Go to https://github.com/kurral-dev/kurral-cli/releases/new
2. Choose tag: `v0.1.0`
3. Release title: "Kurral v0.1.0 - Initial Public Release"
4. Description: Copy from CHANGELOG.md
5. Attach files: `dist/kurral-0.1.0.tar.gz` and `dist/kurral-0.1.0-py3-none-any.whl`
6. Click "Publish release"

## Post-Release

### Verify Release

```bash
# Check PyPI page
open https://pypi.org/project/kurral/

# Test installation in fresh environment
python -m venv test-env
source test-env/bin/activate
pip install kurral
kurral --version
deactivate
rm -rf test-env
```

### Update Documentation

- [ ] Update README with new version
- [ ] Update installation instructions
- [ ] Update examples if needed
- [ ] Announce on social media
- [ ] Monitor GitHub issues

## Version Numbering

Follow Semantic Versioning (semver):

- **MAJOR** version (1.0.0): Incompatible API changes
- **MINOR** version (0.1.0): New features, backwards compatible
- **PATCH** version (0.1.1): Bug fixes, backwards compatible

Examples:
- `0.1.0` - Initial public release
- `0.1.1` - Bug fix
- `0.2.0` - New features (e.g., A/B testing)
- `1.0.0` - Stable API, production ready

## Troubleshooting

### Error: "File already exists"

PyPI doesn't allow re-uploading the same version.

**Solution:** Increment version number

```bash
# Change version in pyproject.toml
version = "0.1.1"  # Increment

# Rebuild and upload
rm -rf dist/
python -m build
python -m twine upload dist/*
```

### Error: "Invalid or non-existent authentication information"

Your API token is incorrect or expired.

**Solution:** Regenerate token on PyPI and update `~/.pypirc`

### Error: "Repository URL not found"

Check your `~/.pypirc` configuration.

**Solution:**
```ini
[pypi]
repository = https://upload.pypi.org/legacy/  # Note: /legacy/ at end
```

### Build Errors

```bash
# Clear all caches and try again
rm -rf build/ dist/ *.egg-info
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
python -m build
```

## Testing Releases

### Local Testing

```bash
# Install in development mode
pip install -e .

# Test commands
kurral --version
kurral auth register --help
kurral config init
```

### Testing from TestPyPI

```bash
# Install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  kurral==0.1.0

# Run tests
kurral --version
kurral auth status
```

## Release Checklist

Before each release:

- [ ] All tests pass (`pytest`)
- [ ] Code is formatted (`black`, `ruff`)
- [ ] Type checking passes (`mypy`)
- [ ] Version updated in `pyproject.toml`
- [ ] CHANGELOG.md updated
- [ ] README.md reviewed
- [ ] All changes committed
- [ ] Tested on TestPyPI
- [ ] Tested installation from TestPyPI

After release:

- [ ] GitHub release created
- [ ] Documentation updated
- [ ] Social media announcement
- [ ] Monitor GitHub issues
- [ ] Increment version for next development cycle

## Resources

- **PyPI**: https://pypi.org/project/kurral/
- **TestPyPI**: https://test.pypi.org/project/kurral/
- **PyPI Help**: https://pypi.org/help/
- **Packaging Guide**: https://packaging.python.org/
- **Twine Docs**: https://twine.readthedocs.io/

## Support

If you encounter issues:

1. Check this guide's troubleshooting section
2. Search PyPI packaging documentation
3. Open an issue on GitHub
4. Contact the team on Discord/Slack

---

**Ready to publish?** Run `./scripts/release.sh 0.1.0` 🚀

