# Getting Your Supabase API Credentials

To connect to Supabase using the API (required for Streamlit Cloud deployment), you need two values:

## 1. SUPABASE_URL
Your project URL in the format: `https://your-project-id.supabase.co`

**Where to find it:**
1. Go to https://app.supabase.com
2. Select your project
3. Go to **Settings** (gear icon in sidebar)
4. Click **API**
5. Find **Project URL** - copy this value


## 2. SUPABASE_KEY (anon/public key)
This is a long JWT token that starts with `eyJ...`

**Where to find it:**
1. In the same **Settings → API** page
2. Look for **Project API keys**
3. Copy the **anon** **public** key (NOT the service_role key)
4. It should be a very long string starting with `eyJ`


## 3. Update your secrets.toml

Once you have both values, update `.streamlit/secrets.toml`:

```toml
# Supabase Configuration
SUPABASE_URL = "https://your-project-id.supabase.co"
SUPABASE_KEY = "eyJhbGci...your-very-long-anon-key..."

# OpenRouter API Key
OPENROUTER_API_KEY = "sk-or-v1-your-api-key-here"
```

## 4. For Streamlit Cloud Deployment

When deploying to Streamlit Cloud:
1. Go to your app settings
2. Navigate to **Secrets**
3. Paste the same content from your `secrets.toml` file
4. Save

## Security Notes

- ✅ The **anon/public** key is safe to use in client-side code
- ❌ NEVER use the **service_role** key in your app (it has full admin access)
- The anon key respects your Supabase Row Level Security (RLS) policies
