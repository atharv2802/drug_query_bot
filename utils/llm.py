"""
LLM interactions via OpenRouter API.
Used for intent fallback and answer formatting.
"""

import json
import requests
from typing import Dict, Any, Optional
import streamlit as st
from config.prompts import (
    INTENT_EXTRACTION_PROMPT,
    ANSWER_GENERATION_PROMPT,
    INTENT_VALIDATION_PROMPT
)


def call_openrouter(
    prompt: str,
    model: str = "meta-llama/llama-3-70b-instruct",
    temperature: float = 0.1,
    max_tokens: int = 1000
) -> Optional[str]:
    """
    Call OpenRouter API with the given prompt.
    
    Args:
        prompt: The prompt to send
        model: Model identifier
        temperature: Sampling temperature (0-1)
        max_tokens: Maximum tokens to generate
        
    Returns:
        Generated text or None on error
    """
    import logging
    import time
    api_key = st.secrets["OPENROUTER_API_KEY"]
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://drug-query-assistant.streamlit.app",
        "X-Title": "Drug Query Assistant"
    }
    data = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            logging.error(f"OpenRouter API error (attempt {attempt}): {str(e)}")
            if st is not None:
                st.error(f"OpenRouter API error (attempt {attempt}): {str(e)}")
            if attempt < max_retries:
                time.sleep(2 * attempt)  # Exponential backoff
            else:
                return None


def extract_intent_with_llm(query: str, all_drug_names: list) -> Optional[Dict[str, Any]]:
    """
    Use LLM to extract intent from ambiguous query.
    Uses smaller, faster model (8B) for intent extraction to optimize costs and latency.
    
    Args:
        query: User's query
        all_drug_names: List of valid drug names (for reference)
        
    Returns:
        Dictionary with extracted intent or None on error
    """
    prompt = INTENT_EXTRACTION_PROMPT.format(query=query)
    
    # Use smaller model for intent extraction (faster and cheaper)
    response = call_openrouter(
        prompt, 
        model="meta-llama/llama-3.1-8b-instruct",  # Smaller model
        temperature=0.0, 
        max_tokens=500
    )
    if not response:
        return None
    try:
        # Extract JSON from response (handle cases where LLM adds explanation)
        response = response.strip()
        # Find first '{' and last '}' and extract JSON block
        start = response.find('{')
        end = response.rfind('}') + 1
        if start == -1 or end == -1:
            if st is not None:
                st.error("No JSON object found in LLM response.")
            return None
        json_str = response[start:end]
        intent = json.loads(json_str)
        # Validate structure
        required_keys = ['query_type', 'drug_name', 'filters']
        if not all(key in intent for key in required_keys):
            if st is not None:
                st.warning("LLM response missing required keys")
            return None
        # Validate values
        valid_query_types = ['drug_status', 'alternatives', 'list_filter']
        if intent['query_type'] not in valid_query_types:
            if st is not None:
                st.warning(f"Invalid query type from LLM: {intent['query_type']}")
            return None
        # Validate filters
        if 'drug_status' in intent['filters']:
            if intent['filters']['drug_status'] not in ['preferred', 'non_preferred', None]:
                intent['filters']['drug_status'] = None
        if 'pa_mnd_required' in intent['filters']:
            if intent['filters']['pa_mnd_required'] not in ['yes', 'no', None]:
                intent['filters']['pa_mnd_required'] = None
        return {
            'query_type': intent['query_type'],
            'drug_name': intent['drug_name'],
            'filters': intent['filters'],
            'confidence': 75,  # LLM fallback gets moderate confidence
            'method': 'llm_fallback'
        }
    except json.JSONDecodeError as e:
        if st is not None:
            st.error(f"Failed to parse LLM response as JSON: {str(e)}")
            st.text(f"Response was: {response}")
        return None
    except Exception as e:
        if st is not None:
            st.error(f"Error processing LLM intent: {str(e)}")
        return None


def generate_answer_with_llm(
    query: str,
    query_type: str,
    results: list,
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Generate a natural language answer using LLM with full context.
    
    Args:
        query: User's original query
        query_type: Type of query (drug_status, alternatives, list_filter)
        results: Database query results
        context: Optional additional context (intent, filters, confidence)
        
    Returns:
        Generated answer text
    """
    # Format intent and filters information
    intent_info = "Not available"
    if context:
        intent_parts = []
        if context.get('drug_name'):
            intent_parts.append(f"Drug Name: {context['drug_name']}")
        if context.get('filters'):
            filters = context['filters']
            if filters.get('drug_status'):
                intent_parts.append(f"Status Filter: {filters['drug_status']}")
            if filters.get('category'):
                intent_parts.append(f"Category Filter: {filters['category']}")
            if filters.get('pa_mnd_required'):
                intent_parts.append(f"PA/MND Filter: {filters['pa_mnd_required']}")
            if filters.get('manufacturer'):
                intent_parts.append(f"Manufacturer Filter: {filters['manufacturer']}")
            if filters.get('has_preferred_alternative'):
                intent_parts.append("Special Filter: Non-preferred drugs with preferred alternatives")
        if context.get('confidence'):
            intent_parts.append(f"Confidence: {context['confidence']}%")
        
        if intent_parts:
            intent_info = "\n".join(intent_parts)
    
    # Format results as readable text
    if not results:
        results_text = "No results found in the database."
    else:
        # Always show all results with full category information
        results_text = f"Database Results: {len(results)} drugs found.\n\n"
        
        for i, row in enumerate(results, 1):
            results_text += f"Drug {i}:\n"
            results_text += f"  Name: {row.get('drug_name', 'N/A')}\n"
            
            # Format categories with per-category status if available
            categories = row.get('categories', [])
            statuses_by_category = row.get('statuses_by_category', {})
            
            if isinstance(categories, list) and categories:
                if statuses_by_category:
                    # Show status for each category
                    category_info = []
                    for cat in categories:
                        status = statuses_by_category.get(cat, 'unknown')
                        category_info.append(f"{cat} ({status})")
                    results_text += f"  Categories: {', '.join(category_info)}\n"
                else:
                    # Fallback to just category names
                    results_text += f"  Categories: {', '.join(categories)}\n"
            else:
                results_text += f"  Categories: N/A\n"
            
            results_text += f"  Overall Status: {row.get('drug_status', 'N/A')}\n"
            results_text += f"  PA/MND Required: {row.get('pa_mnd_required', 'unknown')}\n"
            results_text += f"  HCPCS: {row.get('hcpcs', 'N/A')}\n"
            results_text += f"  Manufacturer: {row.get('manufacturer', 'N/A')}\n"
            if row.get('notes'):
                results_text += f"  Notes: {row['notes']}\n"
            results_text += "\n"
    
    prompt = ANSWER_GENERATION_PROMPT.format(
        query=query,
        query_type=query_type,
        intent_info=intent_info,
        results=results_text
    )
    
    # Use larger model for answer generation (better quality)
    response = call_openrouter(
        prompt, 
        model="meta-llama/llama-3-70b-instruct",  # Larger model for better answers
        temperature=0.2, 
        max_tokens=800
    )
    
    if response:
        return response
    else:
        # Fallback to basic formatting if LLM fails
        return format_answer_fallback(query, query_type, results)


def format_answer_fallback(query: str, query_type: str, results: list) -> str:
    """
    Fallback answer formatting if LLM is unavailable.
    Simple rule-based formatting.
    """
    if not results:
        return "I could not find any drugs matching your query in the provided lists."
    
    if query_type == 'drug_status':
        drug = results[0]
        answer = f"**{drug['drug_name']}**\n\n"
        answer += f"- **Status:** {drug['drug_status']}\n"
        answer += f"- **Category:** {drug.get('category', 'Not listed')}\n"
        answer += f"- **PA/MND Required:** {drug.get('pa_mnd_required', 'unknown')}\n"
        if drug.get('hcpcs'):
            answer += f"- **HCPCS:** {drug['hcpcs']}\n"
        if drug.get('manufacturer'):
            answer += f"- **Manufacturer:** {drug['manufacturer']}\n"
        return answer
    
    elif query_type == 'alternatives':
        if len(results) == 0:
            return "No preferred alternatives found in the same category."
        
        answer = f"Found {len(results)} preferred alternative(s):\n\n"
        for drug in results:
            answer += f"- **{drug['drug_name']}** ({drug.get('category', 'N/A')})\n"
        return answer
    
    elif query_type == 'list_filter':
        if len(results) > 10:
            # For large result sets, just show summary
            answer = f"Found {len(results)} drug(s) matching your criteria. See the table below for the complete list."
        else:
            # For small result sets, show the list
            answer = f"Found {len(results)} drug(s) matching your criteria:\n\n"
            for drug in results:
                answer += f"- **{drug['drug_name']}** - {drug['drug_status']}"
                if drug.get('pa_mnd_required') == 'yes':
                    answer += " (PA/MND required)"
                answer += "\n"
        return answer
    
    return "Results found. Please see the table below for details."
