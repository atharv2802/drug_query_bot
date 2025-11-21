"""
Intent parsing and query understanding.
Uses rule-based logic with LLM fallback for ambiguous queries.
"""

import re
from typing import Dict, Any, Optional, Tuple
from utils.fuzzy import extract_drug_name_from_query


# Known category keywords
CATEGORY_KEYWORDS = {
    'oncology': ['oncology', 'cancer', 'chemotherapy', 'chemo'],
    'immunology': ['immunology', 'immune', 'autoimmune'],
    'rheumatology': ['rheumatology', 'rheumatoid', 'arthritis'],
    'dermatology': ['dermatology', 'skin', 'dermatological'],
    'gastroenterology': ['gastroenterology', 'gi', 'digestive', 'crohn', 'colitis'],
    'neurology': ['neurology', 'neurological', 'nerve'],
    'hematology': ['hematology', 'blood'],
    'cardiology': ['cardiology', 'heart', 'cardiac'],
}


def detect_query_type(query: str) -> Tuple[str, float]:
    """
    Detect the type of query using rule-based patterns.
    
    Returns:
        Tuple of (query_type, confidence)
        query_type: 'drug_status', 'alternatives', 'list_filter'
        confidence: 0-100
    """
    query_lower = query.lower()
    
    # Check for alternatives query
    alternatives_patterns = [
        r'\b(alternative|alternatives|instead|other options?|replace|replacement)\b',
        r'\b(what else|other .+ like)\b',
        r'\b(preferred .+ in .+ category)\b',
    ]
    
    for pattern in alternatives_patterns:
        if re.search(pattern, query_lower):
            return 'alternatives', 90
    
    # Check for list/filter query
    list_patterns = [
        r'\b(list|show all|give all|display all|filter)\b',
        r'\b(all .+ drugs?|all .+ medications?)\b',
        r'\b(what are .+ drugs?)\b',
        r'\b(non.?preferred .+ (with|that have|having) .+ preferred)\b',
    ]
    
    for pattern in list_patterns:
        if re.search(pattern, query_lower):
            return 'list_filter', 85
    
    # Check for drug status query
    status_patterns = [
        r'\b(is .+ preferred)\b',
        r'\b(is .+ non.?preferred)\b',
        r'\b(does .+ require)\b',
        r'\b(pa for|prior auth)',
        r'\b(mnd for|medical necessity)\b',
        r'\b(status of)\b',
        r'\b(what.?s the status)\b',
    ]
    
    for pattern in status_patterns:
        if re.search(pattern, query_lower):
            return 'drug_status', 85
    
    # Default to drug_status with low confidence
    return 'drug_status', 30


def extract_filters(query: str) -> Dict[str, Any]:
    """
    Extract filter criteria from query using rule-based patterns.
    
    Returns:
        Dictionary with possible keys:
        - drug_status: 'preferred' | 'non_preferred' | None (None means all statuses)
        - pa_required: 'yes' | 'no'
        - mnd_required: 'yes' | 'no'
        - category: category name
    """
    query_lower = query.lower()
    filters = {}
    
    # Drug status - detect "both", "all", or specific status
    # Check for edge case: non-preferred drugs with preferred alternatives
    if re.search(r'\b(non.?preferred|not preferred)\b.*\b(with|that have|having)\b.*\b(preferred)\b', query_lower):
        filters['drug_status'] = 'non_preferred'
        filters['has_preferred_alternative'] = True
    # Check for "both" or "all" keywords which mean no filter
    elif re.search(r'\b(both|all)\b.*\b(preferred|non.?preferred)', query_lower):
        # User wants both preferred and non-preferred - don't set filter
        pass
    # Check for explicit "only preferred" or "just preferred"
    elif re.search(r'\b(only|just|exclusively)\s+(preferred)\b', query_lower) and not re.search(r'\b(non.?preferred)\b', query_lower):
        filters['drug_status'] = 'preferred'
    # Check for "preferred" but NOT in context of "non-preferred"
    # Also exclude if it's part of "alternatives" query without status specification
    elif re.search(r'\b(preferred)\b', query_lower) and not re.search(r'\b(non.?preferred)\b', query_lower):
        # Only set filter if "preferred" is used as a status indicator, not just in "alternatives"
        # Check if query is asking for alternatives without specifying status
        if not re.search(r'\b(alternative|alternatives|instead|other options?|replace|replacement)\b.*\bto\b', query_lower) or \
           re.search(r'\b(preferred\s+(alternative|drug|medication|option))', query_lower):
            filters['drug_status'] = 'preferred'
    elif re.search(r'\b(non.?preferred|not preferred)\b', query_lower):
        filters['drug_status'] = 'non_preferred'
    
    # PA/MND required (combined)
    if re.search(r'\b(pa|prior auth|preauth|pre.?auth|prior authorization|mnd|medical necessity)\b', query_lower):
        if re.search(r'\b(requires?|requiring|need|needed)\b', query_lower):
            filters['pa_mnd_required'] = 'yes'
        elif re.search(r'\b(no pa|without pa|doesn.?t require|no mnd|without mnd)\b', query_lower):
            filters['pa_mnd_required'] = 'no'
    
    # Category detection
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if re.search(r'\b' + re.escape(keyword) + r'\b', query_lower):
                filters['category'] = category
                break
        if 'category' in filters:
            break
    
    return filters


def validate_filters(filters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and sanitize filter values.
    Remove invalid or unknown values.
    """
    valid_filters = {}
    
    # Validate drug_status
    if 'drug_status' in filters:
        if filters['drug_status'] in ['preferred', 'non_preferred', 'not_listed']:
            valid_filters['drug_status'] = filters['drug_status']
    
    # Validate pa_mnd_required
    if 'pa_mnd_required' in filters:
        if filters['pa_mnd_required'] in ['yes', 'no', 'unknown']:
            valid_filters['pa_mnd_required'] = filters['pa_mnd_required']
    
    # Category - keep as-is (will be validated against DB)
    if 'category' in filters:
        valid_filters['category'] = filters['category']
    
    # HCPCS
    if 'hcpcs' in filters:
        valid_filters['hcpcs'] = filters['hcpcs']
    
    # Manufacturer
    if 'manufacturer' in filters:
        valid_filters['manufacturer'] = filters['manufacturer']
    
    # has_preferred_alternative (special filter for edge case)
    if 'has_preferred_alternative' in filters:
        valid_filters['has_preferred_alternative'] = filters['has_preferred_alternative']
    
    return valid_filters


def parse_query_rules_based(query: str, all_drug_names: list) -> Dict[str, Any]:
    """
    Parse user query using rule-based logic.
    
    Returns:
        Dictionary with:
        - query_type: 'drug_status' | 'alternatives' | 'list_filter'
        - confidence: 0-100
        - drug_name: extracted drug name (if applicable)
        - drug_confidence: confidence in drug name extraction
        - filters: extracted filter criteria
        - method: 'rule_based'
    """
    query_type, type_confidence = detect_query_type(query)
    filters = extract_filters(query)
    
    # Try to extract drug name if relevant
    drug_name = None
    drug_confidence = 0
    
    if query_type in ['drug_status', 'alternatives']:
        drug_name, drug_confidence, _ = extract_drug_name_from_query(query, all_drug_names)
    
    return {
        'query_type': query_type,
        'confidence': type_confidence,
        'drug_name': drug_name,
        'drug_confidence': drug_confidence,
        'filters': validate_filters(filters),
        'method': 'rule_based'
    }


def should_use_llm_fallback(parse_result: Dict[str, Any]) -> bool:
    """
    Determine if LLM fallback is needed based on rule-based parsing confidence.
    
    Use LLM fallback if:
    - Query type confidence < 70
    - Drug name needed but confidence < 70
    """
    if parse_result['confidence'] < 70:
        return True
    
    if parse_result['query_type'] in ['drug_status', 'alternatives']:
        if not parse_result['drug_name'] or parse_result['drug_confidence'] < 70:
            return True
    
    return False
