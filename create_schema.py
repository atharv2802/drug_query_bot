"""
Utility script to create the database schema.

Creates a unified drugs table that merges:
1. Preferred Medical Drugs List (category, status, HCPCS, manufacturer)
2. Prior Authorization/Medical Necessity Determination List (PA/MND requirements)

Run this before data ingestion.

NOTE: This script still uses psycopg2 for schema creation as Supabase client 
doesn't support CREATE TABLE operations. For regular queries, use utils/db.py 
which uses the Supabase client.
"""
import psycopg2
import sys
import os


def create_schema(database_url: str):
    """
    Create the drugs table and indexes.
    
    Note: This requires a direct Postgres connection string.
    For cloud deployments, run this locally or use Supabase SQL Editor.
    """
    conn = psycopg2.connect(database_url)
    
    try:
        with conn.cursor() as cur:
            # Create table
            print("Creating drugs table...")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS drugs (
                    drug_name TEXT PRIMARY KEY,
                    category TEXT,
                    drug_status TEXT,
                    hcpcs TEXT,
                    manufacturer TEXT,
                    pa_mnd_required TEXT,
                    notes TEXT
                )
            """)
            
            # Create indexes
            print("Creating indexes...")
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_drugs_category 
                ON drugs(category)
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_drugs_status 
                ON drugs(drug_status)
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_drugs_pa_mnd 
                ON drugs(pa_mnd_required)
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_drugs_name_lower
                ON drugs(LOWER(drug_name))
            """)
            
            conn.commit()
            print("Database schema created successfully!")
            
            # Display table info
            cur.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'drugs'
            """)
            
            print("\nTable Structure:")
            for row in cur.fetchall():
                print(f"   {row[0]}: {row[1]}")
    
    except Exception as e:
        print(f"Error creating schema: {e}")
        sys.exit(1)
    
    finally:
        conn.close()


def get_database_url():
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
    # Fallback: prompt user
    return input("Enter your DATABASE_URL: ").strip()


def main():
    """Main entry point."""
    DATABASE_URL = get_database_url()
    if not DATABASE_URL:
        print("DATABASE_URL is required")
        sys.exit(1)
    
    create_schema(DATABASE_URL)


if __name__ == "__main__":
    main()
