"""
Create fresh database schema for drug_query_bot.

This script creates the drugs table with composite primary key (drug_name, category).
Run this AFTER deleting the old table in Supabase.

Schema:
- drug_name + category: Composite PRIMARY KEY
- drug_name: TEXT - Drug name
- category: TEXT - Single category (one row per drug-category combination)
- drug_status: TEXT - preferred | non_preferred | not_listed (can vary by category)
- hcpcs: TEXT - HCPCS billing code
- manufacturer: TEXT - Drug manufacturer
- pa_mnd_required: TEXT - yes | no | unknown (Prior Auth/Medical Necessity)
- notes: TEXT - Additional notes

Indexes:
- B-tree indexes on drug_name, category, drug_status for efficient queries

NOTE: This schema allows a drug to have different statuses in different categories.
Each drug-category combination is a separate row.
"""
import psycopg2
import sys
import os


def create_schema(database_url: str):
    """
    Create the drugs table with composite primary key (drug_name, category).
    
    Args:
        database_url: PostgreSQL connection string
    """
    conn = psycopg2.connect(database_url)
    
    try:
        with conn.cursor() as cur:
            print("=" * 60)
            print("CREATING FRESH SCHEMA WITH COMPOSITE PRIMARY KEY")
            print("=" * 60)
            
            # Drop table if exists
            print("\n[1/3] Dropping existing table (if any)...")
            cur.execute("DROP TABLE IF EXISTS drugs CASCADE")
            conn.commit()
            print("   ✓ Old table dropped")
            
            # Create table with composite primary key
            print("\n[2/3] Creating drugs table with composite key (drug_name, category)...")
            cur.execute("""
                CREATE TABLE drugs (
                    drug_name TEXT,
                    category TEXT,
                    drug_status TEXT,
                    hcpcs TEXT,
                    manufacturer TEXT,
                    pa_mnd_required TEXT DEFAULT 'no',
                    notes TEXT,
                    PRIMARY KEY (drug_name, category)
                )
            """)
            conn.commit()
            print("   ✓ Table created with composite PRIMARY KEY (drug_name, category)")
            
            # Create indexes for better performance
            print("\n[3/3] Creating indexes...")
            
            # Index on drug_name for name lookups
            cur.execute("""
                CREATE INDEX idx_drugs_name 
                ON drugs (drug_name)
            """)
            
            # Index on category for category filters
            cur.execute("""
                CREATE INDEX idx_drugs_category 
                ON drugs (category)
            """)
            
            # Index on drug_status for filtering
            cur.execute("""
                CREATE INDEX idx_drugs_status 
                ON drugs (drug_status)
            """)
            
            # Index on pa_mnd_required for filtering
            cur.execute("""
                CREATE INDEX idx_drugs_pa_mnd 
                ON drugs (pa_mnd_required)
            """)
            
            # Index on hcpcs for code lookups
            cur.execute("""
                CREATE INDEX idx_drugs_hcpcs
                ON drugs (hcpcs)
            """)
            
            # Index for case-insensitive drug name search
            cur.execute("""
                CREATE INDEX idx_drugs_name_lower
                ON drugs(LOWER(drug_name))
            """)
            
            conn.commit()
            print("   ✓ Indexes created")
            
            # Verify schema
            print("\n[VERIFICATION] Schema created successfully:")
            cur.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'drugs'
                ORDER BY ordinal_position
            """)
            
            print("\n   Columns:")
            for row in cur.fetchall():
                print(f"     - {row[0]}: {row[1]}")
            
            cur.execute("""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = 'drugs'
            """)
            
            print("\n   Indexes:")
            for row in cur.fetchall():
                print(f"     - {row[0]}")
            
            print("\n" + "=" * 60)
            print("✓ SCHEMA CREATED SUCCESSFULLY")
            print("=" * 60)
            print("\nNext steps:")
            print("  1. Run: python scraper/scrape_drugs.py")
            print("  2. Run: python ingest_data.py --db_url 'your_url'")
    
    except Exception as e:
        conn.rollback()
        print(f"\n✗ ERROR: {str(e)}")
        sys.exit(1)


def get_database_url():
    """Get database URL from various sources."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Create fresh database schema")
    parser.add_argument('--db_url', type=str, default=None, help="Database URL")
    args = parser.parse_args()
    
    # Try CLI argument first
    if args.db_url:
        return args.db_url
    
    # Try environment variable
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        return db_url
    
    # Try Streamlit secrets
    try:
        import streamlit as st
        db_url = st.secrets.get("DATABASE_URL")
        if db_url:
            return db_url
    except:
        pass
    
    # Try to read from .streamlit/secrets.toml
    secrets_path = os.path.join(os.path.dirname(__file__), '.streamlit', 'secrets.toml')
    if os.path.exists(secrets_path):
        with open(secrets_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip().startswith('DATABASE_URL'):
                    # Parse line: DATABASE_URL = "..."
                    value = line.split('=', 1)[1].strip().strip('"')
                    if value:
                        return value
    
    return None


def main():
    """Main entry point."""
    DATABASE_URL = get_database_url()
    
    if not DATABASE_URL:
        print("Error: DATABASE_URL must be provided via --db_url, environment variable, or Streamlit secrets.")
        sys.exit(1)
    
    # Confirm before proceeding
    print("\n⚠️  WARNING: This will DROP the existing 'drugs' table if it exists!")
    print("⚠️  All data will be lost. Make sure you have a backup if needed.\n")
    
    confirm = input("Type 'YES' to proceed: ")
    if confirm != 'YES':
        print("Aborted.")
        sys.exit(0)
    
    create_schema(DATABASE_URL)


if __name__ == "__main__":
    main()
