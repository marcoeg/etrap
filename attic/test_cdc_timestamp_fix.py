#!/usr/bin/env python3
"""Test the CDC agent timestamp normalization fix"""

import json
import hashlib
from datetime import datetime

# Test the normalization logic
test_cases = [
    {
        "name": "Epoch microseconds from Debezium",
        "data": {
            'id': 97,
            'account_id': 'ACC304',
            'amount': '123456.78',
            'type': 'C',
            'created_at': 1749882020770667,  # Epoch microseconds
            'reference': 'FH-21-OP'
        }
    },
    {
        "name": "Already ISO format (shouldn't change)",
        "data": {
            'id': 97,
            'account_id': 'ACC304',
            'amount': '123456.78',
            'type': 'C',
            'created_at': '2025-06-14T06:20:20.770667',  # Already ISO
            'reference': 'FH-21-OP'
        }
    },
    {
        "name": "Mixed - some fields ISO, some epoch",
        "data": {
            'id': 97,
            'account_id': 'ACC304',
            'amount': '123456.78',
            'type': 'C',
            'created_at': 1749882020770667,  # Epoch
            'updated_at': '2025-06-14T06:20:20.770667',  # ISO
            'reference': 'FH-21-OP'
        }
    }
]

for test in test_cases:
    print(f"\nTest: {test['name']}")
    print("=" * 60)
    
    # Apply the same normalization logic as CDC agent
    normalized_data = test['data'].copy()
    
    for field, value in normalized_data.items():
        if field.endswith('_at'):
            if isinstance(value, str):
                print(f"  {field}: Already ISO format - no conversion")
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
                print(f"  {field}: Converted {value} → {iso_str}")
    
    # Hash the normalized data
    tx_json = json.dumps(normalized_data, sort_keys=True, separators=(',', ':'))
    computed_hash = hashlib.sha256(tx_json.encode()).hexdigest()
    
    print(f"\nNormalized JSON: {tx_json}")
    print(f"Hash: {computed_hash}")

# Now test with the database format that users will provide
print("\n" + "="*60)
print("User verification test:")
user_data = {
    "id": 97,
    "account_id": "ACC304",
    "amount": 123456.78,  # Note: user provides as float
    "type": "C",
    "created_at": "2025-06-14T06:20:20.770667",
    "reference": "FH-21-OP"
}

# Convert amount to string to match CDC format
user_data_normalized = user_data.copy()
user_data_normalized['amount'] = str(user_data['amount'])

tx_json = json.dumps(user_data_normalized, sort_keys=True, separators=(',', ':'))
user_hash = hashlib.sha256(tx_json.encode()).hexdigest()

print(f"User provides: {json.dumps(user_data, indent=2)}")
print(f"Normalized for verification: {tx_json}")
print(f"User's hash: {user_hash}")
print("\nThis should match the hash computed by the CDC agent after normalization!")