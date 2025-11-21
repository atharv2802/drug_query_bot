"""
Test Supabase client connection and basic queries.
"""
import os
import sys

# Set environment variables from secrets file for testing
secrets_path = os.path.join(os.path.dirname(__file__), '.streamlit', 'secrets.toml')
if os.path.exists(secrets_path):
    with open(secrets_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"')
                if key in ['SUPABASE_URL', 'SUPABASE_KEY']:
                    os.environ[key] = value

from utils.db import (
    get_supabase_client,
    fetch_all_drug_names,
    fetch_drug_by_name,
    filter_drugs,
    get_all_categories
)

def test_connection():
    """Test basic Supabase connection."""
    print("=" * 80)
    print("TESTING SUPABASE CONNECTION")
    print("=" * 80)
    
    try:
        client = get_supabase_client()
        print("✅ Supabase client connected successfully")
        return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

def test_fetch_all_drug_names():
    """Test fetching all drug names."""
    print("\n" + "─" * 80)
    print("TEST: Fetch All Drug Names")
    print("─" * 80)
    
    try:
        names = fetch_all_drug_names()
        print(f"✅ Fetched {len(names)} drug names")
        print(f"Sample drugs: {names[:5]}")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

def test_fetch_drug_by_name():
    """Test fetching a specific drug."""
    print("\n" + "─" * 80)
    print("TEST: Fetch Drug By Name")
    print("─" * 80)
    
    try:
        drug = fetch_drug_by_name("Remicade")
        if drug:
            print(f"✅ Found drug: {drug['drug_name']}")
            print(f"   Status: {drug.get('drug_status')}")
            print(f"   Category: {drug.get('category')}")
            print(f"   PA/MND Required: {drug.get('pa_mnd_required')}")
            return True
        else:
            print("❌ Drug not found")
            return False
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

def test_filter_drugs():
    """Test filtering drugs."""
    print("\n" + "─" * 80)
    print("TEST: Filter Drugs (Preferred + Antiemetics)")
    print("─" * 80)
    
    try:
        results = filter_drugs({
            'drug_status': 'preferred',
            'category': 'Antiemetics'
        })
        print(f"✅ Found {len(results)} preferred antiemetics")
        if results:
            print(f"Sample: {results[0]['drug_name']}")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

def test_manufacturer_filter():
    """Test manufacturer filter with 'generic' keyword."""
    print("\n" + "─" * 80)
    print("TEST: Filter by Manufacturer (Generic)")
    print("─" * 80)
    
    try:
        results = filter_drugs({
            'manufacturer': 'generic',
            'drug_status': 'preferred',
            'category': 'Antiemetics'
        })
        print(f"✅ Found {len(results)} generic preferred antiemetics")
        if results:
            print(f"Sample: {results[0]['drug_name']} - Manufacturer: {results[0].get('manufacturer')}")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

def test_get_categories():
    """Test fetching all categories."""
    print("\n" + "─" * 80)
    print("TEST: Get All Categories")
    print("─" * 80)
    
    try:
        categories = get_all_categories()
        print(f"✅ Found {len(categories)} categories")
        print(f"Categories: {', '.join(categories[:5])}...")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

def main():
    """Run all tests."""
    tests = [
        test_connection,
        test_fetch_all_drug_names,
        test_fetch_drug_by_name,
        test_filter_drugs,
        test_manufacturer_filter,
        test_get_categories
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"❌ Test crashed: {e}")
            results.append(False)
    
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✅ ALL TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
        sys.exit(1)

if __name__ == "__main__":
    main()
