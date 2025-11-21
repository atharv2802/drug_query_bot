"""
Test and debug LLM response for a specific query, with raw response logging.
"""
import requests
import json
import logging
import os
import sys
from config.prompts import INTENT_EXTRACTION_PROMPT

# Set up logging to file and console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler("llm_response_debug.log"),
        logging.StreamHandler()
    ]
)

API_KEY = os.getenv("OPENROUTER_API_KEY")
if not API_KEY:
    print("ERROR: OPENROUTER_API_KEY not found in environment. Set it before running.")
    sys.exit(1)
MODEL = "meta-llama/llama-3-70b-instruct"
QUERY = "Suggest generic preferred drugs for Antiemetics category"
PROMPT = INTENT_EXTRACTION_PROMPT.format(query=QUERY)

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://drug-query-assistant.streamlit.app",
    "X-Title": "Drug Query Assistant"
}
data = {
    "model": MODEL,
    "messages": [
        {"role": "user", "content": PROMPT}
    ],
    "temperature": 0.1,
    "max_tokens": 500
}

logging.info(f"Testing query: {QUERY}")
logging.info("=" * 80)
logging.info("PROMPT BEING USED:")
logging.info("=" * 80)
logging.info(PROMPT)
logging.info("=" * 80)
logging.info("Sending prompt to LLM...")
response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data, timeout=30)
logging.info(f"HTTP {response.status_code}")
logging.info(f"Raw LLM response: {response.text}")

# Try to extract JSON from the response
raw = response.json()["choices"][0]["message"]["content"]
logging.info(f"LLM message content: {raw}")

# Attempt to extract the first JSON block
try:
    start = raw.find('{')
    end = raw.rfind('}') + 1
    json_str = raw[start:end]
    intent = json.loads(json_str)
    logging.info(f"Extracted intent: {intent}")
except Exception as e:
    logging.error(f"Failed to parse intent JSON: {e}")
    logging.error(f"Raw content for debugging: {raw}")

print("Done. See llm_response_debug.log for details.")
