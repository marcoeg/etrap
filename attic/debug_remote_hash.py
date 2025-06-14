#!/usr/bin/env python3
"""Run this on the remote server to debug hash computation"""

import json
import hashlib
from datetime import datetime

print("CDC Agent Hash Debug")
print("=" * 60)

# Test the exact normalization logic from the CDC agent
def normalize_and_hash(tx_data):
    """Apply the same normalization as CDC agent"""
    normalized_data = tx_data.copy()
    
    # Convert epoch timestamps
    for field, value in normalized_data.items():
        if field.endswith('_at'):
            if isinstance(value, str):
                continue
            elif isinstance(value, (int, float)) and value > 1000000000000:
                if value > 1000000000000000:  # Microseconds
                    dt = datetime.fromtimestamp(value / 1000000)
                else:  # Milliseconds
                    dt = datetime.fromtimestamp(value / 1000)
                iso_str = dt.strftime('%Y-%m-%dT%H:%M:%S.%f')
                iso_str = iso_str.rstrip('0').rstrip('.')
                if '.' not in iso_str:
                    iso_str += '.000'
                normalized_data[field] = iso_str
    
    tx_json = json.dumps(normalized_data, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(tx_json.encode()).hexdigest(), tx_json

# Test with ACC999 transaction
test_cases = [
    {
        "name": "Raw CDC data",
        "data": {
            "id": 108,
            "account_id": "ACC999",
            "amount": "999.99",
            "type": "C",
            "created_at": 1749884489064,
            "reference": "TEST-VERIFY"
        }
    },
    {
        "name": "Already normalized",
        "data": {
            "id": 108,
            "account_id": "ACC999",
            "amount": "999.99",
            "type": "C",
            "created_at": "2025-06-14T07:01:29.064",
            "reference": "TEST-VERIFY"
        }
    }
]

target_hash = "ba5ba542b41eaa2288e7e5b5342aebfd7a99c22204c28009f8266a7e2e742204"
print(f"Target hash: {target_hash}\n")

for test in test_cases:
    print(f"{test['name']}:")
    print(f"  Input: {json.dumps(test['data'])}")
    hash_val, json_str = normalize_and_hash(test['data'])
    print(f"  Normalized: {json_str}")
    print(f"  Hash: {hash_val}")
    print(f"  Match: {'✅ YES' if hash_val == target_hash else '❌ NO'}")
    print()

# Also test what Python shows for the timestamp
print(f"Python timestamp conversion:")
print(f"  1749884489064 ms = {datetime.fromtimestamp(1749884489064/1000)}")
print(f"  System timezone: {datetime.now().astimezone().tzinfo}")

# Add this to the CDC agent to debug
print("\nTo debug in CDC agent, add this after line 621:")
print('print(f"DEBUG: Hashing {tx_data_to_hash}")')
print('print(f"DEBUG: Hash = {tx_hash}")')