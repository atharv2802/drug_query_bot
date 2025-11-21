"""Unit tests for utils/intent.py - Intent parsing utilities."""

import pytest
from utils.intent import (
    detect_query_type,
    extract_filters,
    validate_filters,
    parse_query_rules_based,
    should_use_llm_fallback,
    CATEGORY_KEYWORDS
)


class TestDetectQueryType:
    """Test detect_query_type function."""
    
    def test_alternatives_query(self):
        """Test detection of alternatives queries."""
        query_type, confidence = detect_query_type("What are alternatives to Remicade?")
        assert query_type == "alternatives"
        assert confidence == 90
        
        query_type, confidence = detect_query_type("Other drugs instead of Humira")
        assert query_type == "alternatives"
        assert confidence == 90
    
    def test_list_filter_query(self):
        """Test detection of list/filter queries."""
        query_type, confidence = detect_query_type("List all preferred oncology drugs")
        assert query_type == "list_filter"
        assert confidence == 85
        
        query_type, confidence = detect_query_type("Show all drugs requiring PA")
        assert query_type == "list_filter"
        assert confidence == 85
    
    def test_drug_status_query(self):
        """Test detection of drug status queries."""
        query_type, confidence = detect_query_type("Is Keytruda preferred?")
        assert query_type == "drug_status"
        assert confidence == 85
        
        query_type, confidence = detect_query_type("Does Remicade require PA?")
        assert query_type == "drug_status"
        assert confidence == 85
    
    def test_ambiguous_query(self):
        """Test detection of ambiguous queries."""
        query_type, confidence = detect_query_type("Tell me about Humira")
        assert query_type == "drug_status"
        assert confidence == 30
    
    def test_case_insensitive(self):
        """Test that detection is case-insensitive."""
        query_type, _ = detect_query_type("IS KEYTRUDA PREFERRED?")
        assert query_type == "drug_status"


class TestExtractFilters:
    """Test extract_filters function."""
    
    def test_extract_preferred_status(self):
        """Test extracting 'preferred' status."""
        filters = extract_filters("List all preferred drugs")
        assert filters.get('drug_status') == 'preferred'
    
    def test_extract_non_preferred_status(self):
        """Test extracting 'non-preferred' status."""
        filters = extract_filters("Show non-preferred drugs")
        assert filters.get('drug_status') == 'non_preferred'
        
        filters = extract_filters("not preferred drugs")
        assert filters.get('drug_status') == 'non_preferred'
    
    def test_extract_pa_required(self):
        """Test extracting PA/MND requirement."""
        filters = extract_filters("Drugs requiring PA")
        assert filters.get('pa_mnd_required') == 'yes'
        
        filters = extract_filters("Drugs requiring MND")
        assert filters.get('pa_mnd_required') == 'yes'
        
        filters = extract_filters("Drugs without PA")
        assert filters.get('pa_mnd_required') == 'no'
    
    def test_extract_category(self):
        """Test extracting category."""
        filters = extract_filters("List oncology drugs")
        assert filters.get('category') == 'oncology'
        
        filters = extract_filters("Show immunology medications")
        assert filters.get('category') == 'immunology'
    
    def test_multiple_filters(self):
        """Test extracting multiple filters."""
        filters = extract_filters("Preferred oncology drugs requiring PA")
        assert filters.get('drug_status') == 'preferred'
        assert filters.get('category') == 'oncology'
        assert filters.get('pa_mnd_required') == 'yes'
    
    def test_no_filters(self):
        """Test query with no filters."""
        filters = extract_filters("Tell me about drugs")
        assert len(filters) == 0


class TestValidateFilters:
    """Test validate_filters function."""
    
    def test_valid_drug_status(self):
        """Test validation of valid drug_status."""
        filters = {'drug_status': 'preferred'}
        validated = validate_filters(filters)
        assert validated['drug_status'] == 'preferred'
    
    def test_invalid_drug_status(self):
        """Test rejection of invalid drug_status."""
        filters = {'drug_status': 'invalid'}
        validated = validate_filters(filters)
        assert 'drug_status' not in validated
    
    def test_valid_pa_required(self):
        """Test validation of valid pa_mnd_required."""
        filters = {'pa_mnd_required': 'yes'}
        validated = validate_filters(filters)
        assert validated['pa_mnd_required'] == 'yes'
    
    def test_invalid_pa_required(self):
        """Test rejection of invalid pa_mnd_required."""
        filters = {'pa_mnd_required': 'maybe'}
        validated = validate_filters(filters)
        assert 'pa_mnd_required' not in validated
    
    def test_category_passthrough(self):
        """Test that category passes through validation."""
        filters = {'category': 'oncology'}
        validated = validate_filters(filters)
        assert validated['category'] == 'oncology'
    
    def test_multiple_valid_filters(self):
        """Test validation of multiple valid filters."""
        filters = {
            'drug_status': 'preferred',
            'pa_mnd_required': 'yes',
            'category': 'immunology'
        }
        validated = validate_filters(filters)
        assert len(validated) == 3


class TestParseQueryRulesBased:
    """Test parse_query_rules_based function."""
    
    def test_parse_drug_status_query(self, sample_drug_names):
        """Test parsing drug status query."""
        result = parse_query_rules_based("Is Keytruda preferred?", sample_drug_names)
        assert result['query_type'] == 'drug_status'
        assert result['drug_name'] == 'Keytruda'
        assert result['method'] == 'rule_based'
    
    def test_parse_alternatives_query(self, sample_drug_names):
        """Test parsing alternatives query."""
        result = parse_query_rules_based("Alternatives to Remicade", sample_drug_names)
        assert result['query_type'] == 'alternatives'
        assert result['drug_name'] == 'Remicade'
    
    def test_parse_list_query(self, sample_drug_names):
        """Test parsing list/filter query."""
        result = parse_query_rules_based("List all preferred oncology drugs", sample_drug_names)
        assert result['query_type'] == 'list_filter'
        assert result['filters'].get('drug_status') == 'preferred'
        assert result['filters'].get('category') == 'oncology'
    
    def test_confidence_scores(self, sample_drug_names):
        """Test that confidence scores are provided."""
        result = parse_query_rules_based("Is Humira preferred?", sample_drug_names)
        assert 'confidence' in result
        assert 'drug_confidence' in result


class TestShouldUseLLMFallback:
    """Test should_use_llm_fallback function."""
    
    def test_low_query_confidence(self):
        """Test LLM fallback for low query confidence."""
        parse_result = {
            'query_type': 'drug_status',
            'confidence': 50,
            'drug_name': 'Keytruda',
            'drug_confidence': 100
        }
        assert should_use_llm_fallback(parse_result) is True
    
    def test_low_drug_confidence(self):
        """Test LLM fallback for low drug confidence."""
        parse_result = {
            'query_type': 'drug_status',
            'confidence': 90,
            'drug_name': 'Keytruda',
            'drug_confidence': 50
        }
        assert should_use_llm_fallback(parse_result) is True
    
    def test_missing_drug_name(self):
        """Test LLM fallback for missing drug name."""
        parse_result = {
            'query_type': 'drug_status',
            'confidence': 90,
            'drug_name': None,
            'drug_confidence': 0
        }
        assert should_use_llm_fallback(parse_result) is True
    
    def test_high_confidence_no_fallback(self):
        """Test no LLM fallback for high confidence."""
        parse_result = {
            'query_type': 'drug_status',
            'confidence': 90,
            'drug_name': 'Keytruda',
            'drug_confidence': 100
        }
        assert should_use_llm_fallback(parse_result) is False
    
    def test_list_query_no_drug_needed(self):
        """Test no LLM fallback for list query without drug."""
        parse_result = {
            'query_type': 'list_filter',
            'confidence': 85,
            'drug_name': None,
            'drug_confidence': 0
        }
        assert should_use_llm_fallback(parse_result) is False


class TestCategoryKeywords:
    """Test CATEGORY_KEYWORDS constant."""
    
    def test_all_categories_present(self):
        """Test that expected categories are present."""
        expected_categories = [
            'oncology', 'immunology', 'rheumatology', 'dermatology',
            'gastroenterology', 'neurology', 'hematology', 'cardiology'
        ]
        for category in expected_categories:
            assert category in CATEGORY_KEYWORDS
    
    def test_keywords_are_lists(self):
        """Test that all category keywords are lists."""
        for keywords in CATEGORY_KEYWORDS.values():
            assert isinstance(keywords, list)
            assert len(keywords) > 0
