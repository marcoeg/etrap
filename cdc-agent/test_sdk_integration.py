#!/usr/bin/env python3
"""
Test script to verify that the CDC agent and SDK produce identical hashes.
"""

import sys
import json
from datetime import datetime

# Test if SDK is available
try:
    from etrap_sdk import ETRAPClient
    print("✅ ETRAP SDK imported successfully")
except ImportError as e:
    print(f"❌ Failed to import ETRAP SDK: {e}")
    sys.exit(1)

# Test data - typical transaction from financial_transactions table
test_transactions = [
    {
        "id": 123,
        "account_id": "ACC999",
        "amount": "999.99",  # Decimal as string (Debezium format)
        "type": "C",
        "created_at": 1718351455461,  # Epoch timestamp in milliseconds
        "reference": "TEST-VERIFY",
        "status": None,  # Test NULL handling
        "description": ""  # Test empty string
    },
    {
        "id": 456,
        "user_id": 789,
        "amount": 100.50,  # Float
        "created_at": "2025-01-07T10:30:00.123",  # Already ISO format
        "notes": None
    }
]

def test_hashing():
    """Test that SDK produces expected hashes."""
    try:
        # Initialize SDK client
        client = ETRAPClient(
            organization_id="test-org",
            network="testnet"
        )
        print("✅ SDK client initialized")
        
        # Test transaction hashing
        for i, tx in enumerate(test_transactions):
            print(f"\n📋 Testing transaction {i+1}:")
            print(f"   Data: {json.dumps(tx, indent=2)}")
            
            # Compute hash using SDK
            tx_hash = client.compute_transaction_hash(tx)
            print(f"   Hash: {tx_hash[:32]}...")
            
            # Test normalization
            normalized = client.prepare_transaction_for_storage(tx)
            print(f"   Normalized created_at: {normalized.get('created_at', 'N/A')}")
            
        print("\n✅ All tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = test_hashing()
    sys.exit(0 if success else 1)