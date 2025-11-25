# Contributing to Kurral

Thank you for your interest in contributing to Kurral! This document provides guidelines and instructions for contributing.

## Development Setup

1. **Fork and clone the repository**
```bash
git clone https://github.com/your-username/kurral.git
cd kurral
```

2. **Create a virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install in development mode**
```bash
make dev
# or
pip install -e ".[dev]"
```

4. **Start local services**
```bash
make docker-up
make init-db
```

## Development Workflow

### Running Tests
```bash
# Run all tests
make test

# Run specific test file
pytest tests/test_artifact.py -v

# Run with coverage
pytest --cov=kurral --cov-report=html
```

### Code Quality

**Formatting:**
```bash
make format
```

**Linting:**
```bash
make lint
```

### Making Changes

1. **Create a feature branch**
```bash
git checkout -b feature/your-feature-name
```

2. **Make your changes**
- Write code following the existing style
- Add tests for new functionality
- Update documentation as needed

3. **Test your changes**
```bash
make test
make lint
```

4. **Commit your changes**
```bash
git add .
git commit -m "Add feature: description"
```

5. **Push and create a pull request**
```bash
git push origin feature/your-feature-name
```

## Code Style

- Use `black` for formatting (line length: 100)
- Follow PEP 8 guidelines
- Use type hints for function signatures
- Write docstrings for public APIs

## Pull Request Guidelines

- **Title**: Use clear, descriptive titles
- **Description**: Explain what and why, not how
- **Tests**: Include tests for new features
- **Documentation**: Update README and docstrings
- **Commits**: Keep commits focused and atomic

## Areas for Contribution

- **Core Features**: Enhance replay engine, add new storage backends
- **Integrations**: Add support for more LLM providers
- **CLI**: Improve user experience, add new commands
- **Documentation**: Examples, tutorials, API docs
- **Tests**: Increase coverage, add integration tests
- **Performance**: Optimize hot paths, reduce memory usage

## Questions?

- Open an issue for bugs or feature requests
- Join our Discord for discussions
- Check existing issues before creating new ones

Thank you for contributing! 🎉

