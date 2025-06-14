#!/usr/bin/env python3
"""Debug hash mismatch between verification and CDC agent"""

import json
import hashlib
from datetime import datetime

# Transaction from database
db_transaction = {
    "id": 107,
    "account_id": "ACC704",
    "amount": 123456.78,
    "type": "C",
    "created_at": "2025-06-14T06:54:27.98659",
    "reference": "FH-21-OP"
}

# Hash from the batch
batch_hash = "4d1c3c7d0db0e74ddb2f2e2bf2b55af461a624df6d0adf3c1a72281a22b41abf"

print("Debugging hash mismatch")
print("=" * 60)
print(f"Batch hash: {batch_hash}")
print()

# Test 1: Direct hash as verification tool does
tx_json = json.dumps(db_transaction, sort_keys=True, separators=(',', ':'))
hash1 = hashlib.sha256(tx_json.encode()).hexdigest()
print(f"Test 1 - Direct hash of DB data:")
print(f"  JSON: {tx_json}")
print(f"  Hash: {hash1}")
print(f"  Match: {'✅' if hash1 == batch_hash else '❌'}")
print()

# Test 2: With amount as string (as CDC shows)
tx_with_str_amount = db_transaction.copy()
tx_with_str_amount['amount'] = '123456.78'
tx_json = json.dumps(tx_with_str_amount, sort_keys=True, separators=(',', ':'))
hash2 = hashlib.sha256(tx_json.encode()).hexdigest()
print(f"Test 2 - Amount as string:")
print(f"  JSON: {tx_json}")
print(f"  Hash: {hash2}")
print(f"  Match: {'✅' if hash2 == batch_hash else '❌'}")
print()

# Test 3: Check timestamp precision
# The batch timestamp shows 1749884067987 (milliseconds)
# Let's convert and see what timestamp that represents
batch_timestamp_ms = 1749884067987
batch_dt = datetime.fromtimestamp(batch_timestamp_ms / 1000)
print(f"Test 3 - Batch timestamp analysis:")
print(f"  Batch timestamp (ms): {batch_timestamp_ms}")
print(f"  Converted to ISO: {batch_dt.strftime('%Y-%m-%dT%H:%M:%S.%f')}")
print(f"  Your timestamp: 2025-06-14T06:54:27.98659")
print()

# Test 4: Try with different timestamp formats
# The timestamp might have different precision
test_timestamps = [
    "2025-06-14T06:54:27.987",      # 3 decimal places
    "2025-06-14T06:54:27.9865",     # 4 decimal places  
    "2025-06-14T06:54:27.98659",    # 5 decimal places (original)
    "2025-06-14T06:54:27.986590",   # 6 decimal places
    "2025-06-14T06:54:27.987468",   # From batch timestamp conversion
]

print("Test 4 - Different timestamp precisions:")
for ts in test_timestamps:
    tx_test = tx_with_str_amount.copy()
    tx_test['created_at'] = ts
    tx_json = json.dumps(tx_test, sort_keys=True, separators=(',', ':'))
    test_hash = hashlib.sha256(tx_json.encode()).hexdigest()
    print(f"  {ts}: {test_hash[:32]}... {'✅' if test_hash == batch_hash else ''}")
print()

# Test 5: Different account ID?
print("Test 5 - Check if data matches:")
print(f"  Your data: id=107, account=ACC704")
print(f"  Batch data: Check S3 to see actual transaction data")
print()
print("The issue might be:")
print("1. The transaction ID doesn't match (batch might have different ID)")
print("2. The timestamp precision is different") 
print("3. The account ID is different")
print("4. The CDC agent might have received different data than what's in DB")