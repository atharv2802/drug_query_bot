"""
Drug Status & Prior Authorization Assistant
Main Streamlit Application
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any, List, Optional

# Import utility modules
from utils.db import (
    fetch_drug_by_name,
    fetch_alternatives,
    filter_drugs,
    fetch_all_drug_names,
    get_all_categories
)
from utils.intent import (
    parse_query_rules_based,
    should_use_llm_fallback,
    validate_filters
)
from utils.llm import (
    extract_intent_with_llm,
    generate_answer_with_llm
)


# Page configuration
st.set_page_config(
    page_title="Drug Query Assistant",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed"
)


def init_session_state():
    """Initialize session state variables."""
    if 'debug_mode' not in st.session_state:
        st.session_state.debug_mode = False
    if 'query_history' not in st.session_state:
        st.session_state.query_history = []


def display_header():
    """Display the application header."""
    st.title("Drug Status & Prior Authorization Assistant")
    st.markdown("""
    This assistant helps you look up:
    - Drug preferred/non-preferred status
    - Prior Authorization (PA) / Medical Necessity Determination (MND) requirements
    - Preferred alternatives within drug categories
    - Filtered lists of drugs by various criteria
    """)
    st.divider()


def execute_query(parsed_intent: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Execute database query based on parsed intent.
    
    Args:
        parsed_intent: Dictionary with query_type, drug_name, and filters
        
    Returns:
        List of drug dictionaries from database
    """
    query_type = parsed_intent['query_type']
    drug_name = parsed_intent.get('drug_name')
    filters = parsed_intent.get('filters', {})
    
    if query_type == 'drug_status':
        if not drug_name:
            st.warning("Could not identify a drug name in your query.")
            return []
        
        result = fetch_drug_by_name(drug_name)
        return [result] if result else []
    
    elif query_type == 'alternatives':
        if not drug_name:
            st.warning("Could not identify a drug name to find alternatives for.")
            return []
        
        return fetch_alternatives(drug_name)
    
    elif query_type == 'list_filter':
        return filter_drugs(filters)
    
    return []


def display_results_table(results: List[Dict[str, Any]]):
    """Display results in a formatted table."""
    if not results:
        st.info("No results found.")
        return
    
    # Convert to DataFrame for better display
    df = pd.DataFrame(results)
    
    # Remove internal fuzzy match columns if present
    columns_to_drop = ['_fuzzy_match', '_fuzzy_confidence', '_original_query']
    df = df.drop(columns=[col for col in columns_to_drop if col in df.columns])
    
    # Reorder columns for better readability
    preferred_order = [
        'drug_name', 'drug_status', 'category', 
        'pa_required', 'mnd_required', 
        'hcpcs', 'manufacturer', 'notes'
    ]
    
    available_columns = [col for col in preferred_order if col in df.columns]
    other_columns = [col for col in df.columns if col not in available_columns]
    final_columns = available_columns + other_columns
    
    df = df[final_columns]
    
    # Display table
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )


def display_debug_info(parsed_intent: Dict[str, Any], results: List[Dict[str, Any]]):
    """Display debug information in an expander."""
    with st.expander("Debug Information", expanded=False):
        st.subheader("Parsed Intent")
        st.json(parsed_intent)
        
        st.subheader("Database Results")
        st.json(results)
        
        if results and results[0].get('_fuzzy_match'):
            st.subheader("Fuzzy Match Details")
            st.write(f"**Original Query:** {results[0].get('_original_query')}")
            st.write(f"**Matched Drug:** {results[0].get('drug_name')}")
            st.write(f"**Confidence:** {results[0].get('_fuzzy_confidence')}%")


def process_query(query: str):
    """
    Main query processing pipeline.
    
    Args:
        query: User's natural language query
    """
    if not query or not query.strip():
        st.warning("Please enter a query.")
        return
    
    # Create a container for processing status
    status_container = st.empty()
    
    try:
        # Step 1: Fetch all drug names for fuzzy matching
        status_container.info("🔍 Understanding your query...")
        all_drug_names = fetch_all_drug_names()
        
        # Step 2: Parse query using rule-based approach
        parsed_intent = parse_query_rules_based(query, all_drug_names)
        
        # Step 3: Check if LLM fallback is needed
        if should_use_llm_fallback(parsed_intent):
            status_container.info(" Using AI to better understand your query...")
            llm_intent = extract_intent_with_llm(query, all_drug_names)
            
            if llm_intent:
                # Merge LLM results with rule-based results
                if llm_intent.get('drug_name') and not parsed_intent.get('drug_name'):
                    parsed_intent['drug_name'] = llm_intent['drug_name']
                
                if llm_intent.get('query_type'):
                    parsed_intent['query_type'] = llm_intent['query_type']
                
                if llm_intent.get('filters'):
                    parsed_intent['filters'].update(llm_intent['filters'])
        
        # Step 4: Execute database query
        status_container.info(" Searching database...")
        results = execute_query(parsed_intent)
        
        # Step 5: Generate answer with LLM
        status_container.info(" Formatting answer...")
        answer = generate_answer_with_llm(
            query=query,
            query_type=parsed_intent['query_type'],
            results=results
        )
        
        # Clear status
        status_container.empty()
        
        # Display answer
        st.markdown("### Answer")
        st.markdown(answer)
        
        # Display results table only if more than 10 results
        if results and len(results) > 10:
            st.markdown("### Detailed Results")
            display_results_table(results)
        
        # Display debug info if enabled
        if st.session_state.debug_mode:
            display_debug_info(parsed_intent, results)
        
        # Add to query history
        st.session_state.query_history.append({
            'query': query,
            'intent': parsed_intent,
            'results_count': len(results)
        })
    
    except Exception as e:
        status_container.empty()
        st.error(f"An error occurred: {str(e)}")
        st.exception(e)


def main():
    """Main application entry point."""
    init_session_state()
    display_header()
    
    # Sidebar for settings
    with st.sidebar:
        st.header("Settings")
        st.session_state.debug_mode = st.checkbox(
            "Enable Debug Mode",
            value=st.session_state.debug_mode,
            help="Show detailed parsing and query information"
        )
        
        st.divider()
        st.subheader("Available Categories")
        try:
            categories = get_all_categories()
            for cat in categories:
                st.text(f"• {cat}")
        except:
            st.text("Connect to database to see categories")
        
        if st.session_state.query_history:
            st.divider()
            st.subheader("Query History")
            for i, item in enumerate(reversed(st.session_state.query_history[-5:]), 1):
                st.text(f"{i}. {item['query'][:50]}...")
    
    # Main query interface
    st.markdown("Ask a Question")
    
    # Query input
    col1, col2 = st.columns([4, 1])
    
    with col1:
        query = st.text_input(
            "Enter your question:",
            placeholder="e.g., Is Remicade preferred? Does it require PA?",
            label_visibility="collapsed"
        )
    
    with col2:
        submit_button = st.button("Submit", type="primary", use_container_width=True)
    
    # Process query on submit
    if submit_button and query:
        st.divider()
        process_query(query)
    
    # Footer
    st.divider()
    st.markdown("""
    <div style='text-align: center; color: #666; font-size: 0.8em;'>
    <p><strong>⚠️ Important Notice</strong></p>
    <p>This tool provides information from official drug lists only. 
    It does NOT provide medical advice, clinical recommendations, or coverage predictions.</p>
    <p>Always consult with healthcare professionals for medical decisions.</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
