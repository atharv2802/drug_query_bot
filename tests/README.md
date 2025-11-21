# Test Suite - Drug Query Bot

Comprehensive test coverage for all components of the Drug Query Bot.

## Running Tests

### All Tests
```bash
pytest
```

### Specific Test Files
```bash
pytest tests/test_db.py -v          # Database layer tests
pytest tests/test_intent.py -v      # Intent parsing tests  
pytest tests/test_llm.py -v         # LLM integration tests
pytest tests/test_fuzzy.py -v       # Fuzzy matching tests
pytest tests/test_full_pipeline_supabase.py -v  # End-to-end tests
```

### With Coverage
```bash
pytest --cov=. --cov-report=html
# Open htmlcov/index.html to view coverage report
```

## Test Files

### `test_db.py`
Tests database operations:
- Supabase client connection
- Drug queries by name (exact and fuzzy matching)
- Filtering by multiple criteria
- Fetching alternatives
- Category retrieval

### `test_intent.py`
Tests query intent extraction:
- Rule-based pattern matching
- Query type classification (drug_status, alternatives, list_filter)
- Filter extraction from natural language
- Edge cases and malformed queries

### `test_llm.py`
Tests LLM integration:
- OpenRouter API calls
- Intent extraction with LLM
- Answer generation
- Error handling and retries
- JSON parsing robustness

### `test_fuzzy.py`
Tests fuzzy string matching:
- Levenshtein distance calculations
- Drug name similarity matching
- Confidence score validation
- Case-insensitive matching

### `test_full_pipeline_supabase.py`
End-to-end integration test:
- Complete query flow from input to output
- Database integration with real data
- LLM integration (if API key available)
- Result formatting

### `test_supabase_connection.py`
Standalone connection validator:
- Supabase client initialization
- All database operations
- Manufacturer filter testing
- Category queries

### `llm_response_debug.py`
LLM debugging utility:
- Raw API response logging
- Prompt testing
- JSON extraction validation

### `verify_ingestion_logic.py`
Data ingestion validator:
- CSV parsing verification
- Drug status normalization
- PA/MND merging logic

## Test Coverage Goals

- **Database Layer**: 95%+
- **Intent Parsing**: 100%
- **Fuzzy Matching**: 90%+
- **LLM Integration**: 85%+
- **Full Pipeline**: 100%

## Setup Requirements

### Environment Variables
```bash
export SUPABASE_URL="your-supabase-url"
export SUPABASE_KEY="your-supabase-anon-key"
export OPENROUTER_API_KEY="your-openrouter-key"  # Optional for LLM tests
```

Or use `.streamlit/secrets.toml`:
```toml
SUPABASE_URL = "your-supabase-url"
SUPABASE_KEY = "your-supabase-anon-key"
OPENROUTER_API_KEY = "your-openrouter-key"
```

## Test Data

Tests use the real database with production data. Ensure data is ingested before running tests:
```bash
python ingest_data.py
```

## CI/CD Integration

Tests are designed to run in CI/CD pipelines with environment-based configuration. See `.github/workflows/` for GitHub Actions setup (if configured).

## Debugging Failed Tests

1. **Database connection failures**:
   - Verify Supabase credentials in secrets
   - Check network connectivity
   - Run `python tests/test_supabase_connection.py` for detailed diagnostics

2. **LLM test failures**:
   - Verify OpenRouter API key is valid
   - Check account has credits
   - Tests will skip if API key not found (not a failure)

3. **Fuzzy matching failures**:
   - Ensure data is ingested correctly
   - Check drug name normalization in database

Run with verbose output for debugging:
```bash
pytest -vv --tb=short
```
