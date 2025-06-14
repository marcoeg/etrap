#!/usr/bin/env python3
"""Test what hash the CDC agent would compute for the ACC777 transaction"""

import json
import hashlib

# The transaction data you're trying to verify
transaction_data = {
    "id": 91,
    "account_id": "ACC777", 
    "amount": 123456.78,
    "type": "C",
    "created_at": "2025-06-14T05:10:44.133755",
    "reference": "FH-21-OP"
}

# Method 1: Hash the decoded transaction data (what the current code should do)
tx_json = json.dumps(transaction_data, sort_keys=True, separators=(',', ':'))
hash1 = hashlib.sha256(tx_json.encode()).hexdigest()
print("Method 1 - Hash of decoded transaction data:")
print(f"  Data: {tx_json}")
print(f"  Hash: {hash1}")
print()

# Method 2: Try with amount as integer (cents)
transaction_data_cents = {
    "id": 91,
    "account_id": "ACC777", 
    "amount": 12345678,  # As cents
    "type": "C",
    "created_at": "2025-06-14T05:10:44.133755",
    "reference": "FH-21-OP"
}
tx_json2 = json.dumps(transaction_data_cents, sort_keys=True, separators=(',', ':'))
hash2 = hashlib.sha256(tx_json2.encode()).hexdigest()
print("Method 2 - With amount as cents:")
print(f"  Data: {tx_json2}")
print(f"  Hash: {hash2}")
print()

# Method 3: With timestamp as microseconds
transaction_data_microseconds = {
    "id": 91,
    "account_id": "ACC777", 
    "amount": 12345678,
    "type": "C",
    "created_at": 1750026644133755,  # As microseconds
    "reference": "FH-21-OP"
}
tx_json3 = json.dumps(transaction_data_microseconds, sort_keys=True, separators=(',', ':'))
hash3 = hashlib.sha256(tx_json3.encode()).hexdigest()
print("Method 3 - With timestamp as microseconds:")
print(f"  Data: {tx_json3}")
print(f"  Hash: {hash3}")
print()

# The actual hash from the batch
print("Actual hash in batch: 468340a471164188b044a70584bd89280ef88e3f0f83b022815cbea7f2666f54")
print()

# Check if any match
if hash1 == "468340a471164188b044a70584bd89280ef88e3f0f83b022815cbea7f2666f54":
    print("✅ Method 1 matches!")
elif hash2 == "468340a471164188b044a70584bd89280ef88e3f0f83b022815cbea7f2666f54":
    print("✅ Method 2 matches!")
elif hash3 == "468340a471164188b044a70584bd89280ef88e3f0f83b022815cbea7f2666f54":
    print("✅ Method 3 matches!")
else:
    print("❌ None of the methods produce the expected hash")
    print("   This suggests the CDC agent is hashing the CDC event structure,")
    print("   not the decoded transaction data.")