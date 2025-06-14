#!/usr/bin/env python3
"""Debug script to examine batch contents"""

import asyncio
import json
import boto3
from py_near import providers

async def debug_batch(batch_id: str):
    # Get batch info from blockchain
    provider = providers.JsonProvider('https://rpc.testnet.near.org')
    result = await provider.view_call(
        'acme.testnet',
        'nft_token',
        json.dumps({'token_id': batch_id}).encode('utf-8')
    )
    
    if not result or 'result' not in result:
        print("Batch not found")
        return
        
    batch_info = json.loads(bytes(result['result']).decode('utf-8'))
    
    # The batch_summary might be in metadata.extra or directly in the token
    metadata = batch_info.get('metadata', {})
    if 'extra' in metadata and metadata['extra']:
        extra_data = json.loads(metadata['extra'])
        summary = extra_data.get('batch_summary', {})
    else:
        # Try looking for batch_summary in the root
        summary = batch_info.get('batch_summary', {})
    
    print(f"Batch: {batch_id}")
    print(f"S3 Bucket: {summary['s3_bucket']}")
    print(f"S3 Key: {summary['s3_key']}")
    print(f"Tx Count: {summary['tx_count']}")
    
    # Try to get batch data from S3
    s3 = boto3.client('s3')
    try:
        s3_key = summary['s3_key']
        if not s3_key.endswith('batch-data.json'):
            s3_key = s3_key.rstrip('/') + '/batch-data.json'
            
        response = s3.get_object(Bucket=summary['s3_bucket'], Key=s3_key)
        batch_data = json.loads(response['Body'].read())
        
        print(f"\nTransactions in batch:")
        for tx in batch_data.get('transactions', []):
            meta = tx['metadata']
            print(f"\n  Transaction ID: {meta['transaction_id']}")
            print(f"  Hash: {meta['hash'][:32]}...")
            print(f"  Operation: {meta['operation_type']}")
            print(f"  Table: {meta['table_affected']}")
            
            # Show what was hashed to create this hash
            print(f"  (This is the hash of the decoded transaction data)")
            
    except Exception as e:
        print(f"\nCould not fetch S3 data: {e}")

if __name__ == '__main__':
    import sys
    batch_id = sys.argv[1] if len(sys.argv) > 1 else 'BATCH-2025-06-14-70d0a1ed'
    asyncio.run(debug_batch(batch_id))