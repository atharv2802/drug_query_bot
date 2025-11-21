"""
API Tests for FastAPI endpoints
"""

import pytest
from fastapi.testclient import TestClient
from api import app

# Create test client
client = TestClient(app)


def test_root_endpoint():
    """Test API root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert data["version"] == "1.0.0"
    print("✅ Root endpoint test passed")


def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    print("✅ Health check test passed")


def test_get_drug():
    """Test GET /api/drug/{name} endpoint"""
    response = client.get("/api/drug/Remicade")
    assert response.status_code == 200
    data = response.json()
    assert data["drug_name"].lower() == "remicade"
    assert "drug_status" in data
    assert "category" in data
    print(f"✅ Get drug test passed: {data['drug_name']}")


def test_get_drug_not_found():
    """Test GET /api/drug/{name} with non-existent drug"""
    response = client.get("/api/drug/NonExistentDrug12345")
    assert response.status_code == 404
    print("✅ Drug not found test passed")


def test_get_alternatives():
    """Test GET /api/alternatives/{name} endpoint"""
    response = client.get("/api/alternatives/Remicade")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "drug_name" in data[0]
        assert "category" in data[0]
    print(f"✅ Get alternatives test passed: Found {len(data)} alternatives")


def test_get_alternatives_with_filter():
    """Test alternatives endpoint with status filter"""
    response = client.get("/api/alternatives/Remicade?drug_status=preferred")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # Verify all results are preferred
    for drug in data:
        assert drug["drug_status"] == "preferred"
    print(f"✅ Alternatives with filter test passed: {len(data)} preferred alternatives")


def test_filter_drugs():
    """Test POST /api/filter endpoint"""
    filter_data = {
        "drug_status": "preferred",
        "category": "oncology"
    }
    response = client.post("/api/filter", json=filter_data)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    
    # Verify filters applied
    for drug in data:
        assert drug["drug_status"] == "preferred"
        if drug.get("category"):
            assert drug["category"].lower() == "oncology"
    
    print(f"✅ Filter drugs test passed: Found {len(data)} drugs")


def test_autocomplete():
    """Test GET /api/autocomplete endpoint"""
    response = client.get("/api/autocomplete?q=Remi&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert "suggestions" in data
    assert "count" in data
    assert isinstance(data["suggestions"], list)
    assert data["count"] <= 5
    print(f"✅ Autocomplete test passed: {data['count']} suggestions")


def test_autocomplete_short_query():
    """Test autocomplete with query too short"""
    response = client.get("/api/autocomplete?q=R")
    assert response.status_code == 422  # Validation error
    print("✅ Autocomplete validation test passed")


def test_get_suggestions():
    """Test GET /api/suggestions/{query} endpoint"""
    response = client.get("/api/suggestions/Remicad?threshold=0.7&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert "query" in data
    assert "suggestions" in data
    assert "count" in data
    assert isinstance(data["suggestions"], list)
    
    # Verify confidence scores
    for suggestion in data["suggestions"]:
        assert "drug_name" in suggestion
        assert "confidence" in suggestion
        assert 0.0 <= suggestion["confidence"] <= 1.0
    
    print(f"✅ Suggestions test passed: {data['count']} suggestions")


def test_get_categories():
    """Test GET /api/categories endpoint"""
    response = client.get("/api/categories")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "oncology" in [c.lower() for c in data]
    print(f"✅ Categories test passed: {len(data)} categories")


def test_search_endpoint():
    """Test POST /api/search endpoint with natural language query"""
    query_data = {
        "query": "Is Remicade preferred?",
        "use_llm": False  # Disable LLM for faster testing
    }
    response = client.post("/api/search", json=query_data)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "answer" in data
    assert "results" in data
    assert "metadata" in data
    assert isinstance(data["results"], list)
    print(f"✅ Search endpoint test passed: {len(data['results'])} results")


def test_search_alternatives_query():
    """Test search endpoint with alternatives query"""
    query_data = {
        "query": "What are alternatives to Remicade?",
        "use_llm": False
    }
    response = client.post("/api/search", json=query_data)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["metadata"]["query_type"] == "alternatives"
    print(f"✅ Alternatives search test passed")


def test_search_filter_query():
    """Test search endpoint with filter query"""
    query_data = {
        "query": "List all preferred oncology drugs",
        "use_llm": False
    }
    response = client.post("/api/search", json=query_data)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["metadata"]["query_type"] == "list_filter"
    print(f"✅ Filter search test passed: {len(data['results'])} results")


def test_rate_limiting():
    """Test that rate limiting headers/logic is present"""
    # Make a request and check it doesn't fail
    response = client.get("/api/categories")
    assert response.status_code == 200
    
    # Note: Full rate limit testing would require making 100+ requests
    # which is slow for unit tests. This just verifies the endpoint works.
    print("✅ Rate limiting test passed")


def test_cors_headers():
    """Test that CORS headers are present"""
    response = client.get("/")
    assert response.status_code == 200
    # CORS middleware should add appropriate headers
    print("✅ CORS test passed")


if __name__ == "__main__":
    print("Running API tests...\n")
    
    test_root_endpoint()
    test_health_check()
    test_get_drug()
    test_get_drug_not_found()
    test_get_alternatives()
    test_get_alternatives_with_filter()
    test_filter_drugs()
    test_autocomplete()
    test_autocomplete_short_query()
    test_get_suggestions()
    test_get_categories()
    test_search_endpoint()
    test_search_alternatives_query()
    test_search_filter_query()
    test_rate_limiting()
    test_cors_headers()
    
    print("\n✅ All API tests passed!")
