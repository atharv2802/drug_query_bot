"""Pytest configuration and fixtures."""

import pytest
from typing import List, Dict, Any


@pytest.fixture
def sample_drug_names() -> List[str]:
    """Sample drug names for testing."""
    return [
        "Keytruda",
        "Opdivo",
        "Yervoy",
        "Humira",
        "Remicade",
        "Simponi Aria",
        "Orencia",
        "Actemra",
        "Stelara",
        "Entyvio",
        "Neulasta",
        "Granix",
        "Cosentyx",
        "Taltz",
        "Ocrevus",
        "Tysabri"
    ]


@pytest.fixture
def sample_drug_data() -> List[Dict[str, Any]]:
    """
    Sample drug data for testing.
    
    Represents merged data from:
    1. Preferred Medical Drugs List (category, status, HCPCS, manufacturer)
    2. PA/MND List (pa_mnd_required - combined requirement)
    """
    return [
        {
            'drug_name': 'Keytruda',
            'category': 'Oncology',
            'drug_status': 'preferred',
            'hcpcs': 'J9271',
            'manufacturer': 'Merck & Co.',
            'pa_mnd_required': 'yes',
            'notes': None
        },
        {
            'drug_name': 'Remicade',
            'category': 'Immunology',
            'drug_status': 'non_preferred',
            'hcpcs': 'J1745',
            'manufacturer': 'Janssen Biotech',
            'pa_mnd_required': 'yes',
            'notes': None
        },
        {
            'drug_name': 'Humira',
            'category': 'Immunology',
            'drug_status': 'preferred',
            'hcpcs': 'J0135',
            'manufacturer': 'AbbVie',
            'pa_mnd_required': 'no',
            'notes': None
        }
    ]
