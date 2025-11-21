"""
Database access layer for drug queries.
Handles all Supabase interactions using the Supabase Python client.
"""

from supabase import create_client, Client
from typing import Optional, List, Dict, Any
import streamlit as st
import os
from utils.fuzzy import fuzzy_match_drug_name


def get_supabase_client() -> Client:
    """
    Get Supabase client instance.
    Uses SUPABASE_URL and SUPABASE_KEY from Streamlit secrets or environment variables.
    """
    try:
        # Try Streamlit secrets first
        if hasattr(st, 'secrets') and 'SUPABASE_URL' in st.secrets:
            url = st.secrets["SUPABASE_URL"]
            key = st.secrets["SUPABASE_KEY"]
        # Fallback to environment variables
        else:
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_KEY")
            if not url or not key:
                raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in secrets or environment")
        
        return create_client(url, key)
    except Exception as e:
        st.error(f"Supabase client initialization failed: {str(e)}")
        raise


def fetch_all_drug_names() -> List[str]:
    """
    Fetch all drug names from the database for fuzzy matching.
    """
    supabase = get_supabase_client()
    try:
        response = supabase.table("drugs").select("drug_name").execute()
        return [row['drug_name'] for row in response.data]
    except Exception as e:
        st.error(f"Failed to fetch drug names: {str(e)}")
        raise


def fetch_drug_by_name(name: str) -> Optional[Dict[str, Any]]:
    """
    Fetch drug information by exact or fuzzy name match.
    
    Args:
        name: Drug name to search for
        
    Returns:
        Dictionary with drug information or None if not found
    """
    supabase = get_supabase_client()
    try:
        # Try exact match first (case-insensitive using ilike)
        response = supabase.table("drugs").select("*").ilike("drug_name", name).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        
        # Try fuzzy match
        all_drug_names = fetch_all_drug_names()
        matched_name, confidence = fuzzy_match_drug_name(name, all_drug_names)
        
        if matched_name and confidence >= 70:
            response = supabase.table("drugs").select("*").ilike("drug_name", matched_name).execute()
            if response.data and len(response.data) > 0:
                result_dict = response.data[0].copy()
                result_dict['_fuzzy_match'] = True
                result_dict['_fuzzy_confidence'] = confidence
                result_dict['_original_query'] = name
                return result_dict
        
        return None
    except Exception as e:
        st.error(f"Failed to fetch drug by name: {str(e)}")
        raise


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
    supabase = get_supabase_client()
    try:
        # First, get the drug's category
        drug_info = fetch_drug_by_name(drug_name)
        
        if not drug_info or not drug_info.get('category'):
            return []
        
        category = drug_info['category']
        actual_drug_name = drug_info['drug_name']
        
        # Fetch alternatives in same category, preferred status, excluding the original drug
        response = (supabase.table("drugs")
                   .select("*")
                   .eq("category", category)
                   .eq("drug_status", "preferred")
                   .neq("drug_name", actual_drug_name)
                   .order("drug_name")
                   .execute())
        
        return response.data
    except Exception as e:
        st.error(f"Failed to fetch alternatives: {str(e)}")
        raise


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
    supabase = get_supabase_client()
    try:
        query = supabase.table("drugs").select("*")
        
        if filters.get('drug_status'):
            # Normalize to match DB values
            status = filters['drug_status'].lower().replace('-', '_')
            if status in ['preferred', 'non_preferred', 'not_listed']:
                query = query.eq("drug_status", status)
        
        if filters.get('pa_mnd_required'):
            # Normalize to match DB values
            pa_mnd = filters['pa_mnd_required'].lower() if isinstance(filters['pa_mnd_required'], str) else filters['pa_mnd_required']
            if pa_mnd in ['yes', 'no', 'unknown']:
                query = query.eq("pa_mnd_required", pa_mnd)
        
        if filters.get('category'):
            # Use exact match for category (case-insensitive)
            query = query.eq("category", filters['category'])
        
        if filters.get('hcpcs'):
            query = query.eq("hcpcs", filters['hcpcs'])
        
        if filters.get('manufacturer'):
            manufacturer = filters['manufacturer']
            # Use exact match for manufacturer (case-insensitive)
            query = query.eq("manufacturer", manufacturer)
        
        response = query.order("drug_name").execute()
        return response.data
    except Exception as e:
        if hasattr(st, 'error'):
            st.error(f"Failed to filter drugs: {str(e)}")
        raise


def get_all_categories() -> List[str]:
    """
    Get all unique categories from the database.
    """
    supabase = get_supabase_client()
    try:
        response = (supabase.table("drugs")
                   .select("category")
                   .not_.is_("category", "null")
                   .execute())
        
        # Extract unique categories and sort
        categories = list(set(row['category'] for row in response.data if row.get('category')))
        return sorted(categories)
    except Exception as e:
        st.error(f"Failed to fetch categories: {str(e)}")
        raise
