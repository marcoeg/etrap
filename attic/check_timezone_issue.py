#!/usr/bin/env python3
"""Check if timezone is causing the mismatch"""

import json
import hashlib
from datetime import datetime, timezone
import pytz

# Your transaction from database (appears to be UTC+7)
db_transaction = {
    "id": 107,
    "account_id": "ACC704", 
    "amount": "123456.78",  # String as CDC shows
    "type": "C",
    "created_at": "2025-06-14T06:54:27.98659",
    "reference": "FH-21-OP"
}

# Batch timestamp: 1749884067987 ms = 2025-06-13T23:54:27.987 UTC
batch_hash = "4d1c3c7d0db0e74ddb2f2e2bf2b55af461a624df6d0adf3c1a72281a22b41abf"

print("Timezone Analysis")
print("=" * 60)

# Parse the database timestamp
db_time_str = "2025-06-14T06:54:27.98659"
print(f"Database timestamp: {db_time_str}")

# If this is UTC+7 (Bangkok/Jakarta time), convert to UTC
# 06:54:27 UTC+7 = 23:54:27 UTC (previous day)
utc_time_str = "2025-06-13T23:54:27.987"
print(f"Same time in UTC: {utc_time_str}")

# Test with UTC timestamp
tx_utc = db_transaction.copy()
tx_utc['created_at'] = utc_time_str
tx_json = json.dumps(tx_utc, sort_keys=True, separators=(',', ':'))
computed_hash = hashlib.sha256(tx_json.encode()).hexdigest()

print(f"\nTest with UTC timestamp:")
print(f"  JSON: {tx_json}")
print(f"  Hash: {computed_hash}")
print(f"  Match batch hash: {'✅ YES!' if computed_hash == batch_hash else '❌ NO'}")

# Try with different precision
tx_utc['created_at'] = "2025-06-13T23:54:27.986590"  # More precision
tx_json = json.dumps(tx_utc, sort_keys=True, separators=(',', ':'))
computed_hash = hashlib.sha256(tx_json.encode()).hexdigest()
print(f"\nWith more precision:")
print(f"  created_at: {tx_utc['created_at']}")
print(f"  Hash: {computed_hash}")

# The issue seems to be:
# 1. Database returns local time (UTC+7)
# 2. CDC/Debezium captures in UTC
# 3. User queries database and gets local time
# 4. Verification fails because times don't match

print("\n" + "="*60)
print("SOLUTION:")
print("The CDC agent should:")
print("1. Detect timezone from database connection")
print("2. Convert all timestamps to UTC before hashing")
print("3. Or document that users must provide timestamps in UTC")