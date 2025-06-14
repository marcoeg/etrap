#!/usr/bin/env python3
"""Find the exact data that produces the batch hash"""

import json
import hashlib
from datetime import datetime

# The hash we need to match from the batch
target_hash = "ba5ba542b41eaa2288e7e5b5342aebfd7a99c22204c28009f8266a7e2e742204"

# Base transaction data
base = {
    "id": 108,
    "account_id": "ACC999",
    "amount": "999.99",  # CDC shows this as string
    "type": "C",
    "reference": "TEST-VERIFY"
}

# Based on remote server behavior:
# Python on remote converts 1749884489064 ms to 2025-06-14 07:01:29.064000
# The CDC agent normalization would produce different formats

print("Finding exact data format...")
print("=" * 60)

# Test different timestamp formats the CDC agent might produce
timestamps = [
    "2025-06-14T07:01:29.064",      # Normalized, no trailing zeros
    "2025-06-14T07:01:29.064000",   # Full microseconds
    "2025-06-14T07:01:29.063897",   # Original DB precision
    "2025-06-14T00:01:29.064",      # If it was UTC
    "2025-06-14T00:01:29.064000",   # UTC full precision
]

# Test with different field orderings (though sort_keys should handle this)
for ts in timestamps:
    test_data = base.copy()
    test_data["created_at"] = ts
    
    # Try exact ordering as it might appear
    tx_json = json.dumps(test_data, sort_keys=True, separators=(',', ':'))
    computed = hashlib.sha256(tx_json.encode()).hexdigest()
    
    if computed == target_hash:
        print(f"✅ FOUND MATCH!")
        print(f"   Timestamp: {ts}")
        print(f"   JSON: {tx_json}")
        print(f"   Hash: {computed}")
        break
    else:
        print(f"   {ts}: {computed[:16]}... ❌")

print("\nIf no match found, the issue might be:")
print("1. The transaction data in the batch is different")
print("2. The CDC agent on remote has different code")
print("3. There's a race condition with transaction IDs")