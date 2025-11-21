"""Unit tests for utils/llm.py - LLM integration utilities."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json
from utils.llm import (
    call_openrouter,
    extract_intent_with_llm,
    generate_answer_with_llm,
    format_answer_fallback
)


class TestCallOpenRouter:
    """Test call_openrouter function."""
    
    @patch('utils.llm.requests.post')
    @patch('utils.llm.st')
    def test_successful_api_call(self, mock_st, mock_post):
        """Test successful OpenRouter API call."""
        mock_st.secrets = {"OPENROUTER_API_KEY": "test-key"}
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Test response"}}]
        }
        mock_post.return_value = mock_response
        
        result = call_openrouter("Test prompt")
        
        assert result == "Test response"
        mock_post.assert_called_once()
    
    @patch('utils.llm.requests.post')
    @patch('utils.llm.st')
    def test_api_failure_with_retry(self, mock_st, mock_post):
        """Test API failure with retry logic."""
        mock_st.secrets = {"OPENROUTER_API_KEY": "test-key"}
        mock_st.error = Mock()
        mock_post.side_effect = Exception("API Error")
        
        result = call_openrouter("Test prompt")
        
        assert result is None
        assert mock_post.call_count == 3  # Should retry 3 times
    
    @patch('utils.llm.requests.post')
    @patch('utils.llm.st')
    def test_custom_parameters(self, mock_st, mock_post):
        """Test custom model, temperature, and max_tokens."""
        mock_st.secrets = {"OPENROUTER_API_KEY": "test-key"}
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Response"}}]
        }
        mock_post.return_value = mock_response
        
        result = call_openrouter(
            "Test",
            model="custom-model",
            temperature=0.5,
            max_tokens=500
        )
        
        call_args = mock_post.call_args
        assert call_args[1]['json']['model'] == "custom-model"
        assert call_args[1]['json']['temperature'] == 0.5
        assert call_args[1]['json']['max_tokens'] == 500


class TestExtractIntentWithLLM:
    """Test extract_intent_with_llm function."""
    
    @patch('utils.llm.call_openrouter')
    def test_valid_intent_extraction(self, mock_call):
        """Test valid intent extraction."""
        mock_call.return_value = json.dumps({
            "query_type": "drug_status",
            "drug_name": "Keytruda",
            "filters": {
                "drug_status": "preferred",
                "pa_mnd_required": None,
                "category": None
            }
        })
        
        result = extract_intent_with_llm("Is Keytruda preferred?", [])
        
        assert result is not None
        assert result['query_type'] == 'drug_status'
        assert result['drug_name'] == 'Keytruda'
        assert result['method'] == 'llm_fallback'
    
    @patch('utils.llm.call_openrouter')
    def test_invalid_json_response(self, mock_call):
        """Test handling of invalid JSON response."""
        mock_call.return_value = "Not valid JSON"
        
        result = extract_intent_with_llm("Test query", [])
        
        assert result is None
    
    @patch('utils.llm.call_openrouter')
    def test_invalid_query_type(self, mock_call):
        """Test handling of invalid query type."""
        mock_call.return_value = json.dumps({
            "query_type": "invalid_type",
            "drug_name": None,
            "filters": {}
        })
        
        result = extract_intent_with_llm("Test query", [])
        
        assert result is None
    
    @patch('utils.llm.call_openrouter')
    def test_filter_validation(self, mock_call):
        """Test that invalid filter values are corrected."""
        mock_call.return_value = json.dumps({
            "query_type": "list_filter",
            "drug_name": None,
            "filters": {
                "drug_status": "invalid_status",
                "pa_mnd_required": "maybe",
                "category": "oncology"
            }
        })
        
        result = extract_intent_with_llm("Test query", [])
        
        assert result is not None
        assert result['filters']['drug_status'] is None
        assert result['filters']['pa_mnd_required'] is None
    
    @patch('utils.llm.call_openrouter')
    def test_api_failure(self, mock_call):
        """Test handling of API failure."""
        mock_call.return_value = None
        
        result = extract_intent_with_llm("Test query", [])
        
        assert result is None


class TestGenerateAnswerWithLLM:
    """Test generate_answer_with_llm function."""
    
    @patch('utils.llm.call_openrouter')
    def test_successful_answer_generation(self, mock_call):
        """Test successful answer generation."""
        mock_call.return_value = "Keytruda is a preferred oncology drug."
        
        result = generate_answer_with_llm(
            query="Is Keytruda preferred?",
            query_type="drug_status",
            results=[{'drug_name': 'Keytruda', 'drug_status': 'preferred'}]
        )
        
        assert "Keytruda" in result
    
    @patch('utils.llm.call_openrouter')
    def test_empty_results(self, mock_call):
        """Test answer generation with empty results."""
        mock_call.return_value = "No drugs found matching your criteria."
        
        result = generate_answer_with_llm(
            query="Test query",
            query_type="list_filter",
            results=[]
        )
        
        assert isinstance(result, str)
    
    @patch('utils.llm.call_openrouter')
    def test_fallback_on_llm_failure(self, mock_call):
        """Test fallback formatting when LLM fails."""
        mock_call.return_value = None
        
        result = generate_answer_with_llm(
            query="Is Keytruda preferred?",
            query_type="drug_status",
            results=[{'drug_name': 'Keytruda', 'drug_status': 'preferred'}]
        )
        
        assert isinstance(result, str)
        assert len(result) > 0


class TestFormatAnswerFallback:
    """Test format_answer_fallback function."""
    
    def test_drug_status_formatting(self):
        """Test formatting for drug status query."""
        results = [{
            'drug_name': 'Keytruda',
            'drug_status': 'preferred',
            'category': 'Oncology',
            'pa_mnd_required': 'yes'
        }]
        
        result = format_answer_fallback("query", "drug_status", results)
        
        assert "Keytruda" in result
        assert "preferred" in result
    
    def test_alternatives_formatting(self):
        """Test formatting for alternatives query."""
        results = [
            {'drug_name': 'Humira', 'category': 'Immunology'},
            {'drug_name': 'Simponi Aria', 'category': 'Immunology'}
        ]
        
        result = format_answer_fallback("query", "alternatives", results)
        
        assert "Humira" in result
        assert "Simponi Aria" in result
    
    def test_list_filter_formatting(self):
        """Test formatting for list/filter query."""
        results = [
            {'drug_name': 'Keytruda', 'drug_status': 'preferred', 'pa_mnd_required': 'yes'},
            {'drug_name': 'Humira', 'drug_status': 'preferred', 'pa_mnd_required': 'no'}
        ]
        
        result = format_answer_fallback("query", "list_filter", results)
        
        assert "Keytruda" in result
        assert "Humira" in result
    
    def test_empty_results(self):
        """Test formatting with no results."""
        result = format_answer_fallback("query", "drug_status", [])
        
        assert "could not find" in result.lower() or "no" in result.lower()
    
    def test_large_result_set_truncation(self):
        """Test that large result sets are truncated."""
        results = [{'drug_name': f'Drug{i}', 'drug_status': 'preferred'} for i in range(30)]
        
        result = format_answer_fallback("query", "list_filter", results)
        
        assert "more" in result.lower() or "table" in result.lower()
