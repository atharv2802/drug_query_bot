# 🛠️ Drug Query Bot - Setup Guide

Complete installation and configuration guide for running the Drug Query Bot locally.

---

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Database Setup](#database-setup)
- [Configuration](#configuration)
- [Data Pipeline](#data-pipeline)
- [Running the Application](#running-the-application)
- [Running Tests](#running-tests)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)

---

## ✅ Prerequisites

### Required Software

1. **Python 3.9 or higher**
   ```bash
   python --version  # Should be 3.9+
   ```

2. **Git**
   ```bash
   git --version
   ```

3. **pip** (Python package manager)
   ```bash
   pip --version
   ```

### Required Accounts

1. **Supabase** (PostgreSQL database hosting)
   - Sign up: [https://supabase.com](https://supabase.com)
   - Free tier is sufficient

2. **OpenRouter** (LLM API access)
   - Sign up: [https://openrouter.ai](https://openrouter.ai)
   - Free credits available, pay-as-you-go pricing

---

## 📥 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/atharv2802/drug_query_bot.git
cd drug_query_bot
```

### 2. Create Virtual Environment (Recommended)

**Windows:**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Mac/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

**Dependencies installed:**
- `streamlit==1.31.0` - Web UI framework
- `supabase==2.10.0` - Database client
- `pandas==2.1.4` - Data manipulation
- `rapidfuzz==3.6.1` - Fuzzy matching
- `requests==2.31.0` - HTTP client
- `beautifulsoup4` - HTML parsing
- `fastapi==0.109.0` - REST API
- `uvicorn[standard]==0.27.0` - ASGI server
- `pytest==7.4.3` - Testing framework

---

## 🗄️ Database Setup

### 1. Create Supabase Project

1. Go to [https://supabase.com/dashboard](https://supabase.com/dashboard)
2. Click **New Project**
3. Fill in details:
   - **Name:** drug-query-bot
   - **Database Password:** (choose a strong password)
   - **Region:** Select closest to you
4. Click **Create new project** (takes ~2 minutes)

### 2. Get Database Credentials

1. In Supabase dashboard, go to **Settings** → **Database**
2. Scroll to **Connection String** section
3. Copy the **URI** (looks like: `postgresql://postgres:[YOUR-PASSWORD]@db.xxx.supabase.co:5432/postgres`)
4. Also note:
   - **Project URL**: `https://xxx.supabase.co`
   - **API Keys** → **anon public**: `eyJ...` (for public access)
   - **API Keys** → **service_role**: `eyJ...` (for admin access)

### 3. Test Database Connection

```bash
# Should return version info
python -c "import psycopg2; print('PostgreSQL connection available')"
```

---

## ⚙️ Configuration

### 1. Create Secrets File

Create `.streamlit/secrets.toml` in the project root:

```bash
mkdir .streamlit
```

**Windows:**
```powershell
New-Item -Path ".streamlit\secrets.toml" -ItemType File
```

**Mac/Linux:**
```bash
touch .streamlit/secrets.toml
```

### 2. Add Configuration

Edit `.streamlit/secrets.toml` and add:

```toml
# Supabase Configuration
SUPABASE_URL = "https://xxx.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."  # anon public key

# PostgreSQL Direct Connection (for schema creation and ingestion)
DATABASE_URL = "postgresql://postgres:[PASSWORD]@db.xxx.supabase.co:5432/postgres"

# OpenRouter API Key
OPENROUTER_API_KEY = "sk-or-v1-..."

# Optional: Site URL and App Name (for OpenRouter)
SITE_URL = "https://drugquerybot.streamlit.app"
APP_NAME = "Drug Query Bot"
```

**⚠️ Security Notes:**
- **NEVER commit** `.streamlit/secrets.toml` to Git (already in `.gitignore`)
- Use **environment variables** for production deployment
- Rotate keys if accidentally exposed

### 3. Verify Configuration

```bash
python -c "from utils.db import get_supabase_client; print('Supabase connection successful')"
```

---

## 🔄 Data Pipeline

### 1. Create Database Schema

```bash
python create_schema.py
```

**What it does:**
- Drops existing `drugs` table (if any)
- Creates new table with composite primary key `(drug_name, category)`
- Adds indexes on `drug_name`, `category`, `drug_status`, `hcpcs`, `pa_mnd_required`

**Expected output:**
```
============================================================
CREATING FRESH SCHEMA WITH COMPOSITE PRIMARY KEY
============================================================

[1/3] Dropping existing table (if any)...
   ✓ Old table dropped

[2/3] Creating drugs table with composite key (drug_name, category)...
   ✓ Table created

[3/3] Creating indexes for query performance...
   ✓ Index created: idx_drugs_name
   ✓ Index created: idx_drugs_category
   ✓ Index created: idx_drugs_status
   ✓ Index created: idx_drugs_hcpcs
   ✓ Index created: idx_drugs_pa_mnd

============================================================
SCHEMA CREATION COMPLETE
============================================================
```

### 2. Scrape Drug Data

```bash
python scraper/scrape_drugs.py
```

**What it does:**
- Fetches HTML from Horizon BCBS website
- Parses preferred drugs list (8 categories)
- Parses PA/MND requirements list
- Saves to `drugs_rows.csv`

**Expected output:**
```
Fetching Preferred Drugs HTML...
Parsing Preferred Drugs...
Fetching PA/MND HTML...
Parsing PA/MND Requirements...

Total unique drugs scraped: 2000+
Output saved to: drugs_rows.csv
```

**CSV Format:**
```csv
Drug Name,Category,Drug Status,HCPCS,Manufacturer,Notes
avastin,Ophthalmic Injections,preferred,J9035,Genentech,
avastin,Oncology/Bevacizumab,non_preferred,J9035,Genentech,
humira,Immunology,non_preferred,J0135,AbbVie,PA required
...
```

### 3. Ingest Data into Database

```bash
python ingest_data.py
```

**What it does:**
- Loads `drugs_rows.csv`
- Loads `data/preferred_drugs_list.csv` (if exists)
- Loads `data/pa_mnd_list.csv` (if exists)
- Merges data with composite key handling
- Upserts to Supabase (ON CONFLICT update)

**Expected output:**
```
Loading CSV data...
Loaded 2000+ drug-category rows

Merging data sources...
Merged successfully

Inserting into database...
[================] 100% (2000/2000)

SUCCESS: Inserted/Updated 2000+ rows
```

### 4. Verify Data

```bash
python -c "from utils.db import fetch_all_drug_names; print(f'Total drugs: {len(fetch_all_drug_names())}')"
```

**Expected:** `Total drugs: 2000+`

---

## 🚀 Running the Application

### Option 1: Streamlit Web App (Recommended)

```bash
streamlit run app.py
```

**Access:** Opens automatically in browser at [http://localhost:8501](http://localhost:8501)

**Features:**
- Natural language query interface
- Autocomplete search
- Query history
- Debug mode (toggle in sidebar)
- Markdown-formatted responses

### Option 2: FastAPI REST API

```bash
uvicorn api:app --reload --port 8000
```

**Access:**
- **API:** [http://localhost:8000](http://localhost:8000)
- **Swagger Docs:** [http://localhost:8000/api/docs](http://localhost:8000/api/docs)
- **ReDoc:** [http://localhost:8000/api/redoc](http://localhost:8000/api/redoc)

**Example API Request:**
```bash
curl -X POST "http://localhost:8000/api/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "Is Humira preferred?"}'
```

### Option 3: Run Both (Different Terminals)

**Terminal 1:**
```bash
streamlit run app.py
```

**Terminal 2:**
```bash
uvicorn api:app --reload --port 8000
```

---

## 🧪 Running Tests

### Run All Tests

```bash
pytest
```

### Run Specific Test Files

```bash
pytest tests/test_db.py          # Database tests
pytest tests/test_intent.py      # Intent parsing tests
pytest tests/test_fuzzy.py       # Fuzzy matching tests
pytest tests/test_api.py         # API endpoint tests
```

### Run with Coverage

```bash
pytest --cov=utils --cov=config --cov-report=html
```

**View coverage report:** Open `htmlcov/index.html` in browser

### Run Single Query Test

```bash
python tests/test_single_query.py "Is Avastin preferred?"
```

---

## 🌐 Deployment

### Streamlit Cloud (Recommended for Web App)

1. **Push code to GitHub:**
   ```bash
   git add .
   git commit -m "Initial deployment"
   git push origin main
   ```

2. **Deploy to Streamlit Cloud:**
   - Go to [https://streamlit.io/cloud](https://streamlit.io/cloud)
   - Click **New app**
   - Select your GitHub repository
   - Set **Main file path:** `app.py`
   - Click **Advanced settings** → **Secrets**
   - Copy contents of `.streamlit/secrets.toml`
   - Click **Deploy**

3. **Your app will be live at:** `https://your-app-name.streamlit.app`

### Heroku (For FastAPI)

1. **Create `Procfile`:**
   ```
   web: uvicorn api:app --host=0.0.0.0 --port=${PORT:-8000}
   ```

2. **Create `runtime.txt`:**
   ```
   python-3.9.18
   ```

3. **Deploy:**
   ```bash
   heroku create drug-query-api
   heroku config:set SUPABASE_URL="..." SUPABASE_KEY="..." OPENROUTER_API_KEY="..."
   git push heroku main
   ```

### Environment Variables (Production)

Set these in your hosting platform:

```bash
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJ...
DATABASE_URL=postgresql://...
OPENROUTER_API_KEY=sk-or-v1-...
SITE_URL=https://your-domain.com
APP_NAME=Drug Query Bot
```

---

## 🔧 Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'supabase'"

**Solution:**
```bash
pip install -r requirements.txt
```

### Issue: "Supabase client initialization failed"

**Causes:**
1. Missing or incorrect credentials in `.streamlit/secrets.toml`
2. Incorrect `SUPABASE_URL` or `SUPABASE_KEY`

**Solution:**
1. Verify credentials in Supabase dashboard
2. Check `.streamlit/secrets.toml` format (TOML syntax)
3. Ensure no extra spaces or quotes

### Issue: "Failed to fetch drug names"

**Causes:**
1. Database table doesn't exist
2. Network connectivity issues

**Solution:**
1. Run `python create_schema.py` first
2. Run `python ingest_data.py` to populate data
3. Check internet connection

### Issue: "OpenRouter API error: 401 Unauthorized"

**Causes:**
1. Invalid API key
2. API key not set in secrets

**Solution:**
1. Verify API key at [https://openrouter.ai/keys](https://openrouter.ai/keys)
2. Check `.streamlit/secrets.toml` has `OPENROUTER_API_KEY`
3. Ensure no extra whitespace in key

### Issue: Scraper returns empty data

**Causes:**
1. Horizon website structure changed
2. Network/firewall blocking requests

**Solution:**
1. Check if website is accessible: [Horizon BCBS Formulary](https://www.horizonblue.com/providers/products-programs/pharmacy/pharmacy-programs/preferred-medical-drugs)
2. Update scraper selectors if HTML changed
3. Try with VPN if blocked

### Issue: Streamlit shows "Connection Error"

**Solution:**
```bash
# Kill existing processes
pkill -f streamlit

# Restart
streamlit run app.py
```

### Issue: Database ingestion fails with duplicate key error

**Explanation:** Composite primary key `(drug_name, category)` prevents duplicates

**Solution:**
- This is expected behavior
- Script uses `ON CONFLICT ... DO UPDATE` to handle duplicates
- Re-run `python ingest_data.py` safely

### Issue: Tests fail with "No module named 'pytest'"

**Solution:**
```bash
pip install pytest pytest-mock pytest-cov
```

---

## 📞 Support

For issues not covered here:

1. **Check existing issues:** GitHub Issues (if repository is public)
2. **Review logs:** Check terminal output for detailed error messages
3. **Verify configuration:** Double-check all credentials and file paths
4. **Test components individually:**
   ```bash
   python -c "from utils.db import get_supabase_client; get_supabase_client()"
   python -c "from utils.llm import call_openrouter; print('OpenRouter OK')"
   ```

---

## 🔄 Updating Data

To refresh drug data from the source website:

```bash
# 1. Scrape latest data
python scraper/scrape_drugs.py

# 2. Re-ingest (will update existing records)
python ingest_data.py
```

**Note:** No need to re-run `create_schema.py` unless schema changes.

---

## 🎓 Development Workflow

1. **Make changes** to code
2. **Run tests:** `pytest`
3. **Test locally:** `streamlit run app.py`
4. **Commit:** `git commit -m "Description"`
5. **Push:** `git push origin main`
6. **Deploy:** Streamlit Cloud auto-deploys from GitHub

---

**Setup complete! 🎉**

You should now have:
- ✅ Database schema created
- ✅ Data scraped and ingested
- ✅ Application running locally
- ✅ Tests passing

**Next:** Try queries like "Is Avastin preferred?" or "Alternatives to Humira"
