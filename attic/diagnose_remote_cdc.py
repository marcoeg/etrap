#!/usr/bin/env python3
"""Diagnose what the remote CDC agent is doing"""

import json
import hashlib
import base64

# The hash from the batch that the remote CDC agent produced
remote_hash = "468340a471164188b044a70584bd89280ef88e3f0f83b022815cbea7f2666f54"

# Transaction data from your database
db_transaction = {
    "id": 91,
    "account_id": "ACC777",
    "amount": 123456.78,
    "type": "C",
    "created_at": "2025-06-14T05:10:44.133755",
    "reference": "FH-21-OP"
}

print("Diagnosing remote CDC agent behavior...")
print("="*60)
print(f"Remote hash: {remote_hash}")
print()

# Test 1: Hash raw database values (what the code SHOULD do)
tx_json = json.dumps(db_transaction, sort_keys=True, separators=(',', ':'))
computed_hash = hashlib.sha256(tx_json.encode()).hexdigest()
print("Test 1 - Raw database values:")
print(f"  JSON: {tx_json}")
print(f"  Hash: {computed_hash}")
print(f"  Match: {'✅ YES' if computed_hash == remote_hash else '❌ NO'}")
print()

# Test 2: Hash with decoded values (cents + microseconds)
decoded_transaction = {
    "id": 91,
    "account_id": "ACC777",
    "amount": 12345678,  # cents
    "type": "C",
    "created_at": 1749877844133755,  # microseconds from batch timestamp
    "reference": "FH-21-OP"
}
tx_json = json.dumps(decoded_transaction, sort_keys=True, separators=(',', ':'))
computed_hash = hashlib.sha256(tx_json.encode()).hexdigest()
print("Test 2 - Decoded values (cents + microseconds):")
print(f"  JSON: {tx_json}")
print(f"  Hash: {computed_hash}")
print(f"  Match: {'✅ YES' if computed_hash == remote_hash else '❌ NO'}")
print()

# Test 3: Simulate what CDC event might look like with base64 encoding
def encode_value(val):
    """Simulate base64 encoding as CDC might do it"""
    if isinstance(val, (int, float)):
        # For numeric values, CDC might encode as big-endian bytes
        if isinstance(val, float):
            # Convert to cents first
            cents = int(val * 100)
            # Convert to bytes (8 bytes for big values)
            return base64.b64encode(cents.to_bytes(8, byteorder='big')).decode('ascii')
        else:
            # Integer ID
            return base64.b64encode(val.to_bytes(8, byteorder='big')).decode('ascii')
    else:
        # String values
        return base64.b64encode(val.encode('utf-8')).decode('ascii')

# Create CDC-style encoded event
cdc_event = {
    "id": encode_value(91),
    "account_id": encode_value("ACC777"),
    "amount": encode_value(123456.78),
    "type": encode_value("C"),
    "created_at": encode_value("2025-06-14T05:10:44.133755"),
    "reference": encode_value("FH-21-OP")
}

print("Test 3 - CDC base64 encoded event:")
print(f"  Encoded event: {json.dumps(cdc_event, indent=2)}")

# Test if hashing the encoded event matches
tx_json = json.dumps(cdc_event, sort_keys=True, separators=(',', ':'))
computed_hash = hashlib.sha256(tx_json.encode()).hexdigest()
print(f"  Hash of encoded: {computed_hash}")
print(f"  Match: {'✅ YES' if computed_hash == remote_hash else '❌ NO'}")
print()

# Test 4: Check if remote is running old code that calls decode_record
# The old code would have decoded the CDC event before hashing
print("Test 4 - Checking for specific issue:")
print("  The remote CDC agent might be:")
print("  1. Running from a different file path")
print("  2. Using cached Python bytecode (.pyc files)")
print("  3. Not fully restarted (still running old process)")
print("  4. Running in a different Python environment")
print()
print("Recommendations:")
print("1. On remote server, check for multiple python processes:")
print("   ps aux | grep etrap_cdc_agent")
print("2. Kill ALL CDC agent processes:")
print("   pkill -f etrap_cdc_agent")
print("3. Clear Python cache:")
print("   find . -name '*.pyc' -delete")
print("   find . -name '__pycache__' -type d -exec rm -rf {} +")
print("4. Verify the exact file being run:")
print("   which python3")
print("   python3 -c 'import sys; print(sys.version)'")
print("5. Add debug logging to the CDC agent at line 608:")
print("   print(f'DEBUG: Hashing {tx_data_to_hash}')")