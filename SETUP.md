# 🛠️ Setup Guide - Drug Query Bot

Complete installation and deployment guide for local development and cloud deployment.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development Setup](#local-development-setup)
3. [Database Configuration](#database-configuration)
4. [API Keys Setup](#api-keys-setup)
5. [Data Ingestion](#data-ingestion)
6. [Running Tests](#running-tests)
7. [Deployment to Streamlit Cloud](#deployment-to-streamlit-cloud)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software
- **Python 3.11+** (recommended: 3.11.9)
- **Git** for version control
- **pip** (comes with Python)

### Required Accounts
- **Supabase** account (free tier): https://supabase.com
- **OpenRouter** account (pay-as-you-go): https://openrouter.ai
- **GitHub** account (for deployment): https://github.com
- **Streamlit Cloud** account (free): https://streamlit.io/cloud

---

## Local Development Setup

### 1. Clone the Repository

```bash
git clone https://github.com/atharv2802/drug_query_bot.git
cd drug_query_bot
```

### 2. Create Virtual Environment

**Windows:**
```powershell
python -m venv drug_query_bot
.\drug_query_bot\Scripts\Activate.ps1
```

**Linux/Mac:**
```bash
python3 -m venv drug_query_bot
source drug_query_bot/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

**Dependencies installed:**
- `streamlit==1.31.0` - Web UI framework
- `supabase==2.10.0` - Database client
- `websockets>=15.0` - Required for Supabase realtime
- `pandas==2.1.4` - Data manipulation
- `rapidfuzz==3.6.1` - Fuzzy string matching
- `requests==2.31.0` - HTTP client
- `beautifulsoup4` - Web scraping
- `pytest==7.4.3` - Testing framework

---

## Database Configuration

### Step 1: Create Supabase Project

1. Go to https://supabase.com and sign up/login
2. Click **"New Project"**
3. Fill in:
   - **Name**: drug-query-bot
   - **Database Password**: (save this securely)
   - **Region**: Choose closest to you
4. Wait for project to be created (~2 minutes)

### Step 2: Get Supabase Credentials

1. In your project dashboard, go to **Settings** (gear icon) → **API**
2. Copy these values:
   - **Project URL** (e.g., `https://xxxxx.supabase.co`)
   - **anon/public key** (starts with `eyJ...`) - **NOT** the service_role key

### Step 3: Create Database Schema

1. In Supabase dashboard, go to **SQL Editor**
2. Click **"New Query"**
3. Paste this SQL:

```sql
CREATE TABLE IF NOT EXISTS drugs (
    drug_name TEXT PRIMARY KEY,
    category TEXT,
    drug_status TEXT,
    hcpcs TEXT,
    manufacturer TEXT,
    pa_mnd_required TEXT,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_drugs_category ON drugs(category);
CREATE INDEX IF NOT EXISTS idx_drugs_status ON drugs(drug_status);
CREATE INDEX IF NOT EXISTS idx_drugs_pa_mnd ON drugs(pa_mnd_required);
CREATE INDEX IF NOT EXISTS idx_drugs_name_lower ON drugs(LOWER(drug_name));
```

4. Click **Run** to execute

**Alternative (using Python script):**
```bash
# Requires psycopg2 and direct DATABASE_URL connection
python create_schema.py
```

---

## API Keys Setup

### Step 1: Get OpenRouter API Key

1. Go to https://openrouter.ai and sign up/login
2. Navigate to **Keys** section or https://openrouter.ai/keys
3. Click **"Create Key"**
4. Name it `Drug Query Bot`
5. Copy the generated key (starts with `sk-or-v1-`)
6. **Add credits**: Go to **Credits** section and add at least $5

### Step 2: Configure Secrets File

1. Navigate to `.streamlit/` directory
2. Copy the example file:
   ```bash
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml
   ```

3. Edit `.streamlit/secrets.toml`:
   ```toml
   # Supabase Configuration
   SUPABASE_URL = "https://your-project-id.supabase.co"
   SUPABASE_KEY = "eyJhbGci...your-anon-key..."

   # OpenRouter API Key
   OPENROUTER_API_KEY = "sk-or-v1-your-key-here"
   ```

4. Save the file

**⚠️ Important**: Never commit `secrets.toml` to Git! It's already in `.gitignore`.

---

## Data Ingestion

### Option 1: Use Existing CSV Files

The repository includes pre-scraped data in `data/` directory:
- `preferred_drugs_list.csv` (1000+ drugs)
- `pa_mnd_list.csv` (PA/MND requirements)

**Ingest into database:**

1. Make sure your `.streamlit/secrets.toml` is configured
2. Run the ingestion script:
   ```bash
   python ingest_data.py
   ```

3. Verify data:
   - Go to Supabase dashboard → **Table Editor**
   - Check the `drugs` table has ~1000 rows

### Option 2: Scrape Fresh Data

If you want to scrape latest data from Horizon Blue Cross:

```bash
cd scraper
python scrape_drugs.py
```

This will:
- Fetch HTML pages from formulary website
- Parse with BeautifulSoup4
- Generate updated CSV files in `data/` directory
- Run `python ingest_data.py` to load into database

---

## Running Tests

### Run All Tests

```bash
pytest
```

### Run Specific Test Suites

```bash
# Database tests
pytest tests/test_db.py -v

# Intent parsing tests
pytest tests/test_intent.py -v

# LLM integration tests
pytest tests/test_llm.py -v

# Fuzzy matching tests
pytest tests/test_fuzzy.py -v

# Full pipeline test
pytest tests/test_full_pipeline_supabase.py -v

# Supabase connection test
python tests/test_supabase_connection.py
```

### Run with Coverage

```bash
pytest --cov=. --cov-report=html
# Open htmlcov/index.html in browser to see coverage report
```

---

## Deployment to Streamlit Cloud

### Step 1: Push to GitHub

```bash
git add .
git commit -m "Initial commit"
git push origin main
```

### Step 2: Deploy on Streamlit Cloud

1. Go to https://streamlit.io/cloud
2. Sign in with GitHub
3. Click **"New app"**
4. Fill in:
   - **Repository**: `your-username/drug_query_bot`
   - **Branch**: `main`
   - **Main file path**: `app.py`
5. Click **"Advanced settings"**
6. Add **Secrets** (paste contents of your `.streamlit/secrets.toml`):
   ```toml
   SUPABASE_URL = "https://your-project-id.supabase.co"
   SUPABASE_KEY = "eyJhbGci...your-anon-key..."
   OPENROUTER_API_KEY = "sk-or-v1-your-key-here"
   ```
7. Click **"Deploy"**
8. Wait for deployment (~5 minutes)

### Step 3: Verify Deployment

1. Once deployed, you'll get a URL like `https://your-app.streamlit.app`
2. Test with sample queries:
   - "Is Remicade preferred?"
   - "What are the alternatives to Humira?"
   - "List all non-preferred drugs in Antiemetics category"

---

## Running the Application

### Local Development

```bash
# Activate virtual environment (if not already active)
.\drug_query_bot\Scripts\Activate.ps1  # Windows
source drug_query_bot/bin/activate      # Linux/Mac

# Start the app
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

---

## Troubleshooting

### Issue: "Database connection failed"

**Solution:**
1. Verify Supabase project is active (not paused)
2. Check `SUPABASE_URL` and `SUPABASE_KEY` in secrets.toml
3. Ensure you're using the **anon key**, not service_role key
4. Test connection: `python tests/test_supabase_connection.py`

### Issue: "OpenRouter API error: 401 Unauthorized"

**Solution:**
1. Check if your OpenRouter API key is valid
2. Verify you have credits in your OpenRouter account
3. Regenerate key if expired: https://openrouter.ai/keys
4. Update `OPENROUTER_API_KEY` in secrets.toml

### Issue: "No module named 'websockets.asyncio'"

**Solution:**
```bash
pip install --upgrade websockets
```

### Issue: "ModuleNotFoundError: No module named 'supabase'"

**Solution:**
```bash
pip install -r requirements.txt --upgrade
```

### Issue: App runs but queries return no results

**Solution:**
1. Verify data is ingested: Check Supabase Table Editor
2. Run ingestion: `python ingest_data.py`
3. Check database schema: `python create_schema.py`

### Issue: "streamlit: command not found"

**Solution:**
1. Ensure virtual environment is activated
2. Reinstall streamlit: `pip install streamlit`

---

## Environment Variables (Alternative to secrets.toml)

For CI/CD or Docker deployments, you can use environment variables:

```bash
export SUPABASE_URL="https://your-project-id.supabase.co"
export SUPABASE_KEY="eyJhbGci...your-anon-key..."
export OPENROUTER_API_KEY="sk-or-v1-your-key-here"
```

The app will automatically detect and use these if `secrets.toml` is not present.

---

## Performance Optimization

### For Large Datasets (10,000+ drugs)

1. **Enable caching in Streamlit:**
   - Already implemented with `@st.cache_data`

2. **Database optimization:**
   ```sql
   -- Add more indexes if needed
   CREATE INDEX idx_drugs_manufacturer ON drugs(manufacturer);
   CREATE INDEX idx_drugs_hcpcs ON drugs(hcpcs);
   ```

3. **Connection pooling:**
   - Supabase client handles this automatically

---

## Updating the Application

### Update Dependencies

```bash
pip install -r requirements.txt --upgrade
```

### Update Database Schema

```bash
python create_schema.py  # Creates new tables/indexes
```

### Re-ingest Data

```bash
python ingest_data.py  # Refreshes all data
```

---

## Security Best Practices

✅ **DO:**
- Use environment variables or secrets.toml for API keys
- Use Supabase **anon key** (not service_role key)
- Enable Row Level Security (RLS) in Supabase for production
- Rotate API keys regularly
- Use HTTPS for all deployments

❌ **DON'T:**
- Commit secrets.toml to Git
- Share API keys publicly
- Use service_role key in client-side code
- Hardcode credentials in source code

---

## Additional Resources

- **Streamlit Docs**: https://docs.streamlit.io
- **Supabase Docs**: https://supabase.com/docs
- **OpenRouter Docs**: https://openrouter.ai/docs
- **RapidFuzz Docs**: https://rapidfuzz.github.io/RapidFuzz/

---

## Need Help?

- **GitHub Issues**: https://github.com/atharv2802/drug_query_bot/issues
- **Email**: (your-email@example.com)

---

**Setup complete! 🎉 Your Drug Query Bot is ready to use.**
