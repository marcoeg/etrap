#!/usr/bin/env python3
"""Try different combinations to find what produces the batch hash"""

import json
import hashlib
from datetime import datetime

target_hash = "94ebae32e830d61a802c3cd8f630776e965920e385d51593ccb546c267480312"

# Base transaction data
base_tx = {
    'id': 92,
    'account_id': 'ACC7077',
    'type': 'C',
    'reference': 'FH-21-OP'
}

# Try different amount formats
amounts = [
    123456.78,  # float dollars
    12345678,   # integer cents
    "123456.78", # string dollars
    "12345678"   # string cents
]

# Try different timestamp formats
timestamps = [
    '2025-06-14T05:23:02.877966',  # ISO format
    '2025-06-14T05:23:02.877966Z', # ISO with Z
    1749878582877,  # milliseconds (close to batch timestamp)
    1749878582877966,  # microseconds
    '2025-06-14 05:23:02.877966',  # Space instead of T
]

# Try different field names for timestamp
time_fields = ['created_at', 'timestamp', 'ts']

print("Searching for correct format...")
print("="*60)

found = False
for amount in amounts:
    for ts_value in timestamps:
        for ts_field in time_fields:
            # Build transaction
            tx = base_tx.copy()
            tx['amount'] = amount
            tx[ts_field] = ts_value
            
            # Compute hash
            tx_json = json.dumps(tx, sort_keys=True, separators=(',', ':'))
            computed_hash = hashlib.sha256(tx_json.encode()).hexdigest()
            
            if computed_hash == target_hash:
                print(f"\n✅ FOUND MATCH!")
                print(f"   JSON: {tx_json}")
                print(f"   Hash: {computed_hash}")
                found = True
                break
        if found:
            break
    if found:
        break

if not found:
    print("\n❌ No match found with standard formats")
    print("\nTrying without timestamp field...")
    
    # Try without any timestamp
    for amount in amounts:
        tx = base_tx.copy()
        tx['amount'] = amount
        
        tx_json = json.dumps(tx, sort_keys=True, separators=(',', ':'))
        computed_hash = hashlib.sha256(tx_json.encode()).hexdigest()
        
        if computed_hash == target_hash:
            print(f"\n✅ FOUND MATCH (no timestamp)!")
            print(f"   JSON: {tx_json}")
            print(f"   Hash: {computed_hash}")
            found = True
            break