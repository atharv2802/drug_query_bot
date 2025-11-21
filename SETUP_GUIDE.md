# Drug Query Bot - First Time Setup Guide

This guide will walk you through setting up the Drug Query Bot project from scratch.

---

## Prerequisites

Before you begin, ensure you have:
- **Python 3.11.9** installed (download from https://www.python.org/downloads/release/python-3119/)
- **Git** (if cloning from repository)
- A **Supabase account** (free tier works fine)
- An **OpenRouter API account** (for LLM access)

---

## Step 1: Install Python Dependencies

1. Open PowerShell/Terminal and navigate to the project directory:
```powershell
cd d:\drug_query_bot
```

2. (Recommended) Create a virtual environment with Python 3.11.9:
```powershell
python3.11 -m venv drug_query_bot
.\drug_query_bot\Scripts\Activate.ps1
```
If your Python 3.11.9 executable is named differently, use its full path:
```powershell
C:\Path\To\python3.11.exe -m venv drug_query_bot
.\drug_query_bot\Scripts\Activate.ps1
```

3. Install required packages:
```powershell
pip install -r requirements.txt
```

---

## Step 2: Set Up Supabase Database

### 2.1 Create Supabase Project

1. Go to [https://supabase.com](https://supabase.com)
2. Sign up or log in
3. Click **"New Project"**
4. Fill in:
   - **Project Name**: drug-query-bot (or any name you prefer)
   - **Database Password**: Choose a strong password (save this!)
   - **Region**: Select closest to you
5. Click **"Create new project"** and wait for it to initialize (~2 minutes)

### 2.2 Get Database Connection String

1. In your Supabase project dashboard, go to **Settings** → **Database**
2. Scroll down to **Connection String** section
3. Select **URI** format
4. Copy the connection string - it looks like:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.xxxxxxxxxxxxx.supabase.co:5432/postgres
   ```
5. Replace `[YOUR-PASSWORD]` with your actual database password

---

## Step 3: Set Up OpenRouter API

### 3.1 Get OpenRouter API Key

1. Go to [https://openrouter.ai](https://openrouter.ai)
2. Sign up or log in
3. Go to **Keys** section (top right menu)
4. Click **"Create Key"**
5. Copy the API key (starts with `sk-or-v1-...`)

---

## Step 4: Configure Secrets

### 4.1 Create Secrets File

1. Navigate to the `.streamlit` folder
2. Create a new file named `secrets.toml` (copy from `secrets.toml.example`)
3. Open `secrets.toml` in a text editor

### 4.2 Add Your Credentials

Paste the following and replace with your actual values:

```toml
DATABASE_URL = "postgresql://postgres:your-password@db.xxxxx.supabase.co:5432/postgres"
OPENROUTER_API_KEY = "sk-or-v1-your-api-key-here"
SUPABASE_URL = "https://xxxxx.supabase.co"
SUPABASE_KEY = "your-supabase-anon-key"
```

**Important**: All values must be in double quotes!

### 4.3 Get Supabase URL and Key (Optional)

If you need `SUPABASE_URL` and `SUPABASE_KEY`:
1. In Supabase dashboard, go to **Settings** → **API**
2. Copy **Project URL** → paste as `SUPABASE_URL`
3. Copy **anon public** key → paste as `SUPABASE_KEY`

---

## Step 5: Create Database Schema

Run the schema creation script:

```powershell
python create_schema.py
```

When prompted, enter your `DATABASE_URL` (the same one from secrets.toml).

You should see:
```
Creating drugs table...
Creating indexes...
Database schema created successfully!

Table Structure:
   drug_name: text
   category: text
   drug_status: text
   hcpcs: text
   manufacturer: text
   pa_mnd_required: text
   notes: text
```

---

## Step 6: Load Sample Data

### 6.1 Verify CSV Files

Check that you have these files in the `data/` folder:
- `preferred_drugs_list.csv`
- `pa_mnd_list.csv`

### 6.2 Run Data Ingestion

```powershell
python ingest_data.py
```

Or with custom CSV paths and database URL:
```powershell
python ingest_data.py --preferred_csv data/preferred_drugs_list.csv --pa_mnd_csv data/pa_mnd_list.csv --db_url "your-database-url"
```

You should see:
```
Loading Preferred Medical Drugs List from data/preferred_drugs_list.csv...
   Loaded 16 drugs
Loading PA/MND Medicine List from data/pa_mnd_list.csv...
   Loaded 16 PA/MND entries
Merging data...
   Final dataset: 16 drugs
Inserting into database...
Successfully inserted 16 drugs into database
Data ingestion complete!
```

---

## Step 7: Run the Application

Start the Streamlit app:

```powershell
streamlit run app.py
```

The app will automatically open in your browser at:
```
http://localhost:8501
```

---

## Step 8: Test the Application

Try these example queries:

1. **Drug Status Query**:
   - "Is Keytruda preferred?"
   - "Does Remicade require PA?"

2. **Alternatives Query**:
   - "What are preferred alternatives to Remicade?"

3. **List/Filter Query**:
   - "List all preferred oncology drugs"
   - "Show drugs requiring PA/MND"

---

## Troubleshooting

### Issue: Database Connection Failed
- **Solution**: Check your `DATABASE_URL` in `.streamlit/secrets.toml`
- Verify your Supabase project is running
- Ensure password is correct (no special characters unescaped)

### Issue: OpenRouter API Error
- **Solution**: Verify `OPENROUTER_API_KEY` in secrets.toml
- Check you have API credits available at OpenRouter
- Try a different model if rate limited

### Issue: No Results Found
- **Solution**: Run `python ingest_data.py` to load data
- Check data exists in Supabase Table Editor
- Verify drug names match database entries

### Issue: Import Errors
- **Solution**: Run `pip install -r requirements.txt`
- Ensure you're in the project directory
- Use Python 3.9 or higher

### Issue: Secrets File Not Found
- **Solution**: Create `.streamlit/secrets.toml` (note the dot before streamlit)
- Copy from `secrets.toml.example`
- Ensure file is in the correct location

---

## Running Tests (Optional)

To run the test suite:

```powershell
# Run all tests
pytest

# Run with coverage report
pytest --cov=utils --cov=config --cov-report=html

# Run specific test file
pytest tests/test_fuzzy.py
```

---

## Next Steps

- **Add your own data**: Replace CSV files in `data/` folder with your organization's drug lists
- **Customize categories**: Update `CATEGORY_KEYWORDS` in `utils/intent.py`
- **Adjust LLM model**: Change model in `utils/llm.py` (currently using `meta-llama/llama-3-70b-instruct`)
- **Deploy to Streamlit Cloud**: Follow deployment guide in README.md

---

## Project Structure Reference

```
drug_query_bot/
├── app.py                          # Main Streamlit application
├── requirements.txt                # Python dependencies
├── create_schema.py                # Database setup script
├── ingest_data.py                  # Data loading script
├── pytest.ini                      # Test configuration
│
├── .streamlit/
│   ├── secrets.toml               # Your credentials (DO NOT COMMIT)
│   └── secrets.toml.example       # Template for secrets
│
├── utils/                          # Core modules
│   ├── db.py                       # Database access layer
│   ├── fuzzy.py                    # Fuzzy matching
│   ├── intent.py                   # Query parsing
│   └── llm.py                      # OpenRouter integration
│
├── config/
│   └── prompts.py                  # LLM system prompts
│
├── data/                           # Data files
│   ├── preferred_drugs_list.csv    # Drug categorization
│   └── pa_mnd_list.csv             # PA/MND requirements
│
└── tests/                          # Test suite
    ├── test_fuzzy.py
    ├── test_intent.py
    ├── test_db.py
    └── test_llm.py
```

---

## Environment Variables (Alternative to Secrets)

Instead of `.streamlit/secrets.toml`, you can also set environment variables:

```powershell
# PowerShell
$env:DATABASE_URL = "postgresql://..."
$env:OPENROUTER_API_KEY = "sk-or-v1-..."

# Then run
streamlit run app.py
```

---

## Security Reminders

⚠️ **Important Security Notes**:
- Never commit `.streamlit/secrets.toml` to version control
- Keep your API keys private
- Rotate API keys regularly
- Use Supabase Row Level Security (RLS) policies in production
- Keep dependencies updated

---

## Support & Resources

- **Supabase Docs**: https://supabase.com/docs
- **OpenRouter Docs**: https://openrouter.ai/docs
- **Streamlit Docs**: https://docs.streamlit.io
- **Project README**: See `README.md` for detailed documentation

---

**You're all set! 🚀**

If you encounter any issues, check the Troubleshooting section above or review the main README.md file.
