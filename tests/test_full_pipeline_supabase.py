"""
Full pipeline test: from query to answer generation for
"list all non preferred drugs that have preferred alternatives"
using the actual Supabase database.
"""
import json
import psycopg2
import os

# Step 1: Simulate LLM intent extraction
llm_message_content = '''{
  "query_type": "list_filter",
  "drug_name": null,
  "filters": {
    "drug_status": "non_preferred",
    "pa_mnd_required": null,
    "category": null
  }
}'''
intent = json.loads(llm_message_content)

# Step 2: Query Supabase database
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not found. Set it as environment variable.")
    sys.exit(1)
conn = psycopg2.connect(DATABASE_URL)

query = """
SELECT drug_name, category, drug_status, hcpcs, manufacturer
FROM drugs
WHERE drug_status = %s
"""
with conn.cursor() as cur:
    cur.execute(query, (intent['filters']['drug_status'],))
    results = cur.fetchall()
    columns = [desc[0] for desc in cur.description]
    drugs = [dict(zip(columns, row)) for row in results]
conn.close()

# Step 3: Simulate answer generation
user_query = "list all non preferred drugs that have preferred alternatives"
query_type = intent["query_type"]
if drugs:
    print("Non-preferred drugs with possible preferred alternatives:")
    for drug in drugs:
        print(f"- {drug['drug_name']} ({drug['category']}, HCPCS: {drug['hcpcs']}, Manufacturer: {drug['manufacturer']})")
else:
    print("No non-preferred drugs found.")

print("\nFull pipeline test complete.")
