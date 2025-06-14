#!/usr/bin/env python3
"""Test the verification tool's normalization"""

import subprocess
import json

test_cases = [
    {
        "name": "Raw database format",
        "data": {
            "id": 109,
            "account_id": "ACC999",
            "amount": 999.99,
            "type": "C", 
            "created_at": "2025-06-14 07:10:55.461133",
            "reference": "TEST-VERIFY"
        }
    },
    {
        "name": "Already normalized",
        "data": {
            "id": 109,
            "account_id": "ACC999", 
            "amount": "999.99",
            "type": "C",
            "created_at": "2025-06-14T07:10:55.461",
            "reference": "TEST-VERIFY"
        }
    },
    {
        "name": "Mixed format",
        "data": {
            "id": 109,
            "account_id": "ACC999",
            "amount": 999.99,  # Numeric
            "type": "C",
            "created_at": "2025-06-14T07:10:55.461133",  # T separator but 6 decimals
            "reference": "TEST-VERIFY"
        }
    }
]

print("Testing verification tool normalization")
print("=" * 60)

for test in test_cases:
    print(f"\n{test['name']}:")
    print(f"Input: {json.dumps(test['data'])}")
    
    # Run verification
    cmd = [
        'python3', 'etrap_verify.py',
        '-c', 'acme.testnet',
        '--data', json.dumps(test['data']),
        '-q'  # Quiet mode
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Verification successful")
    else:
        print("❌ Verification failed")
        if result.stderr:
            print(f"Error: {result.stderr}")

print("\nAll formats should verify successfully with automatic normalization!")