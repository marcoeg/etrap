#!/usr/bin/env python3
"""Debug ACC999 transaction hash"""

import json
import hashlib
from datetime import datetime

# Hash from the batch
batch_hash = "ba5ba542b41eaa2288e7e5b5342aebfd7a99c22204c28009f8266a7e2e742204"

# Database values
db_values = {
    "id": 108,
    "account_id": "ACC999",
    "amount": 999.99,
    "type": "C",
    "created_at": "2025-06-14 07:01:29.063897",  # Space format from DB
    "reference": "TEST-VERIFY"
}

print("Debugging ACC999 transaction")
print("=" * 60)
print(f"Batch hash: {batch_hash}")
print()

# Test different combinations
tests = [
    # Test 1: Exact DB values
    {
        "name": "Exact DB values",
        "data": db_values
    },
    # Test 2: ISO format timestamp
    {
        "name": "ISO timestamp format",
        "data": {**db_values, "created_at": "2025-06-14T07:01:29.063897"}
    },
    # Test 3: Amount as string
    {
        "name": "Amount as string",
        "data": {**db_values, "amount": "999.99", "created_at": "2025-06-14T07:01:29.063897"}
    },
    # Test 4: UTC timestamp (7 hours back)
    {
        "name": "UTC timestamp",
        "data": {**db_values, "amount": "999.99", "created_at": "2025-06-14T00:01:29.063897"}
    },
    # Test 5: Timestamp from batch (milliseconds)
    {
        "name": "From batch timestamp",
        "data": {**db_values, "amount": "999.99", "created_at": datetime.fromtimestamp(1749884489064/1000).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}
    }
]

for test in tests:
    tx_json = json.dumps(test["data"], sort_keys=True, separators=(',', ':'))
    computed_hash = hashlib.sha256(tx_json.encode()).hexdigest()
    match = "✅" if computed_hash == batch_hash else ""
    print(f"{test['name']}: {computed_hash[:32]}... {match}")
    if match:
        print(f"  JSON: {tx_json}")

# Show batch timestamp conversion
print(f"\nBatch timestamp: 1749884489064 ms")
print(f"Converts to: {datetime.fromtimestamp(1749884489064/1000)}")

# The issue is likely timezone - check if DB is in UTC+7
print("\nIf database is UTC+7:")
print(f"  DB shows: 2025-06-14 07:01:29")
print(f"  UTC time: 2025-06-14 00:01:29")