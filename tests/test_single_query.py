"""
Single Query Test with Detailed Logging

This script runs a single user query through the entire pipeline with comprehensive logging
to show exactly what happens at each step.

Usage:
    python tests/test_single_query.py "Your query here"
    python tests/test_single_query.py "Is Remicade preferred?"
    python tests/test_single_query.py "List all generic preferred drugs for Antiemetics"
"""

import sys
import os
import json
from datetime import datetime
from typing import Dict, Any, List

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up environment variables from secrets if needed
secrets_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.streamlit', 'secrets.toml')
if os.path.exists(secrets_path):
    with open(secrets_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"')
                if key in ['SUPABASE_URL', 'SUPABASE_KEY', 'OPENROUTER_API_KEY']:
                    os.environ[key] = value

from utils.db import (
    fetch_all_drug_names,
    fetch_drug_by_name,
    fetch_alternatives,
    filter_drugs
)
from utils.intent import (
    parse_query_rules_based,
    should_use_llm_fallback
)
from utils.llm import (
    extract_intent_with_llm,
    generate_answer_with_llm
)


class QueryLogger:
    """Logger for tracking query pipeline execution."""
    
    def __init__(self):
        self.logs = []
        self.start_time = datetime.now()
        
    def log(self, step: str, data: Any, level: str = "INFO"):
        """Log a pipeline step."""
        timestamp = datetime.now()
        elapsed = (timestamp - self.start_time).total_seconds()
        
        log_entry = {
            "timestamp": timestamp.isoformat(),
            "elapsed_seconds": round(elapsed, 3),
            "level": level,
            "step": step,
            "data": data
        }
        self.logs.append(log_entry)
        
        # Print to console
        print(f"\n{'='*80}")
        print(f"[{elapsed:.3f}s] {level}: {step}")
        print('='*80)
        
        if isinstance(data, (dict, list)):
            print(json.dumps(data, indent=2, default=str))
        else:
            print(data)
    
    def save_to_file(self, query: str):
        """Save logs to a file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"query_log_{timestamp}.json"
        
        output = {
            "query": query,
            "total_time_seconds": (datetime.now() - self.start_time).total_seconds(),
            "logs": self.logs
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dumps(output, f, indent=2, default=str)
        
        print(f"\n{'='*80}")
        print(f"✅ Logs saved to: {filename}")
        print('='*80)


def execute_query(query: str, logger: QueryLogger) -> Dict[str, Any]:
    """
    Execute a single query through the entire pipeline with detailed logging.
    
    Args:
        query: User's natural language query
        logger: QueryLogger instance for tracking execution
        
    Returns:
        Dictionary with final results and metadata
    """
    
    # Step 1: Log the input query
    logger.log("INPUT QUERY", {
        "query": query,
        "length": len(query),
        "words": len(query.split())
    })
    
    # Step 2: Fetch all drug names for fuzzy matching
    logger.log("FETCHING DRUG NAMES", "Loading all drug names from database...")
    try:
        all_drug_names = fetch_all_drug_names()
        logger.log("DRUG NAMES LOADED", {
            "total_drugs": len(all_drug_names),
            "sample_drugs": all_drug_names[:5] if all_drug_names else []
        })
    except Exception as e:
        logger.log("ERROR", f"Failed to fetch drug names: {str(e)}", "ERROR")
        return {"error": str(e), "step": "fetch_drug_names"}
    
    # Step 3: Rule-based intent parsing
    logger.log("RULE-BASED PARSING", "Attempting rule-based intent extraction...")
    try:
        parsed_intent = parse_query_rules_based(query, all_drug_names)
        logger.log("RULE-BASED RESULT", {
            "query_type": parsed_intent.get('query_type'),
            "drug_name": parsed_intent.get('drug_name'),
            "filters": parsed_intent.get('filters', {}),
            "confidence": parsed_intent.get('confidence', 'medium')
        })
    except Exception as e:
        logger.log("ERROR", f"Rule-based parsing failed: {str(e)}", "ERROR")
        parsed_intent = {'query_type': None, 'filters': {}}
    
    # Step 4: Check if LLM fallback is needed
    use_llm = should_use_llm_fallback(parsed_intent)
    logger.log("LLM FALLBACK CHECK", {
        "use_llm": use_llm,
        "reason": "Low confidence or ambiguous intent" if use_llm else "Rule-based parsing sufficient"
    })
    
    # Step 5: LLM intent extraction (if needed)
    if use_llm:
        logger.log("LLM INTENT EXTRACTION", "Calling OpenRouter API for intent extraction...")
        try:
            llm_intent = extract_intent_with_llm(query, all_drug_names)
            logger.log("LLM RAW RESPONSE", {
                "query_type": llm_intent.get('query_type'),
                "drug_name": llm_intent.get('drug_name'),
                "filters": llm_intent.get('filters', {})
            })
            
            # Merge LLM results with rule-based
            if llm_intent.get('drug_name') and not parsed_intent.get('drug_name'):
                parsed_intent['drug_name'] = llm_intent['drug_name']
            if llm_intent.get('query_type'):
                parsed_intent['query_type'] = llm_intent['query_type']
            if llm_intent.get('filters'):
                parsed_intent['filters'].update(llm_intent['filters'])
            
            logger.log("MERGED INTENT", {
                "query_type": parsed_intent.get('query_type'),
                "drug_name": parsed_intent.get('drug_name'),
                "filters": parsed_intent.get('filters', {})
            })
        except Exception as e:
            logger.log("WARNING", f"LLM extraction failed, using rule-based only: {str(e)}", "WARNING")
    
    # Step 6: Execute database query based on intent
    logger.log("DATABASE QUERY", {
        "query_type": parsed_intent['query_type'],
        "parameters": {
            "drug_name": parsed_intent.get('drug_name'),
            "filters": parsed_intent.get('filters', {})
        }
    })
    
    results = []
    try:
        if parsed_intent['query_type'] == 'drug_status':
            if parsed_intent.get('drug_name'):
                result = fetch_drug_by_name(parsed_intent['drug_name'])
                results = [result] if result else []
                logger.log("DB QUERY: DRUG_STATUS", {
                    "method": "fetch_drug_by_name",
                    "drug_name": parsed_intent['drug_name'],
                    "found": bool(result),
                    "fuzzy_match": result.get('_fuzzy_match', False) if result else False
                })
        
        elif parsed_intent['query_type'] == 'alternatives':
            if parsed_intent.get('drug_name'):
                # Pass drug_status filter if specified (None means all statuses)
                drug_status_filter = parsed_intent.get('filters', {}).get('drug_status')
                results = fetch_alternatives(parsed_intent['drug_name'], drug_status_filter)
                logger.log("DB QUERY: ALTERNATIVES", {
                    "method": "fetch_alternatives",
                    "drug_name": parsed_intent['drug_name'],
                    "drug_status_filter": drug_status_filter if drug_status_filter else "all statuses",
                    "alternatives_found": len(results)
                })
        
        elif parsed_intent['query_type'] == 'list_filter':
            results = filter_drugs(parsed_intent.get('filters', {}))
            logger.log("DB QUERY: LIST_FILTER", {
                "method": "filter_drugs",
                "filters": parsed_intent.get('filters', {}),
                "results_count": len(results)
            })
        
        else:
            logger.log("WARNING", "Unknown query type, no database query executed", "WARNING")
    
    except Exception as e:
        logger.log("ERROR", f"Database query failed: {str(e)}", "ERROR")
        return {"error": str(e), "step": "database_query"}
    
    # Step 7: Log raw database results
    logger.log("RAW DATABASE RESULTS", {
        "count": len(results),
        "results": results[:5] if len(results) > 5 else results  # Show first 5 or all if less
    })
    
    if len(results) > 5:
        logger.log("RESULTS SUMMARY", {
            "total_count": len(results),
            "showing": "First 5 results above, see full results in final answer"
        })
    
    # Step 8: Generate LLM answer
    logger.log("LLM ANSWER GENERATION", "Generating natural language answer...")
    try:
        answer = generate_answer_with_llm(
            query=query,
            query_type=parsed_intent['query_type'],
            results=results
        )
        logger.log("LLM GENERATED ANSWER", {
            "answer_length": len(answer),
            "answer": answer
        })
    except Exception as e:
        logger.log("WARNING", f"LLM answer generation failed: {str(e)}", "WARNING")
        answer = f"Found {len(results)} result(s)."
    
    # Step 9: Final output
    final_output = {
        "query": query,
        "parsed_intent": parsed_intent,
        "results_count": len(results),
        "results": results,
        "answer": answer
    }
    
    logger.log("FINAL OUTPUT", final_output)
    
    return final_output


def main():
    """Main entry point."""
    print("\n" + "="*80)
    print("🔍 SINGLE QUERY TEST WITH DETAILED LOGGING")
    print("="*80)
    
    # Get query from command line or prompt
    if len(sys.argv) > 1:
        query = ' '.join(sys.argv[1:])
    else:
        query = input("\nEnter your query: ").strip()
    
    if not query:
        print("❌ No query provided. Exiting.")
        sys.exit(1)
    
    # Initialize logger
    logger = QueryLogger()
    
    # Execute query
    try:
        result = execute_query(query, logger)
        
        # Print summary
        print("\n" + "="*80)
        print("📊 EXECUTION SUMMARY")
        print("="*80)
        print(f"Query: {query}")
        print(f"Query Type: {result.get('parsed_intent', {}).get('query_type')}")
        print(f"Results Found: {result.get('results_count')}")
        print(f"Total Time: {(datetime.now() - logger.start_time).total_seconds():.3f}s")
        print(f"Steps Executed: {len(logger.logs)}")
        print("="*80)
        
        # Save logs
        # logger.save_to_file(query)  # Uncomment to save logs to file
        
    except Exception as e:
        logger.log("FATAL ERROR", str(e), "ERROR")
        print(f"\n❌ Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
