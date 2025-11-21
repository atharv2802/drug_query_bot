"""
Fuzzy matching utilities for drug name resolution.
Uses RapidFuzz for similarity matching.
"""

import re
from rapidfuzz import fuzz, process
from typing import List, Tuple, Optional


def normalize_drug_name(name: str) -> str:
    """
    Normalize a drug name for comparison.
    
    - Convert to lowercase
    - Strip whitespace
    - Remove ™ and ® symbols
    - Remove extra whitespace
    
    Args:
        name: Raw drug name
        
    Returns:
        Normalized drug name
    """
    if not name:
        return ""
    
    # Convert to lowercase
    normalized = name.lower()
    
    # Remove trademark symbols
    normalized = normalized.replace('™', '').replace('®', '')
    
    # Remove extra whitespace
    normalized = re.sub(r'\s+', ' ', normalized)
    
    # Strip leading/trailing whitespace
    normalized = normalized.strip()
    
    return normalized


def fuzzy_match_drug_name(query: str, drug_names: List[str], threshold: int = 70) -> Tuple[Optional[str], int]:
    """
    Find the best matching drug name using fuzzy matching.
    
    Uses RapidFuzz's token_sort_ratio for better partial matching.
    
    Args:
        query: User's drug name query
        drug_names: List of valid drug names from database
        threshold: Minimum confidence score (0-100)
        
    Returns:
        Tuple of (best_match_name, confidence_score)
        Returns (None, 0) if no match meets threshold
    """
    if not query or not drug_names:
        return None, 0
    
    # Normalize query
    normalized_query = normalize_drug_name(query)
    
    # Normalize all drug names for comparison
    normalized_drugs = {normalize_drug_name(name): name for name in drug_names}
    
    # Try exact match first
    if normalized_query in normalized_drugs:
        return normalized_drugs[normalized_query], 100
    
    # Use fuzzy matching
    result = process.extractOne(
        normalized_query,
        list(normalized_drugs.keys()),
        scorer=fuzz.token_sort_ratio
    )
    
    if result and result[1] >= threshold:
        matched_normalized = result[0]
        original_name = normalized_drugs[matched_normalized]
        confidence = int(result[1])
        return original_name, confidence
    
    return None, 0


def extract_drug_name_from_query(query: str, drug_names: List[str]) -> Tuple[Optional[str], int, str]:
    """
    Extract a drug name from a natural language query.
    
    Tries to identify drug names by:
    1. Checking each word/phrase against known drugs
    2. Using fuzzy matching for potential typos
    
    Args:
        query: User's natural language query
        drug_names: List of valid drug names from database
        
    Returns:
        Tuple of (matched_drug_name, confidence, extraction_method)
    """
    if not query:
        return None, 0, "empty_query"
    
    # Try to find drug name by checking words in query
    words = query.split()
    
    # Check individual words and consecutive pairs
    candidates = []
    
    for i in range(len(words)):
        # Single word
        candidates.append(words[i])
        
        # Two consecutive words
        if i < len(words) - 1:
            candidates.append(f"{words[i]} {words[i+1]}")
        
        # Three consecutive words
        if i < len(words) - 2:
            candidates.append(f"{words[i]} {words[i+1]} {words[i+2]}")
    
    # Find best match among candidates
    best_match = None
    best_confidence = 0
    
    for candidate in candidates:
        matched_name, confidence = fuzzy_match_drug_name(candidate, drug_names, threshold=60)
        if confidence > best_confidence:
            best_match = matched_name
            best_confidence = confidence
    
    if best_match:
        return best_match, best_confidence, "extracted_from_query"
    
    # Last resort: try matching entire query
    matched_name, confidence = fuzzy_match_drug_name(query, drug_names, threshold=50)
    if matched_name:
        return matched_name, confidence, "full_query_match"
    
    return None, 0, "no_match"
