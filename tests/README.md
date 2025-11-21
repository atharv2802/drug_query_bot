# Drug Query Bot - Tests

This directory contains the test suite for the Drug Query Assistant.

## Running Tests

### Install Test Dependencies
```bash
pip install -r requirements.txt
```

### Run All Tests
```bash
pytest
```

### Run with Coverage Report
```bash
pytest --cov=utils --cov=config --cov-report=html
```

### Run Specific Test File
```bash
pytest tests/test_fuzzy.py
```

### Run Specific Test Class
```bash
pytest tests/test_fuzzy.py::TestNormalizeDrugName
```

### Run Specific Test Function
```bash
pytest tests/test_fuzzy.py::TestNormalizeDrugName::test_lowercase_conversion
```

## Test Structure

- `conftest.py` - Shared fixtures and pytest configuration
- `test_fuzzy.py` - Tests for fuzzy matching utilities
- `test_intent.py` - Tests for intent parsing utilities
- `test_db.py` - Tests for database access layer (with mocks)
- `test_llm.py` - Tests for LLM integration (with mocks)

## Test Coverage

The test suite covers:
- Drug name normalization and fuzzy matching
- Intent detection and query parsing
- Filter extraction and validation
- Database query functions (mocked)
- LLM API interactions (mocked)
- Error handling and edge cases

## Writing New Tests

Follow the existing patterns:
- Use pytest fixtures from `conftest.py`
- Mock external dependencies (DB, API calls)
- Test both success and failure paths
- Include edge cases and error handling
