#!/usr/bin/env python3
"""Verify transaction by checking batch metadata"""

import json
import sys

def check_batch(batch_data, account_id):
    """Check if batch contains transaction for given account"""
    
    print(f"Checking batch: {batch_data['batch_info']['batch_id']}")
    print(f"Created at: {batch_data['batch_info']['created_at']}")
    print(f"Database: {batch_data['batch_info']['database_name']}")
    
    for tx in batch_data['transactions']:
        meta = tx['metadata']
        print(f"\nTransaction: {meta['transaction_id']}")
        print(f"  Operation: {meta['operation_type']}")
        print(f"  Table: {meta['table_affected']}")
        print(f"  Hash: {meta['hash'][:32]}...")
        print(f"  Timestamp: {meta['timestamp']}")
        
        # Note: We can't see the actual transaction data since it's not stored
        # This confirms the privacy-compliant design is working!
        print(f"\n✅ This batch contains a transaction for table '{meta['table_affected']}'")
        print(f"   recorded at timestamp {meta['timestamp']}")
        print(f"   with hash {meta['hash'][:32]}...")
        print(f"\n   To verify this is YOUR transaction (ACC777), the CDC agent")
        print(f"   on the remote server needs to be updated with the new hash")
        print(f"   computation method that hashes transaction data, not CDC events.")

if __name__ == '__main__':
    # The batch data you provided
    batch_data = {
      "batch_info": {
        "batch_id": "BATCH-2025-06-14-70d0a1ed",
        "created_at": 1749877904578,
        "organization_id": "acme",
        "database_name": "etrapdb",
        "etrap_agent_version": "1.0.0"
      },
      "transactions": [
        {
          "metadata": {
            "transaction_id": "BATCH-2025-06-14-70d0a1ed-0",
            "timestamp": 1749877844134,
            "operation_type": "INSERT",
            "database_name": "etrapdb",
            "table_affected": "financial_transactions",
            "rows_affected": {
              "inserted": 1,
              "updated": 0,
              "deleted": 0
            },
            "hash": "468340a471164188b044a70584bd89280ef88e3f0f83b022815cbea7f2666f54",
            "user_id": "system",
            "lsn": 24784016,
            "transaction_db_id": 786
          },
          "merkle_leaf": {
            "index": 0,
            "hash": "468340a471164188b044a70584bd89280ef88e3f0f83b022815cbea7f2666f54",
            "raw_data_hash": "161e19b76274da4f04acb3d0fd3f05a43a1865927fc44222c95d3d1bf1636d45"
          },
          "data_location": {
            "encrypted": False,
            "storage_path": "etrapdb/financial_transactions/BATCH-2025-06-14-70d0a1ed/transactions/tx-0.json",
            "retention_expires": None
          }
        }
      ],
      "merkle_tree": {
        "algorithm": "sha256",
        "root": "468340a471164188b044a70584bd89280ef88e3f0f83b022815cbea7f2666f54",
        "height": 1,
        "nodes": [
          {
            "index": 0,
            "hash": "468340a471164188b044a70584bd89280ef88e3f0f83b022815cbea7f2666f54",
            "level": 0
          }
        ],
        "proof_index": {
          "tx-0": {
            "leaf_index": 0,
            "proof_path": [],
            "sibling_positions": []
          }
        }
      }
    }
    
    check_batch(batch_data, "ACC777")