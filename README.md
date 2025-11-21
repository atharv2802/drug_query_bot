
# Drug Status & Prior Authorization Assistant

A production-ready drug information lookup system built with **Streamlit + Supabase + OpenRouter LLM**.

Query drug status, PA/MND requirements, and preferred alternatives using natural language - powered by hybrid rule-based + AI intelligence.

---


## Features

- Drug Status Lookup - Check if drugs are preferred/non-preferred
- PA/MND Requirements - Find Prior Authorization and Medical Necessity requirements
- Preferred Alternatives - Discover alternative drugs in the same category
- Advanced Filtering - List drugs by multiple criteria (status, PA, MND, category)
- Smart Query Understanding - Hybrid rule-based + LLM parsing
- Fuzzy Matching - Handles typos and name variations
- Safe & Grounded - Database-backed only, no hallucinations, no medical advice

---


## Quick Start (5 Minutes)

### Prerequisites
- Python 3.9+
- Supabase account (free tier works)
- OpenRouter API key

### Installation

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up Supabase database
python create_schema.py
# Enter your DATABASE_URL when prompted

# 3. Configure secrets
# Copy .streamlit/secrets.toml.example to .streamlit/secrets.toml
# Add your credentials (see Configuration section below)

# 4. Load sample data (or use your own CSV files)
python ingest_data.py

# 5. Run the app
streamlit run app.py
```

**That's it!** App opens at http://localhost:8501

---


## Configuration

Create `.streamlit/secrets.toml` with:

```toml
DATABASE_URL = "postgresql://postgres:password@db.xxxxx.supabase.co:5432/postgres"
OPENROUTER_API_KEY = "sk-or-v1-your-api-key-here"
SUPABASE_URL = "https://xxxxx.supabase.co"
SUPABASE_KEY = "your-supabase-anon-key"
```

### Get Your Credentials:

**Supabase:**
1. Create project at https://supabase.com
2. Go to Project Settings → Database
3. Copy "Connection String" (URI format)
4. Replace `[YOUR-PASSWORD]` with your actual password

**OpenRouter:**
1. Sign up at https://openrouter.ai
2. Go to Keys section
3. Create new API key
4. Copy the key (starts with `sk-or-v1-`)

---


## Database Setup

### Option 1: Using the Script (Recommended)

```bash
python create_schema.py
```

### Option 2: Manual Setup

Run this SQL in Supabase SQL Editor:

```sql
CREATE TABLE drugs (
    drug_name TEXT PRIMARY KEY,
    category TEXT,
    drug_status TEXT,        -- 'preferred', 'non_preferred', 'not_listed'
    hcpcs TEXT,
    manufacturer TEXT,
    pa_mnd_required TEXT,    -- 'yes', 'no', 'unknown' (combined PA/MND requirement)
    notes TEXT
);

-- Create indexes
CREATE INDEX idx_drugs_category ON drugs(category);
CREATE INDEX idx_drugs_status ON drugs(drug_status);
CREATE INDEX idx_drugs_pa_mnd ON drugs(pa_mnd_required);
CREATE INDEX idx_drugs_name_lower ON drugs(LOWER(drug_name));
```

---


## Data Loading

### Prepare Your CSV Files

Place in `data/` folder:

**1. `preferred_drugs_list.csv`** - Contains category, drug status, drug name, HCPCS, and manufacturer
```csv
Category,Drug Status,Drug Name,HCPCS,Manufacturer
Oncology,Preferred,Keytruda,J9271,Merck & Co.
Immunology,Non-Preferred,Remicade,J1745,Janssen Biotech
```

**2. `pa_mnd_list.csv`** - List of drugs requiring Prior Authorization or Medical Necessity Determination
```csv
Drug Name
Keytruda
Remicade
Yervoy
```

**Note:** Any drug listed in `pa_mnd_list.csv` will be marked with `pa_mnd_required = 'yes'`. Drugs NOT in this list will be marked as `pa_mnd_required = 'no'`.

### Load Data

```bash
python ingest_data.py
```

Sample data is included for testing!

---


## Usage Examples

### Drug Status Queries
```
Is Remicade preferred?
Does Stelara require PA?
Does Keytruda require authorization?
What is the status of Neulasta?
```

### Alternatives Queries
```
What are preferred alternatives to Remicade?
Other preferred drugs like Entyvio?
Preferred immunology alternatives to Humira
```

### List/Filter Queries
```
List all preferred oncology drugs
Show drugs requiring PA/MND in immunology
All non-preferred drugs requiring authorization
Filter by oncology category
```

---


## Project Structure

```
drug_query_bot/
├── app.py                          # Main Streamlit application ⭐
├── requirements.txt                # Python dependencies
├── create_schema.py                # Database setup script
├── ingest_data.py                  # Data loading script
│
├── utils/                          # Core modules
│   ├── db.py                       # Database access layer
│   ├── fuzzy.py                    # Fuzzy matching (RapidFuzz)
│   ├── intent.py                   # Query parsing logic
│   └── llm.py                      # OpenRouter integration
│
├── config/
│   └── prompts.py                  # LLM system prompts
│
├── data/                           # Data files
│   ├── preferred_drugs_list.csv    # Sample preferred drugs
│   └── pa_mnd_list.csv             # Sample PA/MND requirements
│
└── .streamlit/
    └── secrets.toml.example        # Secrets template

  ---

  ## Architecture

  ### High-Level Flow

  1. User enters a natural language query in the Streamlit UI.
  2. The backend (Python) uses rule-based logic to parse the query and extract intent, drug names, and filters.
  3. If the query is ambiguous, the system uses an LLM (OpenRouter) to clarify intent.
  4. Drug names are matched using fuzzy logic (RapidFuzz) to handle typos.
  5. The backend queries the Supabase Postgres database for relevant drug information.
  6. The LLM formats the results into a clear, human-readable answer.
  7. The UI displays the answer and a table of raw results, with optional debug info.

  ### Component Overview

  - Streamlit UI: User interface for input and results display.
  - Intent Parsing: Rule-based and LLM fallback for query understanding.
  - Fuzzy Matching: RapidFuzz-based drug name matching.
  - Database Layer: Supabase Postgres for all drug data.
  - LLM Layer: OpenRouter for fallback intent parsing and answer formatting.

  ### Data Flow

  User Query → Intent Parsing → Fuzzy Matching → Database Query → LLM Formatting → Display

  ### Safety Layers

  - All answers are grounded in the database (no hallucination).
  - LLM is only used for intent clarification and answer formatting, never for generating new data.
  - No medical advice, clinical recommendations, or policy predictions are made.
```

---


---


## Troubleshooting

**Import Errors:**
```bash
pip install -r requirements.txt
```

**Database Connection Failed:**
- Check `DATABASE_URL` in `.streamlit/secrets.toml`
- Verify Supabase project is running
- Test connection in Supabase dashboard

**OpenRouter API Error:**
- Verify `OPENROUTER_API_KEY` is correct
- Check you have credits/quota available
- Try different model if rate limited

**No Results Found:**
- Run `python ingest_data.py` to load data
- Check data in Supabase Table Editor
- Verify drug names match database entries

**Enable Debug Mode:**
- Toggle "Enable Debug Mode" in app sidebar
- See parsed intent, fuzzy matches, and query details

---


## Dependencies

From `requirements.txt`:
- `streamlit==1.31.0` - Web UI framework
- `psycopg2-binary==2.9.9` - PostgreSQL driver
- `pandas==2.1.4` - Data manipulation
- `rapidfuzz==3.6.1` - Fuzzy string matching
- `requests==2.31.0` - HTTP requests

---


## Deployment (Streamlit Cloud)

1. **Push to GitHub** (exclude `.streamlit/secrets.toml`)
2. **Connect to Streamlit Cloud** at https://streamlit.io/cloud
3. **Select Repository** and set main file: `app.py`
4. **Add Secrets** in Advanced Settings:
   ```toml
   DATABASE_URL = "your-connection-string"
   OPENROUTER_API_KEY = "your-api-key"
   SUPABASE_URL = "your-supabase-url"
   SUPABASE_KEY = "your-anon-key"
   ```
5. **Deploy!**

---


## Safety & Limitations


### What This Tool DOES:
- Looks up drug status from official lists
- Reports PA/MND requirements accurately
- Suggests preferred alternatives
- Filters drugs by various criteria

### What This Tool DOES NOT Do:
- Provide medical advice
- Make clinical recommendations
- Predict coverage or costs
- Invent or hallucinate information
- Make policy decisions

**Always consult healthcare professionals for medical decisions.**

---


## Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Frontend | Streamlit 1.31.0 | Interactive web UI |
| Database | Supabase Postgres | Drug data storage |
| LLM | OpenRouter (Claude 3.5 Sonnet) | Query understanding & formatting |
| Fuzzy Match | RapidFuzz 3.6.1 | Typo tolerance |
| Data | Pandas 2.1.4 | Table display |

---


## Data Sources

The system merges two official lists:

1. **Preferred Medical Drugs List** - Contains:
   - Category (e.g., Oncology, Immunology)
   - Drug Status (Preferred, Non-Preferred)
   - Drug Name
   - HCPCS Code
   - Manufacturer

2. **Prior Authorization/Medical Necessity Determination Medicine List** - A combined list containing:
   - Drug Name
   - PA Required (yes/no)
   - MND Required (yes/no)

Both lists are normalized and merged into a single `drugs` table.

---


## Advanced Features

### Debug Mode
- Enable in sidebar to see:
  - Parsed intent details
  - Fuzzy match confidence
  - Database query results
  - Query classification method

### Query History
- Recent queries displayed in sidebar
- Track your lookup patterns

### Category Browser
- View all available drug categories
- Displayed in sidebar

---


## Security Best Practices

- ⚠️ **Never commit** `.streamlit/secrets.toml`
- ⚠️ Use environment variables in production
- ⚠️ Rotate API keys regularly
- ⚠️ Use Supabase Row Level Security (RLS) policies
- ⚠️ Keep dependencies updated

---


## Contributing

Contributions welcome! Please ensure:
- Code follows existing patterns
- Safety rules maintained
- No medical advice generated
- All data grounded in database
- Tests pass (if applicable)

---


## License

[Your License Here]

---


## Acknowledgments

Built according to ultra-detailed specifications for safety, reliability, and intelligent drug information lookup.

Built with precision. Deployed with confidence.
