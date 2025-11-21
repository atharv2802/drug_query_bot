"""
Database access layer for drug queries.
Handles all Supabase Postgres interactions.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional, List, Dict, Any
import streamlit as st
from utils.fuzzy import fuzzy_match_drug_name


def get_db_connection():
    """
    Establish connection to Supabase Postgres database.
    Uses DATABASE_URL from Streamlit secrets.
    """
    try:
        conn = psycopg2.connect(
            st.secrets["DATABASE_URL"],
            cursor_factory=RealDictCursor
        )
        return conn
    except Exception as e:
        st.error(f"Database connection failed: {str(e)}")
        raise


def fetch_all_drug_names() -> List[str]:
    """
    Fetch all drug names from the database for fuzzy matching.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT drug_name FROM drugs")
            rows = cur.fetchall()
            return [row['drug_name'] for row in rows]
    finally:
        conn.close()


def fetch_drug_by_name(name: str) -> Optional[Dict[str, Any]]:
    """
    Fetch drug information by exact or fuzzy name match.
    
    Args:
        name: Drug name to search for
        
    Returns:
        Dictionary with drug information or None if not found
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Try exact match first (case-insensitive)
            cur.execute(
                "SELECT * FROM drugs WHERE LOWER(drug_name) = LOWER(%s)",
                (name,)
            )
            result = cur.fetchone()
            
            if result:
                return dict(result)
            
            # Try fuzzy match
            all_drug_names = fetch_all_drug_names()
            matched_name, confidence = fuzzy_match_drug_name(name, all_drug_names)
            
            if matched_name and confidence >= 70:
                cur.execute(
                    "SELECT * FROM drugs WHERE LOWER(drug_name) = LOWER(%s)",
                    (matched_name,)
                )
                result = cur.fetchone()
                if result:
                    result_dict = dict(result)
                    result_dict['_fuzzy_match'] = True
                    result_dict['_fuzzy_confidence'] = confidence
                    result_dict['_original_query'] = name
                    return result_dict
            
            return None
    finally:
        conn.close()


def fetch_alternatives(drug_name: str) -> List[Dict[str, Any]]:
    """
    Fetch preferred alternatives for a given drug.
    
    Logic:
    1. Find the drug's category
    2. Return all preferred drugs in the same category
    3. Exclude the original drug
    
    Args:
        drug_name: Name of the drug to find alternatives for
        
    Returns:
        List of preferred alternative drugs
    """
    conn = get_db_connection()
    try:
        # First, get the drug's category
        drug_info = fetch_drug_by_name(drug_name)
        
        if not drug_info or not drug_info.get('category'):
            return []
        
        category = drug_info['category']
        actual_drug_name = drug_info['drug_name']
        
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT * FROM drugs 
                WHERE category = %s 
                AND drug_status = 'preferred'
                AND LOWER(drug_name) != LOWER(%s)
                ORDER BY drug_name
                """,
                (category, actual_drug_name)
            )
            results = cur.fetchall()
            return [dict(row) for row in results]
    finally:
        conn.close()


def filter_drugs(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Filter drugs based on multiple criteria.
    
    Supported filters:
    - drug_status: 'preferred', 'non_preferred', 'not_listed'
    - pa_mnd_required: 'yes', 'no', 'unknown' (combined PA/MND requirement)
    - category: category name (partial match)
    - hcpcs: HCPCS code
    - manufacturer: manufacturer name (partial match)
    
    Args:
        filters: Dictionary of filter criteria
        
    Returns:
        List of drugs matching all criteria
    """
    conn = get_db_connection()
    try:
        conditions = []
        params = []
        
        if filters.get('drug_status'):
            # Normalize to match DB values
            status = filters['drug_status'].lower().replace('-', '_')
            if status in ['preferred', 'non_preferred', 'not_listed']:
                conditions.append("drug_status = %s")
                params.append(status)
        if filters.get('pa_mnd_required'):
            # Normalize to match DB values
            pa_mnd = filters['pa_mnd_required'].lower() if isinstance(filters['pa_mnd_required'], str) else filters['pa_mnd_required']
            if pa_mnd in ['yes', 'no', 'unknown']:
                conditions.append("pa_mnd_required = %s")
                params.append(pa_mnd)
        
        if filters.get('category'):
            conditions.append("LOWER(category) LIKE LOWER(%s)")
            params.append(f"%{filters['category']}%")
        
        if filters.get('hcpcs'):
            conditions.append("LOWER(hcpcs) = LOWER(%s)")
            params.append(filters['hcpcs'])
        
        if filters.get('manufacturer'):
            manufacturer = filters['manufacturer'].lower()
            # Handle special case: "generic" keyword should match manufacturer='Generic'
            if 'generic' in manufacturer:
                conditions.append("LOWER(manufacturer) = 'generic'")
            else:
                conditions.append("LOWER(manufacturer) LIKE LOWER(%s)")
                params.append(f"%{filters['manufacturer']}%")
        
        # Build query
        query = "SELECT * FROM drugs"
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY drug_name"
        
        with conn.cursor() as cur:
            cur.execute(query, params)
            results = cur.fetchall()
            return [dict(row) for row in results]
    finally:
        conn.close()


def get_all_categories() -> List[str]:
    """
    Get all unique categories from the database.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT DISTINCT category FROM drugs WHERE category IS NOT NULL ORDER BY category"
            )
            rows = cur.fetchall()
            return [row['category'] for row in rows]
    finally:
        conn.close()
