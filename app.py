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
    get_all_categories,
    fuzzy_search_drug_db,
    autocomplete_drug_search,
    suggest_corrections
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
    if 'autocomplete_suggestions' not in st.session_state:
        st.session_state.autocomplete_suggestions = []
    if 'selected_drug' not in st.session_state:
        st.session_state.selected_drug = None


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
        
        # Pass drug_status filter if specified (None means all statuses)
        drug_status_filter = filters.get('drug_status') if filters else None
        return fetch_alternatives(drug_name, drug_status_filter)
    
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
    
    # Format categories array as comma-separated string
    if 'categories' in df.columns:
        df['categories'] = df['categories'].apply(
            lambda x: ', '.join(x) if isinstance(x, list) and x else 'N/A'
        )
    
    # Remove internal fuzzy match columns if present
    columns_to_drop = ['_fuzzy_match', '_fuzzy_confidence', '_original_query']
    df = df.drop(columns=[col for col in columns_to_drop if col in df.columns])
    
    # Reorder columns for better readability
    preferred_order = [
        'drug_name', 'drug_status', 'categories', 
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
    Main query processing pipeline with lazy loading optimization.
    
    Args:
        query: User's natural language query
    """
    if not query or not query.strip():
        st.warning("Please enter a query.")
        return
    
    # Create a container for processing status
    status_container = st.empty()
    
    try:
        # Step 1: Parse query using rule-based approach (NO drug name loading yet)
        status_container.info("🔍 Understanding your query...")
        
        # Lazy loading: Only fetch drug names if needed for fuzzy matching
        all_drug_names = None
        
        # Initial parse without drug names (for query type detection)
        from utils.intent import detect_query_type, extract_filters
        query_type, type_confidence = detect_query_type(query)
        filters = extract_filters(query)
        
        parsed_intent = {
            'query_type': query_type,
            'confidence': type_confidence,
            'drug_name': None,
            'drug_confidence': 0,
            'filters': filters,
            'method': 'rule_based'
        }
        
        # Step 2: Only load drug names if we need to extract a drug name
        if query_type in ['drug_status', 'alternatives']:
            # Try database-side fuzzy search first (more efficient)
            from utils.fuzzy import extract_drug_name_from_query
            
            # Quick extraction attempt without full list
            potential_drug = extract_drug_name_from_query(query, [])
            if potential_drug and potential_drug[0]:
                # Try DB-side fuzzy search
                db_matches = fuzzy_search_drug_db(potential_drug[0], limit=3)
                
                if db_matches and db_matches[0][1] >= 70:
                    # Found good match using DB search
                    parsed_intent['drug_name'] = db_matches[0][0]
                    parsed_intent['drug_confidence'] = db_matches[0][1]
                    
                    # Show "Did you mean?" if confidence is between 70-90
                    if 70 <= db_matches[0][1] < 90 and len(db_matches) > 1:
                        suggestions = [name for name, score in db_matches[:3]]
                        st.info(f"💡 Did you mean: {', '.join(suggestions)}?")
                else:
                    # Fallback to loading all names for client-side fuzzy matching
                    status_container.info("🔍 Loading drug database for fuzzy matching...")
                    all_drug_names = fetch_all_drug_names()
                    drug_name, drug_confidence, _ = extract_drug_name_from_query(query, all_drug_names)
                    parsed_intent['drug_name'] = drug_name
                    parsed_intent['drug_confidence'] = drug_confidence
                    
                    # Show "Did you mean?" suggestions
                    if drug_name and drug_confidence < 90:
                        suggestions = suggest_corrections(query, threshold=0.7, limit=3)
                        if suggestions:
                            suggestion_names = [name for name, _ in suggestions[:3] if name != drug_name]
                            if suggestion_names:
                                st.info(f"💡 Did you mean: {', '.join(suggestion_names)}?")
        
        # Step 3: Check if LLM fallback is needed
        if should_use_llm_fallback(parsed_intent):
            status_container.info("🤖 Using AI to better understand your query...")
            
            # Load drug names if not already loaded
            if all_drug_names is None:
                all_drug_names = fetch_all_drug_names()
            
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
        status_container.info("🔎 Searching database...")
        results = execute_query(parsed_intent)
        
        # Step 5: Generate answer with LLM (always use LLM for consistent, high-quality answers)
        status_container.info("✨ Generating answer...")
        answer = generate_answer_with_llm(
            query=query,
            query_type=parsed_intent['query_type'],
            results=results,
            context={
                'intent': parsed_intent,
                'filters': parsed_intent.get('filters', {}),
                'drug_name': parsed_intent.get('drug_name'),
                'confidence': parsed_intent.get('confidence', 0)
            }
        )
        
        # Clear status
        status_container.empty()
        
        # Display answer
        st.markdown("### Answer")
        st.markdown(answer)
        
        # Display results table for drug lists
        if results and (len(results) > 1 or parsed_intent['query_type'] == 'list_filter'):
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
    
    # Autocomplete drug search (optional quick lookup)
    with st.expander("🔍 Quick Drug Lookup (Autocomplete)", expanded=False):
        autocomplete_query = st.text_input(
            "Start typing a drug name:",
            key="autocomplete_input",
            placeholder="e.g., Remi...",
            help="Get quick suggestions as you type"
        )
        
        if autocomplete_query and len(autocomplete_query) >= 2:
            suggestions = autocomplete_drug_search(autocomplete_query, limit=10)
            if suggestions:
                st.markdown("**Suggestions:**")
                cols = st.columns(2)
                for idx, drug in enumerate(suggestions):
                    col_idx = idx % 2
                    with cols[col_idx]:
                        status_text = "preferred" if drug.get('drug_status') == 'preferred' else "non-preferred"
                        if st.button(
                            f"{drug['drug_name']} ({drug.get('category', 'N/A')}, {status_text})",
                            key=f"autocomplete_{idx}",
                            use_container_width=True
                        ):
                            st.session_state.selected_drug = drug['drug_name']
                            st.rerun()
            else:
                st.info("No suggestions found. Try a different spelling.")
    
    # If a drug was selected from autocomplete, pre-fill the query
    default_query = ""
    if st.session_state.selected_drug:
        default_query = f"What is the status of {st.session_state.selected_drug}?"
        st.session_state.selected_drug = None  # Reset after use
    
    # Query input
    col1, col2 = st.columns([4, 1])
    
    with col1:
        query = st.text_input(
            "Enter your question:",
            value=default_query,
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
