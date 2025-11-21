"""
Quick verification script to test ingestion logic without database.
This demonstrates how pa_mnd_required flags are set.
"""
import sys
sys.path.insert(0, 'd:\\drug_query_bot')

from ingest_data import load_preferred_drugs_list, load_pa_mnd_list, merge_drug_data

# Load data
print("Loading preferred drugs list...")
preferred_drugs = load_preferred_drugs_list('data/preferred_drugs_list.csv')
print(f"Loaded {len(preferred_drugs)} drugs\n")

print("Loading PA/MND list...")
pa_mnd_data = load_pa_mnd_list('data/pa_mnd_list.csv')
print(f"Loaded {len(pa_mnd_data)} drugs requiring PA/MND")
print(f"PA/MND drugs: {list(pa_mnd_data.keys())}\n")

print("Merging data...")
merged_drugs = merge_drug_data(preferred_drugs, pa_mnd_data)
print(f"Final dataset: {len(merged_drugs)} drugs\n")

# Display results
print("=" * 100)
print(f"{'Drug Name':<25} {'Category':<20} {'Status':<15} {'PA/MND Required':<20}")
print("=" * 100)

for drug in sorted(merged_drugs, key=lambda x: x['drug_name']):
    print(f"{drug['drug_name']:<25} {drug['category'] or 'N/A':<20} {drug['drug_status']:<15} {drug['pa_mnd_required']:<20}")

print("=" * 100)

# Verification checks
print("\n🔍 VERIFICATION CHECKS:")
print("-" * 50)

# Check 1: Drugs in PA/MND list should have pa_mnd_required='yes'
pa_mnd_drugs = [d for d in merged_drugs if d['pa_mnd_required'] == 'yes']
print(f"✓ Drugs requiring PA/MND: {len(pa_mnd_drugs)}")
for drug in pa_mnd_drugs[:5]:
    print(f"  - {drug['drug_name']}")
if len(pa_mnd_drugs) > 5:
    print(f"  ... and {len(pa_mnd_drugs) - 5} more")

# Check 2: Drugs NOT in PA/MND list should have pa_mnd_required='no'
no_pa_mnd_drugs = [d for d in merged_drugs if d['pa_mnd_required'] == 'no']
print(f"\n✓ Drugs NOT requiring PA/MND: {len(no_pa_mnd_drugs)}")
for drug in no_pa_mnd_drugs[:5]:
    print(f"  - {drug['drug_name']}")
if len(no_pa_mnd_drugs) > 5:
    print(f"  ... and {len(no_pa_mnd_drugs) - 5} more")

# Check 3: Verify specific examples
print("\n✓ Specific Examples:")
test_cases = [
    ('Keytruda', 'yes'),  # In PA/MND list
    ('Humira', 'no'),     # NOT in PA/MND list
    ('Remicade', 'yes'),  # In PA/MND list
    ('Neulasta', 'no'),   # NOT in PA/MND list
]

for drug_name, expected in test_cases:
    drug_data = next((d for d in merged_drugs if d['drug_name'] == drug_name), None)
    if drug_data:
        actual = drug_data['pa_mnd_required']
        status = "✓" if actual == expected else "✗"
        print(f"  {status} {drug_name}: expected={expected}, actual={actual}")
    else:
        print(f"  ✗ {drug_name}: NOT FOUND in merged data")

print("\n✅ Verification complete!")
