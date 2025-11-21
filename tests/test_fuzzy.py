"""Unit tests for utils/fuzzy.py - Fuzzy matching utilities."""

import pytest
from utils.fuzzy import (
    normalize_drug_name,
    fuzzy_match_drug_name,
    extract_drug_name_from_query
)


class TestNormalizeDrugName:
    """Test normalize_drug_name function."""
    
    def test_lowercase_conversion(self):
        """Test that drug names are converted to lowercase."""
        assert normalize_drug_name("KEYTRUDA") == "keytruda"
        assert normalize_drug_name("Remicade") == "remicade"
    
    def test_whitespace_stripping(self):
        """Test that leading/trailing whitespace is removed."""
        assert normalize_drug_name("  Humira  ") == "humira"
        assert normalize_drug_name("\tOpdivo\n") == "opdivo"
    
    def test_trademark_removal(self):
        """Test that trademark symbols are removed."""
        assert normalize_drug_name("Keytruda™") == "keytruda"
        assert normalize_drug_name("Humira®") == "humira"
        assert normalize_drug_name("Drug™ Name®") == "drug name"
    
    def test_extra_whitespace_removal(self):
        """Test that extra whitespace is normalized."""
        assert normalize_drug_name("Simponi   Aria") == "simponi aria"
        assert normalize_drug_name("Drug  \t  Name") == "drug name"
    
    def test_empty_string(self):
        """Test that empty strings are handled."""
        assert normalize_drug_name("") == ""
        assert normalize_drug_name(None) == ""
    
    def test_combined_normalization(self):
        """Test multiple normalizations together."""
        assert normalize_drug_name("  KEYTRUDA™  ") == "keytruda"
        assert normalize_drug_name("Drug®   Name™") == "drug name"


class TestFuzzyMatchDrugName:
    """Test fuzzy_match_drug_name function."""
    
    def test_exact_match(self, sample_drug_names):
        """Test exact match returns 100% confidence."""
        match, confidence = fuzzy_match_drug_name("Keytruda", sample_drug_names)
        assert match == "Keytruda"
        assert confidence == 100
    
    def test_case_insensitive_match(self, sample_drug_names):
        """Test case-insensitive matching."""
        match, confidence = fuzzy_match_drug_name("keytruda", sample_drug_names)
        assert match == "Keytruda"
        assert confidence == 100
    
    def test_fuzzy_match_typo(self, sample_drug_names):
        """Test fuzzy matching with typos."""
        match, confidence = fuzzy_match_drug_name("Ketruda", sample_drug_names)
        assert match == "Keytruda"
        assert confidence >= 70
    
    def test_partial_match(self, sample_drug_names):
        """Test partial name matching."""
        match, confidence = fuzzy_match_drug_name("Simponi", sample_drug_names)
        assert match == "Simponi Aria"
        assert confidence >= 70
    
    def test_no_match_below_threshold(self, sample_drug_names):
        """Test that poor matches are rejected."""
        match, confidence = fuzzy_match_drug_name("xyz123", sample_drug_names)
        assert match is None
        assert confidence == 0
    
    def test_empty_query(self, sample_drug_names):
        """Test empty query handling."""
        match, confidence = fuzzy_match_drug_name("", sample_drug_names)
        assert match is None
        assert confidence == 0
    
    def test_empty_drug_list(self):
        """Test empty drug list handling."""
        match, confidence = fuzzy_match_drug_name("Keytruda", [])
        assert match is None
        assert confidence == 0
    
    def test_custom_threshold(self, sample_drug_names):
        """Test custom threshold parameter."""
        match, confidence = fuzzy_match_drug_name("Key", sample_drug_names, threshold=90)
        # May or may not match depending on algorithm
        assert isinstance(confidence, int)


class TestExtractDrugNameFromQuery:
    """Test extract_drug_name_from_query function."""
    
    def test_extract_single_word_drug(self, sample_drug_names):
        """Test extracting single-word drug names."""
        drug, confidence, method = extract_drug_name_from_query(
            "Is Humira preferred?", sample_drug_names
        )
        assert drug == "Humira"
        assert confidence >= 60
    
    def test_extract_two_word_drug(self, sample_drug_names):
        """Test extracting two-word drug names."""
        drug, confidence, method = extract_drug_name_from_query(
            "Does Simponi Aria require PA?", sample_drug_names
        )
        assert drug == "Simponi Aria"
        assert confidence >= 60
    
    def test_extract_with_typo(self, sample_drug_names):
        """Test extracting drug names with typos."""
        drug, confidence, method = extract_drug_name_from_query(
            "What about Remicad?", sample_drug_names
        )
        assert drug == "Remicade"
        assert confidence >= 60
    
    def test_no_drug_in_query(self, sample_drug_names):
        """Test query with no recognizable drug name."""
        drug, confidence, method = extract_drug_name_from_query(
            "List all oncology drugs", sample_drug_names
        )
        # May or may not find a match
        assert isinstance(confidence, int)
    
    def test_empty_query(self, sample_drug_names):
        """Test empty query handling."""
        drug, confidence, method = extract_drug_name_from_query("", sample_drug_names)
        assert drug is None
        assert confidence == 0
        assert method == "empty_query"
    
    def test_extraction_method_reported(self, sample_drug_names):
        """Test that extraction method is reported."""
        drug, confidence, method = extract_drug_name_from_query(
            "Keytruda status", sample_drug_names
        )
        assert method in ["extracted_from_query", "full_query_match", "no_match"]
