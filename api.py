"""
FastAPI REST API for Drug Query Bot
Provides programmatic access to drug information and query functionality.
"""

from fastapi import FastAPI, HTTPException, Depends, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import os
from datetime import datetime
import time

# Import database and utility functions
from utils.db import (
    fetch_drug_by_name,
    fetch_alternatives,
    filter_drugs,
    fuzzy_search_drug_db,
    autocomplete_drug_search,
    suggest_corrections,
    get_all_categories
)
from utils.intent import parse_query_rules_based, extract_filters
from utils.llm import extract_intent_with_llm, generate_answer_with_llm


# Initialize FastAPI app
app = FastAPI(
    title="Drug Query API",
    description="REST API for querying drug status, alternatives, and formulary information",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Rate limiting storage (simple in-memory, use Redis for production)
request_counts = {}
RATE_LIMIT = 100  # requests per minute
RATE_WINDOW = 60  # seconds


# Pydantic models for request/response validation
class DrugQuery(BaseModel):
    """Request model for natural language drug queries"""
    query: str = Field(..., min_length=3, max_length=500, description="Natural language query")
    use_llm: bool = Field(default=True, description="Whether to use LLM for intent extraction and answer generation")


class DrugFilter(BaseModel):
    """Request model for filtering drugs"""
    drug_status: Optional[str] = Field(None, description="Filter by status: preferred, non_preferred, not_listed")
    category: Optional[str] = Field(None, description="Filter by category (e.g., oncology, immunology)")
    pa_mnd_required: Optional[str] = Field(None, description="Filter by PA/MND requirement: yes, no, unknown")
    manufacturer: Optional[str] = Field(None, description="Filter by manufacturer name")
    hcpcs: Optional[str] = Field(None, description="Filter by HCPCS code")


class DrugResponse(BaseModel):
    """Response model for drug information"""
    drug_name: str
    drug_status: str
    category: Optional[str]
    pa_mnd_required: Optional[str]
    hcpcs: Optional[str]
    manufacturer: Optional[str]
    notes: Optional[str]


class QueryResponse(BaseModel):
    """Response model for natural language queries"""
    success: bool
    query: str
    answer: str
    results: List[DrugResponse]
    metadata: Dict[str, Any]


class AutocompleteResponse(BaseModel):
    """Response model for autocomplete suggestions"""
    suggestions: List[Dict[str, str]]
    count: int


class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    detail: Optional[str] = None
    timestamp: str


# Authentication dependency
async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    """
    Verify API key for authentication.
    Set API_KEY environment variable or use Streamlit secrets.
    """
    # For development, allow requests without API key
    # In production, enforce API key validation
    if os.getenv("REQUIRE_API_KEY", "false").lower() == "true":
        expected_key = os.getenv("API_KEY")
        if not expected_key:
            raise HTTPException(status_code=500, detail="API key not configured")
        if x_api_key != expected_key:
            raise HTTPException(status_code=401, detail="Invalid API key")
    return True


# Rate limiting dependency
async def check_rate_limit(x_api_key: Optional[str] = Header(None)):
    """
    Simple rate limiting based on API key or IP.
    For production, use Redis or proper rate limiting library.
    """
    identifier = x_api_key or "anonymous"
    current_time = time.time()
    
    # Clean up old entries
    request_counts[identifier] = [
        timestamp for timestamp in request_counts.get(identifier, [])
        if current_time - timestamp < RATE_WINDOW
    ]
    
    # Check rate limit
    if len(request_counts.get(identifier, [])) >= RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {RATE_LIMIT} requests per {RATE_WINDOW} seconds"
        )
    
    # Record this request
    if identifier not in request_counts:
        request_counts[identifier] = []
    request_counts[identifier].append(current_time)
    
    return True


# API Endpoints

@app.get("/", tags=["General"])
async def root():
    """API root endpoint with basic information"""
    return {
        "name": "Drug Query API",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "docs": "/api/docs",
            "search": "/api/search",
            "drug": "/api/drug/{name}",
            "alternatives": "/api/alternatives/{name}",
            "filter": "/api/filter",
            "autocomplete": "/api/autocomplete",
            "categories": "/api/categories",
            "suggestions": "/api/suggestions/{query}"
        }
    }


@app.get("/health", tags=["General"])
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/api/search", response_model=QueryResponse, tags=["Query"])
async def search_drugs(
    query_data: DrugQuery,
    authenticated: bool = Depends(verify_api_key),
    rate_limited: bool = Depends(check_rate_limit)
):
    """
    Natural language search for drug information.
    
    Supports queries like:
    - "Is Remicade preferred?"
    - "What are alternatives to Mvasi?"
    - "List all oncology drugs requiring PA"
    """
    try:
        start_time = time.time()
        
        # Parse query
        all_drug_names = []  # Lazy loading
        from utils.intent import detect_query_type
        query_type, confidence = detect_query_type(query_data.query)
        filters = extract_filters(query_data.query)
        
        parsed_intent = {
            'query_type': query_type,
            'confidence': confidence,
            'drug_name': None,
            'filters': filters,
            'method': 'rule_based'
        }
        
        # Extract drug name if needed
        if query_type in ['drug_status', 'alternatives']:
            from utils.fuzzy import extract_drug_name_from_query
            
            # Try DB-side fuzzy search first
            potential_drug = extract_drug_name_from_query(query_data.query, [])
            if potential_drug and potential_drug[0]:
                db_matches = fuzzy_search_drug_db(potential_drug[0], limit=1)
                if db_matches and db_matches[0][1] >= 70:
                    parsed_intent['drug_name'] = db_matches[0][0]
        
        # Execute query
        if parsed_intent['query_type'] == 'drug_status':
            if not parsed_intent['drug_name']:
                raise HTTPException(status_code=400, detail="Could not identify drug name in query")
            result = fetch_drug_by_name(parsed_intent['drug_name'])
            results = [result] if result else []
        
        elif parsed_intent['query_type'] == 'alternatives':
            if not parsed_intent['drug_name']:
                raise HTTPException(status_code=400, detail="Could not identify drug name for alternatives")
            drug_status_filter = filters.get('drug_status')
            results = fetch_alternatives(parsed_intent['drug_name'], drug_status_filter)
        
        elif parsed_intent['query_type'] == 'list_filter':
            results = filter_drugs(filters)
        
        else:
            results = []
        
        # Generate answer
        answer = ""
        if query_data.use_llm:
            answer = generate_answer_with_llm(
                query=query_data.query,
                query_type=parsed_intent['query_type'],
                results=results
            )
        else:
            answer = f"Found {len(results)} result(s)"
        
        execution_time = time.time() - start_time
        
        return QueryResponse(
            success=True,
            query=query_data.query,
            answer=answer,
            results=[DrugResponse(**r) for r in results],
            metadata={
                "query_type": parsed_intent['query_type'],
                "results_count": len(results),
                "execution_time_ms": round(execution_time * 1000, 2),
                "llm_used": query_data.use_llm
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query processing failed: {str(e)}")


@app.get("/api/drug/{name}", response_model=DrugResponse, tags=["Drugs"])
async def get_drug(
    name: str,
    authenticated: bool = Depends(verify_api_key),
    rate_limited: bool = Depends(check_rate_limit)
):
    """
    Get detailed information about a specific drug by name.
    Supports fuzzy matching.
    """
    try:
        result = fetch_drug_by_name(name)
        if not result:
            raise HTTPException(status_code=404, detail=f"Drug '{name}' not found")
        return DrugResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/alternatives/{name}", response_model=List[DrugResponse], tags=["Drugs"])
async def get_alternatives(
    name: str,
    drug_status: Optional[str] = Query(None, description="Filter by status: preferred, non_preferred"),
    authenticated: bool = Depends(verify_api_key),
    rate_limited: bool = Depends(check_rate_limit)
):
    """
    Get alternative drugs in the same category.
    """
    try:
        results = fetch_alternatives(name, drug_status)
        if not results:
            return []
        return [DrugResponse(**r) for r in results]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/filter", response_model=List[DrugResponse], tags=["Drugs"])
async def filter_drugs_endpoint(
    filters: DrugFilter,
    authenticated: bool = Depends(verify_api_key),
    rate_limited: bool = Depends(check_rate_limit)
):
    """
    Filter drugs by multiple criteria.
    """
    try:
        # Convert Pydantic model to dict and remove None values
        filter_dict = {k: v for k, v in filters.dict().items() if v is not None}
        
        results = filter_drugs(filter_dict)
        return [DrugResponse(**r) for r in results]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/autocomplete", response_model=AutocompleteResponse, tags=["Search"])
async def autocomplete(
    q: str = Query(..., min_length=2, description="Search query (minimum 2 characters)"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of suggestions"),
    authenticated: bool = Depends(verify_api_key),
    rate_limited: bool = Depends(check_rate_limit)
):
    """
    Get autocomplete suggestions for drug names.
    """
    try:
        suggestions = autocomplete_drug_search(q, limit=limit)
        return AutocompleteResponse(
            suggestions=suggestions,
            count=len(suggestions)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/suggestions/{query}", tags=["Search"])
async def get_suggestions(
    query: str,
    threshold: float = Query(0.7, ge=0.0, le=1.0, description="Minimum similarity threshold"),
    limit: int = Query(5, ge=1, le=20, description="Maximum number of suggestions"),
    authenticated: bool = Depends(verify_api_key),
    rate_limited: bool = Depends(check_rate_limit)
):
    """
    Get spelling correction suggestions for drug names.
    """
    try:
        suggestions = suggest_corrections(query, threshold=threshold, limit=limit)
        return {
            "query": query,
            "suggestions": [
                {"drug_name": name, "confidence": round(score, 3)}
                for name, score in suggestions
            ],
            "count": len(suggestions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/categories", response_model=List[str], tags=["Metadata"])
async def get_categories(
    authenticated: bool = Depends(verify_api_key),
    rate_limited: bool = Depends(check_rate_limit)
):
    """
    Get all available drug categories.
    """
    try:
        categories = get_all_categories()
        return categories
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            timestamp=datetime.utcnow().isoformat()
        ).dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc),
            timestamp=datetime.utcnow().isoformat()
        ).dict()
    )


# Run with: uvicorn api:app --reload --port 8000
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
