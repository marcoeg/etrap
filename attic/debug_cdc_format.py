#!/usr/bin/env python3
"""Debug what format the CDC event might have"""

import json
import hashlib

target_hash = "9c8da7d5df6f3911ed3ad15da59cb8700893738f94786b6b9af75c67d146baf9"

# Base data
base = {
    'account_id': 'ACC17077',
    'type': 'C',
    'reference': 'FH-21-OP'
}

# Try different combinations
print("Searching for correct CDC event format...")
print("="*60)

# Different ID formats
ids = [93, '93']

# Different amount formats
amounts = [
    123456.78,      # float
    '123456.78',    # string
    '123456.780000', # string with trailing zeros
    12345678,       # integer cents
    '12345678'      # string cents
]

# Different timestamp formats
timestamps = [
    '2025-06-14T05:34:21.598781',      # From database
    '2025-06-14T05:34:21.598781000',   # With extra precision
    '2025-06-14T05:34:21.598',         # Less precision
    '2025-06-14T05:34:21',             # No fractional seconds
    '2025-06-14 05:34:21.598781',      # Space separator
    1749879261598781,                   # Microseconds
    1749879261598,                      # Milliseconds
]

found = False
for id_val in ids:
    for amount in amounts:
        for ts in timestamps:
            tx = base.copy()
            tx['id'] = id_val
            tx['amount'] = amount
            tx['created_at'] = ts
            
            tx_json = json.dumps(tx, sort_keys=True, separators=(',', ':'))
            computed_hash = hashlib.sha256(tx_json.encode()).hexdigest()
            
            if computed_hash == target_hash:
                print(f"\n✅ FOUND MATCH!")
                print(f"   JSON: {tx_json}")
                print(f"   id type: {type(id_val)}")
                print(f"   amount type: {type(amount)}")
                print(f"   created_at type: {type(ts)}")
                found = True
                break
        if found:
            break
    if found:
        break

if not found:
    print("\n❌ No match found")
    print("\nTrying without created_at field (CDC might not include it)...")
    
    for id_val in ids:
        for amount in amounts:
            tx = {
                'account_id': 'ACC17077',
                'amount': amount,
                'id': id_val,
                'reference': 'FH-21-OP',
                'type': 'C'
            }
            
            tx_json = json.dumps(tx, sort_keys=True, separators=(',', ':'))
            computed_hash = hashlib.sha256(tx_json.encode()).hexdigest()
            
            if computed_hash == target_hash:
                print(f"\n✅ FOUND MATCH (no created_at)!")
                print(f"   JSON: {tx_json}")
                found = True
                break
        if found:
            break