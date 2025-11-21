"""
Database access layer for drug queries.
Handles all Supabase interactions using the Supabase Python client.
"""

from supabase import create_client, Client
from typing import Optional, List, Dict, Any, Tuple
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


@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_all_drug_names() -> List[str]:
    """
    Fetch all unique drug names from the database for fuzzy matching.
    Handles pagination to get all records beyond Supabase's 1000 row default limit.
    CACHED: Results are cached for 1 hour to improve performance.
    
    Note: Uses DISTINCT since each drug appears multiple times (once per category).
    """
    supabase = get_supabase_client()
    try:
        # Fetch all unique drug names with pagination
        all_names = set()  # Use set to automatically handle duplicates
        page_size = 1000
        offset = 0
        
        while True:
            response = (supabase.table("drugs")
                       .select("drug_name")
                       .range(offset, offset + page_size - 1)
                       .execute())
            
            if not response.data:
                break
            
            all_names.update([row['drug_name'] for row in response.data])
            
            # If we got less than page_size, we've reached the end
            if len(response.data) < page_size:
                break
            
            offset += page_size
        
        return sorted(list(all_names))  # Return sorted list of unique names
    except Exception as e:
        if hasattr(st, 'error'):
            st.error(f"Failed to fetch drug names: {str(e)}")
        raise


def fetch_drug_by_name(name: str) -> Optional[Dict[str, Any]]:
    """
    Fetch drug information by exact or fuzzy name match.
    Aggregates multiple rows (one per category) into a single drug object.
    
    Args:
        name: Drug name to search for
        
    Returns:
        Dictionary with drug information or None if not found
        Includes:
        - drug_name: str
        - categories: List[str] - all categories the drug appears in
        - statuses_by_category: Dict[str, str] - status for each category
        - drug_status: str - overall status (preferred if ANY category is preferred)
        - hcpcs, manufacturer, pa_mnd_required, notes: from first row
    """
    supabase = get_supabase_client()
    try:
        # Try exact match first (case-insensitive using ilike)
        response = supabase.table("drugs").select("*").ilike("drug_name", name).execute()
        
        if not response.data or len(response.data) == 0:
            # Try fuzzy match
            all_drug_names = fetch_all_drug_names()
            matched_name, confidence = fuzzy_match_drug_name(name, all_drug_names)
            
            if not matched_name or confidence < 70:
                return None
            
            response = supabase.table("drugs").select("*").ilike("drug_name", matched_name).execute()
            
            if not response.data or len(response.data) == 0:
                return None
        
        # Aggregate multiple rows into single drug object
        rows = response.data
        drug = {
            'drug_name': rows[0]['drug_name'],
            'hcpcs': rows[0]['hcpcs'],
            'manufacturer': rows[0]['manufacturer'],
            'pa_mnd_required': rows[0]['pa_mnd_required'],
            'notes': rows[0]['notes'],
            'categories': [],
            'statuses_by_category': {}
        }
        
        # Collect all categories and their statuses
        for row in rows:
            category = row['category']
            status = row['drug_status']
            drug['categories'].append(category)
            drug['statuses_by_category'][category] = status
        
        # Determine overall status: preferred if ANY category is preferred
        all_statuses = list(drug['statuses_by_category'].values())
        if 'preferred' in all_statuses:
            drug['drug_status'] = 'preferred'
        elif 'non_preferred' in all_statuses:
            drug['drug_status'] = 'non_preferred'
        else:
            drug['drug_status'] = all_statuses[0] if all_statuses else 'not_listed'
        
        return drug
    except Exception as e:
        st.error(f"Failed to fetch drug by name: {str(e)}")
        raise


def fetch_alternatives(drug_name: str, drug_status: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetch alternatives for a given drug.
    
    Logic:
    1. Find the drug's categories
    2. Query all drugs in those same categories
    3. Aggregate by drug_name and exclude the original drug
    
    Args:
        drug_name: Name of the drug to find alternatives for
        drug_status: Optional filter - 'preferred', 'non_preferred', or None for all
        
    Returns:
        List of alternative drugs (aggregated by drug_name)
    """
    supabase = get_supabase_client()
    try:
        # First, get the drug's categories
        drug_info = fetch_drug_by_name(drug_name)
        
        if not drug_info or not drug_info.get('categories'):
            return []
        
        categories = drug_info['categories']
        actual_drug_name = drug_info['drug_name']
        
        # Fetch all drugs in the same categories with pagination
        all_rows = []
        page_size = 1000
        offset = 0
        
        # Query each category separately and collect results
        for category in categories:
            offset = 0
            while True:
                query = (supabase.table("drugs")
                        .select("*")
                        .eq("category", category)
                        .neq("drug_name", actual_drug_name)
                        .range(offset, offset + page_size - 1))
                
                # Optionally filter by drug_status
                if drug_status:
                    query = query.eq("drug_status", drug_status)
                
                response = query.order("drug_name").execute()
                
                if not response.data:
                    break
                
                all_rows.extend(response.data)
                
                if len(response.data) < page_size:
                    break
                
                offset += page_size
        
        # Aggregate rows by drug_name
        drugs_dict = {}
        for row in all_rows:
            name = row['drug_name']
            if name not in drugs_dict:
                drugs_dict[name] = {
                    'drug_name': name,
                    'hcpcs': row['hcpcs'],
                    'manufacturer': row['manufacturer'],
                    'pa_mnd_required': row['pa_mnd_required'],
                    'notes': row['notes'],
                    'categories': [],
                    'statuses_by_category': {}
                }
            
            drugs_dict[name]['categories'].append(row['category'])
            drugs_dict[name]['statuses_by_category'][row['category']] = row['drug_status']
        
        # Determine overall status for each drug
        alternatives = []
        for drug in drugs_dict.values():
            all_statuses = list(drug['statuses_by_category'].values())
            if 'preferred' in all_statuses:
                drug['drug_status'] = 'preferred'
            elif 'non_preferred' in all_statuses:
                drug['drug_status'] = 'non_preferred'
            else:
                drug['drug_status'] = all_statuses[0] if all_statuses else 'not_listed'
            
            alternatives.append(drug)
        
        return alternatives
    except Exception as e:
        if hasattr(st, 'error'):
            st.error(f"Failed to fetch alternatives: {str(e)}")
        raise


def filter_drugs(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Filter drugs based on multiple criteria.
    Aggregates results by drug_name since each drug appears multiple times (once per category).
    
    Supported filters:
    - drug_status: 'preferred', 'non_preferred', 'not_listed'
    - pa_mnd_required: 'yes', 'no', 'unknown' (combined PA/MND requirement)
    - category: category name (exact or partial match)
    - hcpcs: HCPCS code
    - manufacturer: manufacturer name (partial match)
    - has_preferred_alternative: True (only for non-preferred drugs with preferred alternatives)
    
    Args:
        filters: Dictionary of filter criteria
        
    Returns:
        List of drugs matching all criteria (aggregated by drug_name)
    """
    # Handle special case: non-preferred drugs with preferred alternatives
    if filters.get('has_preferred_alternative'):
        return get_non_preferred_drugs_with_preferred_alternatives()
    
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
            # Category is now a single value per row - use equality
            category_filter = filters['category']
            query = query.ilike("category", f"%{category_filter}%")
        
        if filters.get('hcpcs'):
            query = query.eq("hcpcs", filters['hcpcs'])
        
        if filters.get('manufacturer'):
            manufacturer = filters['manufacturer']
            query = query.ilike("manufacturer", f"%{manufacturer}%")
        
        response = query.order("drug_name").execute()
        
        # Aggregate results by drug_name
        drugs_dict = {}
        for row in response.data:
            name = row['drug_name']
            if name not in drugs_dict:
                drugs_dict[name] = {
                    'drug_name': name,
                    'hcpcs': row['hcpcs'],
                    'manufacturer': row['manufacturer'],
                    'pa_mnd_required': row['pa_mnd_required'],
                    'notes': row['notes'],
                    'categories': [],
                    'statuses_by_category': {}
                }
            
            drugs_dict[name]['categories'].append(row['category'])
            drugs_dict[name]['statuses_by_category'][row['category']] = row['drug_status']
        
        # Determine overall status for each drug
        results = []
        for drug in drugs_dict.values():
            all_statuses = list(drug['statuses_by_category'].values())
            if 'preferred' in all_statuses:
                drug['drug_status'] = 'preferred'
            elif 'non_preferred' in all_statuses:
                drug['drug_status'] = 'non_preferred'
            else:
                drug['drug_status'] = all_statuses[0] if all_statuses else 'not_listed'
            
            results.append(drug)
        
        return results
    except Exception as e:
        if hasattr(st, 'error'):
            st.error(f"Failed to filter drugs: {str(e)}")
        raise



def get_non_preferred_drugs_with_preferred_alternatives() -> List[Dict[str, Any]]:
    """
    Find all non-preferred drugs that have at least one preferred alternative in a shared category.
    Aggregates results by drug_name.
    
    Returns:
        List of non-preferred drugs that have preferred alternatives
    """
    supabase = get_supabase_client()
    try:
        # Get all non-preferred drug-category pairs
        non_preferred_response = (supabase.table("drugs")
                                 .select("*")
                                 .eq("drug_status", "non_preferred")
                                 .not_.is_("category", "null")
                                 .execute())
        
        # Get all preferred drug-category pairs
        preferred_response = (supabase.table("drugs")
                             .select("category")
                             .eq("drug_status", "preferred")
                             .not_.is_("category", "null")
                             .execute())
        
        # Build a set of categories that have preferred drugs
        categories_with_preferred = set()
        for row in preferred_response.data:
            if row.get('category'):
                categories_with_preferred.add(row['category'])
        
        # Filter non-preferred drugs that share a category with a preferred drug
        # Then aggregate by drug_name
        drugs_dict = {}
        for row in non_preferred_response.data:
            category = row.get('category')
            if category in categories_with_preferred:
                name = row['drug_name']
                if name not in drugs_dict:
                    drugs_dict[name] = {
                        'drug_name': name,
                        'hcpcs': row['hcpcs'],
                        'manufacturer': row['manufacturer'],
                        'pa_mnd_required': row['pa_mnd_required'],
                        'notes': row['notes'],
                        'categories': [],
                        'statuses_by_category': {}
                    }
                
                drugs_dict[name]['categories'].append(category)
                drugs_dict[name]['statuses_by_category'][category] = row['drug_status']
        
        # Set overall status
        results = []
        for drug in drugs_dict.values():
            drug['drug_status'] = 'non_preferred'  # All are non-preferred by filter
            results.append(drug)
        
        return results
    except Exception as e:
        if hasattr(st, 'error'):
            st.error(f"Failed to find non-preferred drugs with preferred alternatives: {str(e)}")
        raise
        raise


@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_all_categories() -> List[str]:
    """
    Get all unique categories from the database.
    Uses SELECT DISTINCT since each category is a separate row.
    CACHED: Results are cached for 1 hour to improve performance.
    """
    supabase = get_supabase_client()
    try:
        # Fetch all unique categories with pagination
        all_categories = set()
        page_size = 1000
        offset = 0
        
        while True:
            response = (supabase.table("drugs")
                       .select("category")
                       .not_.is_("category", "null")
                       .range(offset, offset + page_size - 1)
                       .execute())
            
            if not response.data:
                break
            
            all_categories.update([row['category'] for row in response.data if row.get('category')])
            
            if len(response.data) < page_size:
                break
            
            offset += page_size
        
        return sorted(list(all_categories))
    except Exception as e:
        st.error(f"Failed to fetch categories: {str(e)}")
        raise


def fuzzy_search_drug_db(query: str, limit: int = 5) -> List[Tuple[str, float]]:
    """
    Database-side fuzzy search using PostgreSQL pattern matching.
    This is more efficient than loading all names and doing client-side fuzzy matching.
    
    Args:
        query: Drug name to search for
        limit: Maximum number of results to return
        
    Returns:
        List of tuples (drug_name, similarity_score) sorted by relevance
    """
    supabase = get_supabase_client()
    try:
        query_normalized = query.strip().lower()
        
        # Try exact match first
        exact_response = (supabase.table("drugs")
                         .select("drug_name")
                         .ilike("drug_name", query_normalized)
                         .limit(1)
                         .execute())
        
        if exact_response.data:
            return [(exact_response.data[0]['drug_name'], 100.0)]
        
        # Try prefix match (starts with)
        prefix_response = (supabase.table("drugs")
                          .select("drug_name")
                          .ilike("drug_name", f"{query_normalized}%")
                          .limit(limit)
                          .execute())
        
        if prefix_response.data:
            results = [(row['drug_name'], 90.0) for row in prefix_response.data]
            return results[:limit]
        
        # Try contains match
        contains_response = (supabase.table("drugs")
                            .select("drug_name")
                            .ilike("drug_name", f"%{query_normalized}%")
                            .limit(limit * 2)
                            .execute())
        
        if contains_response.data:
            # Score based on position and length similarity
            results = []
            for row in contains_response.data:
                name = row['drug_name']
                # Higher score if match is closer to start
                pos = name.lower().find(query_normalized)
                length_ratio = len(query_normalized) / len(name)
                score = 70.0 + (20.0 * length_ratio) - (pos * 2)
                score = max(60.0, min(89.0, score))  # Clamp between 60-89
                results.append((name, score))
            
            # Sort by score descending
            results.sort(key=lambda x: x[1], reverse=True)
            return results[:limit]
        
        return []
    except Exception as e:
        if hasattr(st, 'error'):
            st.error(f"Failed to fuzzy search: {str(e)}")
        # Fallback to client-side fuzzy matching
        return []


def autocomplete_drug_search(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Autocomplete search for drug names with metadata.
    Returns drugs that match the query prefix with category and status info.
    
    Args:
        query: Partial drug name to search for
        limit: Maximum number of suggestions
        
    Returns:
        List of drug dictionaries with name, category, status
    """
    supabase = get_supabase_client()
    try:
        if not query or len(query) < 2:
            return []
        
        query_normalized = query.strip().lower()
        
        # Search for drugs that start with or contain the query
        response = (supabase.table("drugs")
                   .select("drug_name, category, drug_status")
                   .or_(f"drug_name.ilike.{query_normalized}%,drug_name.ilike.%{query_normalized}%")
                   .order("drug_name")
                   .limit(limit)
                   .execute())
        
        # Prioritize prefix matches
        results = response.data if response.data else []
        results.sort(key=lambda x: (
            not x['drug_name'].lower().startswith(query_normalized),  # Prefix matches first
            x['drug_name'].lower()
        ))
        
        return results[:limit]
    except Exception as e:
        if hasattr(st, 'error'):
            st.error(f"Failed to autocomplete: {str(e)}")
        return []


def suggest_corrections(query: str, threshold: float = 0.6, limit: int = 5) -> List[Tuple[str, float]]:
    """
    Suggest drug name corrections for typos or misspellings.
    Shows "Did you mean..." suggestions.
    
    Args:
        query: User's input (potentially misspelled)
        threshold: Minimum similarity score (0-1)
        limit: Maximum number of suggestions
        
    Returns:
        List of tuples (drug_name, confidence) sorted by confidence
    """
    try:
        # Try database-side fuzzy search first (more efficient)
        db_results = fuzzy_search_drug_db(query, limit=limit)
        
        if db_results:
            # Filter by threshold and convert to 0-1 scale
            filtered = [(name, score/100.0) for name, score in db_results if score/100.0 >= threshold]
            if filtered:
                return filtered
        
        # Fallback to client-side fuzzy matching if database search doesn't yield results
        all_names = fetch_all_drug_names()
        matched_name, confidence, _ = fuzzy_match_drug_name(query, all_names)
        
        if matched_name and confidence >= threshold * 100:
            # Get similar names using rapidfuzz
            from rapidfuzz import process, fuzz
            matches = process.extract(
                query, 
                all_names, 
                scorer=fuzz.WRatio,
                limit=limit
            )
            
            # Filter by threshold and convert to 0-1 scale
            results = [(name, score/100.0) for name, score, _ in matches if score/100.0 >= threshold]
            return results
        
        return []
    except Exception as e:
        if hasattr(st, 'error'):
            st.error(f"Failed to suggest corrections: {str(e)}")
        return []
