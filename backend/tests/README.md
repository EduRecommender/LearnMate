# LearnMate Test Suite

This directory contains the test suite for the LearnMate backend services and functionality.

## Test Structure

The tests are organized to verify the functionality of various components:

- API endpoint tests
- Model and data structure tests
- Integration tests with external services (Ollama, etc.)
- Utility function tests

## Running Tests

### Locally

From the backend directory:

```bash
# Run all tests
pytest

# Run tests with verbose output
pytest -v

# Run specific test file
pytest tests/test_file.py

# Run specific test function
pytest tests/test_file.py::test_function_name

# Run tests with coverage report
pytest --cov=app
```

### With Docker

From the project root directory:

```bash
docker-compose up pytest
```

This will run all tests in an isolated container with the same dependencies as the backend.

## Environment Variables for Testing

Tests can be configured with environment variables:

```
TESTING=true
SKIP_OLLAMA_CHECK=true  # Skip tests that require Ollama
```

## Test Configuration

The test configuration is defined in `pytest.ini` in the backend directory. This includes:

- Default plugins
- Test markers
- Log formats and levels

## Writing New Tests

When adding new functionality, please add corresponding test cases:

1. Create or modify test files in the appropriate test directory
2. Follow the existing naming convention: `test_*.py` for files and `test_*` for functions
3. Use pytest fixtures for common setup/teardown
4. Add comments to explain complex test scenarios

## GitHub Actions Integration

Tests are automatically run on GitHub for pull requests and pushes to the main branch. The GitHub workflow configuration can be found in the `.github/workflows` directory.
