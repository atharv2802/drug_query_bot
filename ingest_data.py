"""
Data ingestion script for loading drug data into Supabase.

Merges two data sources:
1. Preferred Medical Drugs List (category, status, name, HCPCS, manufacturer)
2. PA/MND List (drugs requiring prior authorization or medical necessity determination)

Logic:
- Drugs in pa_mnd_list.csv are marked with pa_mnd_required = 'yes'
- Drugs NOT in pa_mnd_list.csv are marked with pa_mnd_required = 'no'
"""
import csv
import psycopg2
from psycopg2.extras import execute_values
import re
from typing import Dict, List, Any


def normalize_drug_name(name: str) -> str:
    """Normalize drug name for consistency."""
    if not name:
        return ""
    normalized = name.lower().strip()
    normalized = normalized.replace('™', '').replace('®', '')
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized


def load_preferred_drugs_list(csv_path: str) -> List[Dict[str, Any]]:
    """
    Load the Preferred Medical Drugs List from CSV.
    
    This list contains drug categorization and preference information.
    
    Expected columns:
    - Category (e.g., Oncology, Immunology, Rheumatology)
    - Drug Status (Preferred, Non-Preferred)
    - Drug Name
    - HCPCS (billing code)
    - Manufacturer
    """
    drugs = []
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            status_raw = row.get('Drug Status', '').strip().lower().replace('-', '_').replace(' ', '_')
            if status_raw in ['preferred', 'non_preferred']:
                drug_status = status_raw
            else:
                drug_status = 'not_listed'
            drug = {
                'drug_name': row.get('Drug Name', '').strip(),
                'category': row.get('Category', '').strip() or None,
                'drug_status': drug_status,
                'hcpcs': row.get('HCPCS', '').strip() or None,
                'manufacturer': row.get('Manufacturer', '').strip() or None,
                'pa_mnd_required': 'no',  # Default to 'no', will be updated during merge
                'notes': None
            }
            drugs.append(drug)
    
    return drugs


def load_pa_mnd_list(csv_path: str) -> Dict[str, str]:
    """
    Load the Prior Authorization/Medical Necessity Determination Medicine List from CSV.
    
    This is a simple list containing drugs that require PA or MND.
    Any drug in this list is marked as requiring authorization.
    
    Expected columns:
    - Drug Name
    
    Returns:
        Dictionary mapping drug_name to 'yes' (all drugs in this list require PA/MND)
    """
    pa_mnd_data = {}
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            drug_name = row.get('Drug Name', '').strip()
            if drug_name:
                # Any drug in this list requires PA/MND
                pa_mnd_data[drug_name] = 'yes'
    
    return pa_mnd_data


def merge_drug_data(
    preferred_drugs: List[Dict[str, Any]],
    pa_mnd_data: Dict[str, str]
) -> List[Dict[str, Any]]:
    """
    Merge preferred drugs list with PA/MND data as described:
    1. Load preferred_drugs_list, set pa_mnd_required to 'no'.
    2. For each drug in pa_mnd_list:
       - If present in preferred_drugs, update pa_mnd_required to 'yes'.
       - If not present, add with only drug_name, pa_mnd_required='yes', notes, others empty.
    """
    # Step 1: Add all preferred drugs, pa_mnd_required = 'no'
    drugs_map = {}
    for drug in preferred_drugs:
        normalized_name = normalize_drug_name(drug['drug_name'])
        # Ensure pa_mnd_required is 'no' (even if CSV was wrong)
        drug['pa_mnd_required'] = 'no'
        drugs_map[normalized_name] = drug

    # Step 2: Update/add drugs from pa_mnd_list
    for drug_name, pa_mnd_status in pa_mnd_data.items():
        normalized_name = normalize_drug_name(drug_name)
        if normalized_name in drugs_map:
            # Update flag only
            drugs_map[normalized_name]['pa_mnd_required'] = 'yes'
        else:
            # Add new drug with only name, flag, and notes
            drugs_map[normalized_name] = {
                'drug_name': drug_name,
                'category': None,
                'drug_status': None,
                'hcpcs': None,
                'manufacturer': None,
                'pa_mnd_required': 'yes',
                'notes': 'Only found in PA/MND list'
            }
    return list(drugs_map.values())


def insert_drugs_to_db(drugs: List[Dict[str, Any]], database_url: str):
    """
    Insert merged drug data into Supabase Postgres.
    """
    conn = psycopg2.connect(database_url)
    
    try:
        with conn.cursor() as cur:
            # Clear existing data (optional - comment out to append instead)
            cur.execute("TRUNCATE TABLE drugs")
            
            # Prepare data for insertion
            drug_tuples = [
                (
                    drug['drug_name'],
                    drug['category'],
                    drug['drug_status'],
                    drug['hcpcs'],
                    drug['manufacturer'],
                    drug['pa_mnd_required'],
                    drug['notes']
                )
                for drug in drugs
            ]
            
            # Batch insert
            execute_values(
                cur,
                """
                INSERT INTO drugs 
                (drug_name, category, drug_status, hcpcs, manufacturer, 
                 pa_mnd_required, notes)
                VALUES %s
                ON CONFLICT (drug_name) DO UPDATE SET
                    category = EXCLUDED.category,
                    drug_status = EXCLUDED.drug_status,
                    hcpcs = EXCLUDED.hcpcs,
                    manufacturer = EXCLUDED.manufacturer,
                    pa_mnd_required = EXCLUDED.pa_mnd_required,
                    notes = EXCLUDED.notes
                """,
                drug_tuples
            )
            
            conn.commit()
            print(f"Successfully inserted {len(drugs)} drugs into database")
    
    finally:
        conn.close()


def main():
    """
    Main data ingestion pipeline.
    """
    import argparse
    import os
    try:
        import streamlit as st
    except ImportError:
        st = None

    parser = argparse.ArgumentParser(description="Drug Data Ingestion Script")
    parser.add_argument('--preferred_csv', type=str, default="data/preferred_drugs_list.csv", help="Path to preferred drugs CSV")
    parser.add_argument('--pa_mnd_csv', type=str, default="data/pa_mnd_list.csv", help="Path to PA/MND CSV")
    parser.add_argument('--db_url', type=str, default=None, help="Database URL")
    args = parser.parse_args()

    PREFERRED_DRUGS_CSV = args.preferred_csv
    PA_MND_CSV = args.pa_mnd_csv

    # Try to get DATABASE_URL from CLI, env, or Streamlit secrets
    DATABASE_URL = args.db_url or os.environ.get("DATABASE_URL")
    if not DATABASE_URL and st is not None:
        DATABASE_URL = st.secrets.get("DATABASE_URL")
    if not DATABASE_URL:
        print("Error: DATABASE_URL must be provided via --db_url, environment variable, or Streamlit secrets.")
        return

    print(f"Loading Preferred Medical Drugs List from {PREFERRED_DRUGS_CSV}...")
    preferred_drugs = load_preferred_drugs_list(PREFERRED_DRUGS_CSV)
    print(f"   Loaded {len(preferred_drugs)} drugs")

    print(f"Loading PA/MND Medicine List from {PA_MND_CSV}...")
    pa_mnd_data = load_pa_mnd_list(PA_MND_CSV)
    print(f"   Loaded {len(pa_mnd_data)} PA/MND entries")

    print("Merging data...")
    merged_drugs = merge_drug_data(preferred_drugs, pa_mnd_data)
    print(f"   Final dataset: {len(merged_drugs)} drugs")

    print("Inserting into database...")
    insert_drugs_to_db(merged_drugs, DATABASE_URL)

    print("Data ingestion complete!")


if __name__ == "__main__":
    main()
