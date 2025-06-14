#!/usr/bin/env python3
"""Test what the CDC agent normalization produces"""

import json
import hashlib
from datetime import datetime

# Simulate what CDC agent receives from Debezium
cdc_event = {
    'id': 108,
    'account_id': 'ACC999',
    'amount': '999.99',  # Debezium sends as string due to decimal.handling.mode=string
    'type': 'C',
    'created_at': 1749884489064,  # Epoch milliseconds from batch timestamp
    'reference': 'TEST-VERIFY'
}

print("Testing CDC agent normalization")
print("=" * 60)
print(f"CDC event (from Debezium): {json.dumps(cdc_event, indent=2)}")
print()

# Apply CDC agent normalization
normalized_data = cdc_event.copy()

# The CDC agent checks for fields ending in '_at'
for field, value in normalized_data.items():
    if field.endswith('_at'):
        if isinstance(value, str):
            print(f"  {field} is already string, no conversion")
        elif isinstance(value, (int, float)) and value > 1000000000000:
            # Convert epoch to ISO
            if value > 1000000000000000:  # Microseconds
                dt = datetime.fromtimestamp(value / 1000000)
            else:  # Milliseconds
                dt = datetime.fromtimestamp(value / 1000)
            iso_str = dt.strftime('%Y-%m-%dT%H:%M:%S.%f')
            # Remove trailing zeros but keep at least milliseconds
            iso_str = iso_str.rstrip('0').rstrip('.')
            if '.' not in iso_str:
                iso_str += '.000'
            normalized_data[field] = iso_str
            print(f"  Converted {field}: {value} → {iso_str}")

print(f"\nNormalized data: {json.dumps(normalized_data, indent=2)}")

# Compute hash
tx_json = json.dumps(normalized_data, sort_keys=True, separators=(',', ':'))
computed_hash = hashlib.sha256(tx_json.encode()).hexdigest()

print(f"\nFinal JSON for hashing: {tx_json}")
print(f"Computed hash: {computed_hash}")
print(f"Batch hash:    ba5ba542b41eaa2288e7e5b5342aebfd7a99c22204c28009f8266a7e2e742204")
print(f"Match: {'✅ YES!' if computed_hash == 'ba5ba542b41eaa2288e7e5b5342aebfd7a99c22204c28009f8266a7e2e742204' else '❌ NO'}")