"""Unit tests for utils/db.py - Database access layer."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from utils.db import (
    get_db_connection,
    fetch_all_drug_names,
    fetch_drug_by_name,
    fetch_alternatives,
    filter_drugs,
    get_all_categories
)


class TestGetDbConnection:
    """Test get_db_connection function."""
    
    @patch('utils.db.psycopg2.connect')
    @patch('utils.db.st')
    def test_connection_success(self, mock_st, mock_connect):
        """Test successful database connection."""
        mock_st.secrets = {"DATABASE_URL": "postgresql://test"}
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        
        conn = get_db_connection()
        
        assert conn == mock_conn
        mock_connect.assert_called_once()
    
    @patch('utils.db.psycopg2.connect')
    @patch('utils.db.st')
    def test_connection_failure(self, mock_st, mock_connect):
        """Test database connection failure."""
        mock_st.secrets = {"DATABASE_URL": "postgresql://test"}
        mock_connect.side_effect = Exception("Connection failed")
        
        with pytest.raises(Exception):
            get_db_connection()


class TestFetchAllDrugNames:
    """Test fetch_all_drug_names function."""
    
    @patch('utils.db.get_db_connection')
    def test_fetch_drug_names(self, mock_get_conn):
        """Test fetching all drug names."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
        mock_cursor.fetchall.return_value = [
            {'drug_name': 'Keytruda'},
            {'drug_name': 'Humira'},
            {'drug_name': 'Remicade'}
        ]
        mock_get_conn.return_value = mock_conn
        
        result = fetch_all_drug_names()
        
        assert result == ['Keytruda', 'Humira', 'Remicade']
        mock_conn.close.assert_called_once()
    
    @patch('utils.db.get_db_connection')
    def test_fetch_empty_list(self, mock_get_conn):
        """Test fetching when no drugs exist."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
        mock_cursor.fetchall.return_value = []
        mock_get_conn.return_value = mock_conn
        
        result = fetch_all_drug_names()
        
        assert result == []


class TestFetchDrugByName:
    """Test fetch_drug_by_name function."""
    
    @patch('utils.db.get_db_connection')
    def test_exact_match(self, mock_get_conn):
        """Test exact drug name match."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
        mock_cursor.fetchone.return_value = {
            'drug_name': 'Keytruda',
            'category': 'Oncology',
            'drug_status': 'preferred'
        }
        mock_get_conn.return_value = mock_conn
        
        result = fetch_drug_by_name('Keytruda')
        
        assert result['drug_name'] == 'Keytruda'
        assert result['category'] == 'Oncology'
    
    @patch('utils.db.fetch_all_drug_names')
    @patch('utils.db.get_db_connection')
    def test_fuzzy_match(self, mock_get_conn, mock_fetch_names):
        """Test fuzzy drug name matching."""
        mock_fetch_names.return_value = ['Keytruda', 'Humira']
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
        
        # First call returns None (no exact match), second returns fuzzy match
        mock_cursor.fetchone.side_effect = [
            None,
            {'drug_name': 'Keytruda', 'category': 'Oncology', 'drug_status': 'preferred'}
        ]
        mock_get_conn.return_value = mock_conn
        
        result = fetch_drug_by_name('Ketruda')
        
        assert result is not None
        assert '_fuzzy_match' in result or result['drug_name'] == 'Keytruda'
    
    @patch('utils.db.fetch_all_drug_names')
    @patch('utils.db.get_db_connection')
    def test_no_match(self, mock_get_conn, mock_fetch_names):
        """Test when no match is found."""
        mock_fetch_names.return_value = ['Keytruda', 'Humira']
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
        mock_cursor.fetchone.return_value = None
        mock_get_conn.return_value = mock_conn
        
        result = fetch_drug_by_name('xyz123')
        
        assert result is None


class TestFetchAlternatives:
    """Test fetch_alternatives function."""
    
    @patch('utils.db.fetch_drug_by_name')
    @patch('utils.db.get_db_connection')
    def test_fetch_alternatives(self, mock_get_conn, mock_fetch_drug):
        """Test fetching alternatives for a drug."""
        mock_fetch_drug.return_value = {
            'drug_name': 'Remicade',
            'category': 'Immunology'
        }
        
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
        mock_cursor.fetchall.return_value = [
            {'drug_name': 'Humira', 'category': 'Immunology', 'drug_status': 'preferred'},
            {'drug_name': 'Simponi Aria', 'category': 'Immunology', 'drug_status': 'preferred'}
        ]
        mock_get_conn.return_value = mock_conn
        
        result = fetch_alternatives('Remicade')
        
        assert len(result) == 2
        assert result[0]['drug_name'] == 'Humira'
    
    @patch('utils.db.fetch_drug_by_name')
    def test_no_category(self, mock_fetch_drug):
        """Test when drug has no category."""
        mock_fetch_drug.return_value = {
            'drug_name': 'TestDrug',
            'category': None
        }
        
        result = fetch_alternatives('TestDrug')
        
        assert result == []
    
    @patch('utils.db.fetch_drug_by_name')
    def test_drug_not_found(self, mock_fetch_drug):
        """Test when drug is not found."""
        mock_fetch_drug.return_value = None
        
        result = fetch_alternatives('NonExistentDrug')
        
        assert result == []


class TestFilterDrugs:
    """Test filter_drugs function."""
    
    @patch('utils.db.get_db_connection')
    def test_filter_by_status(self, mock_get_conn):
        """Test filtering by drug status."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
        mock_cursor.fetchall.return_value = [
            {'drug_name': 'Keytruda', 'drug_status': 'preferred'},
            {'drug_name': 'Humira', 'drug_status': 'preferred'}
        ]
        mock_get_conn.return_value = mock_conn
        
        result = filter_drugs({'drug_status': 'preferred'})
        
        assert len(result) == 2
    
    @patch('utils.db.get_db_connection')
    def test_filter_multiple_criteria(self, mock_get_conn):
        """Test filtering by multiple criteria."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
        mock_cursor.fetchall.return_value = [
            {'drug_name': 'Keytruda', 'drug_status': 'preferred', 'category': 'Oncology'}
        ]
        mock_get_conn.return_value = mock_conn
        
        result = filter_drugs({
            'drug_status': 'preferred',
            'category': 'Oncology'
        })
        
        assert len(result) == 1
        assert result[0]['category'] == 'Oncology'
    
    @patch('utils.db.get_db_connection')
    def test_no_filters(self, mock_get_conn):
        """Test querying with no filters."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
        mock_cursor.fetchall.return_value = []
        mock_get_conn.return_value = mock_conn
        
        result = filter_drugs({})
        
        assert isinstance(result, list)


class TestGetAllCategories:
    """Test get_all_categories function."""
    
    @patch('utils.db.get_db_connection')
    def test_fetch_categories(self, mock_get_conn):
        """Test fetching all categories."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
        mock_cursor.fetchall.return_value = [
            {'category': 'Oncology'},
            {'category': 'Immunology'},
            {'category': 'Neurology'}
        ]
        mock_get_conn.return_value = mock_conn
        
        result = get_all_categories()
        
        assert result == ['Oncology', 'Immunology', 'Neurology']
        mock_conn.close.assert_called_once()
