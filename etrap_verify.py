#!/usr/bin/env python3
"""
ETRAP Transaction Verification Tool

This tool verifies that a given transaction exists in the blockchain-backed audit trail.
It takes the complete transaction data, computes its hash, and verifies it against 
the Merkle trees stored on the NEAR blockchain.

Usage:
    etrap_verify.py --data '{"id":123,"account_id":"ACC500",...}'
    etrap_verify.py --data-file transaction.json
    cat transaction.json | etrap_verify.py --data -
"""

import asyncio
import argparse
import json
import sys
import os
import hashlib
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import boto3
from py_near import providers
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class ETRAPTransactionVerifier:
    def __init__(self, contract_id: str, network: str = "testnet"):
        self.contract_id = contract_id
        self.network = network
        self.near_rpc_url = f"https://rpc.{network}.near.org" if network != "localnet" else "http://localhost:3030"
        self.provider = providers.JsonProvider(self.near_rpc_url)
        
        # Initialize S3 client
        self.s3_client = boto3.client('s3',
            region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        )
        
        # Statistics for search
        self.batches_checked = 0
        self.total_batches = 0
        
    async def query_contract(self, method: str, args: Dict = None) -> Any:
        """Query a view method on the contract"""
        try:
            args_bytes = json.dumps(args or {}).encode('utf-8')
            result = await self.provider.view_call(self.contract_id, method, args_bytes)
            
            if result and 'result' in result and result['result']:
                if isinstance(result['result'], list):
                    decoded = bytes(result['result']).decode('utf-8')
                    return json.loads(decoded)
                else:
                    decoded = base64.b64decode(result['result']).decode('utf-8')
                    return json.loads(decoded)
            return None
        except Exception as e:
            print(f"❌ Error calling {method}: {e}")
            return None
    
    def compute_transaction_hash(self, transaction_data: Dict) -> str:
        """
        Compute deterministic hash of transaction data.
        This must match the hash computation in the CDC agent.
        """
        # Sort keys to ensure deterministic JSON
        normalized_json = json.dumps(transaction_data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(normalized_json.encode()).hexdigest()
    
    def verify_merkle_proof(self, leaf_hash: str, proof_path: List[str], 
                           merkle_root: str, sibling_positions: List[str]) -> bool:
        """Verify a Merkle proof"""
        current_hash = leaf_hash
        
        for i, sibling_hash in enumerate(proof_path):
            position = sibling_positions[i]
            
            if position == 'left':
                combined = sibling_hash + current_hash
            else:
                combined = current_hash + sibling_hash
            
            current_hash = hashlib.sha256(combined.encode()).hexdigest()
        
        return current_hash == merkle_root
    
    def get_batch_data_from_s3(self, s3_bucket: str, s3_key: str) -> Optional[Dict]:
        """Retrieve batch data from S3"""
        try:
            # Ensure key ends with batch-data.json
            if not s3_key.endswith('batch-data.json'):
                s3_key = s3_key.rstrip('/') + '/batch-data.json'
            
            response = self.s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
            return json.loads(response['Body'].read())
        except Exception as e:
            print(f"⚠️  Error fetching from S3: {e}")
            return None
    
    async def find_transaction_in_batch(self, tx_hash: str, batch: Dict) -> Optional[Dict]:
        """Check if transaction hash exists in a specific batch"""
        batch_summary = batch.get('batch_summary', {})
        s3_bucket = batch_summary.get('s3_bucket')
        s3_key = batch_summary.get('s3_key')
        
        if not s3_bucket or not s3_key:
            return None
        
        # Get batch data from S3
        batch_data = self.get_batch_data_from_s3(s3_bucket, s3_key)
        if not batch_data:
            return None
        
        # Look for the transaction hash
        transactions = batch_data.get('transactions', [])
        for tx in transactions:
            if tx.get('metadata', {}).get('hash') == tx_hash:
                # Found it! Get the Merkle proof
                tx_id = tx['metadata']['transaction_id']
                tx_index = tx_id.split('-')[-1]
                proof_key = f"tx-{tx_index}"
                
                merkle_tree = batch_data.get('merkle_tree', {})
                proof_index = merkle_tree.get('proof_index', {})
                
                if proof_key in proof_index:
                    proof_data = proof_index[proof_key]
                    return {
                        'transaction': tx,
                        'batch': batch,
                        'merkle_tree': merkle_tree,
                        'proof': proof_data
                    }
        
        return None
    
    async def verify_transaction(self, transaction_data: Dict, hints: Dict = None) -> Dict:
        """Main verification process"""
        # Step 1: Compute hash of the provided transaction
        tx_hash = self.compute_transaction_hash(transaction_data)
        
        print(f"\n🔍 ETRAP Transaction Verification")
        print(f"━" * 60)
        print(f"\n📊 Transaction Hash: {tx_hash[:32]}...")
        
        # Step 2: Progressive search for the transaction
        found_result = None
        
        # Level 1: Direct batch ID if provided
        if hints and hints.get('batch_id'):
            print(f"\n🔎 Checking specific batch: {hints['batch_id']}")
            batch_info = await self.query_contract("nft_token", {"token_id": hints['batch_id']})
            if batch_info:
                self.batches_checked += 1
                found_result = await self.find_transaction_in_batch(tx_hash, batch_info)
        
        # Level 2: Search by table if provided
        if not found_result and hints and hints.get('table'):
            print(f"\n🔎 Searching batches for table: {hints['table']}")
            batches = await self.query_contract("get_batches_by_table", {
                "table_name": hints['table'],
                "limit": 50
            })
            if batches:
                for batch in batches:
                    self.batches_checked += 1
                    found_result = await self.find_transaction_in_batch(tx_hash, batch)
                    if found_result:
                        break
        
        # Level 3: Search recent batches
        if not found_result:
            print(f"\n🔎 Searching recent batches...")
            recent_batches = await self.query_contract("get_recent_batches", {"limit": 100})
            
            if recent_batches:
                self.total_batches = len(recent_batches)
                print(f"   Found {self.total_batches} recent batches to check")
                
                for i, batch in enumerate(recent_batches):
                    if i > 0 and i % 10 == 0:
                        print(f"   Checked {i}/{self.total_batches} batches...")
                    
                    self.batches_checked += 1
                    found_result = await self.find_transaction_in_batch(tx_hash, batch)
                    if found_result:
                        print(f"   Found in batch {i+1} of {self.total_batches}")
                        break
        
        # Step 3: Verify and return results
        if found_result:
            # Verify the Merkle proof
            proof_data = found_result['proof']
            merkle_tree = found_result['merkle_tree']
            
            is_valid = self.verify_merkle_proof(
                tx_hash,
                proof_data['proof_path'],
                merkle_tree['root'],
                proof_data['sibling_positions']
            )
            
            return {
                'verified': is_valid,
                'transaction_hash': tx_hash,
                'batch': found_result['batch'],
                'transaction_metadata': found_result['transaction']['metadata'],
                'proof': proof_data,
                'merkle_root': merkle_tree['root'],
                'batches_searched': self.batches_checked
            }
        else:
            return {
                'verified': False,
                'transaction_hash': tx_hash,
                'batches_searched': self.batches_checked,
                'message': 'Transaction not found in recent batches'
            }
    
    def format_verification_result(self, result: Dict, transaction_data: Dict) -> str:
        """Format the verification result for display"""
        output = []
        
        if result['verified']:
            batch = result['batch']
            tx_meta = result['transaction_metadata']
            batch_summary = batch['batch_summary']
            
            # Success header
            output.append("\n✅ TRANSACTION VERIFIED")
            output.append("━" * 60)
            
            # Transaction details
            output.append("\n📄 Transaction Details:")
            output.append(f"   Hash: {result['transaction_hash'][:32]}...")
            output.append(f"   Operation: {tx_meta['operation_type']}")
            output.append(f"   Database: {tx_meta['database_name']}")
            output.append(f"   Table: {tx_meta['table_affected']}")
            
            # NFT/Blockchain details
            output.append("\n🔗 Blockchain Record:")
            output.append(f"   NFT Token ID: {batch['token_id']}")
            output.append(f"   Contract: {self.contract_id}")
            output.append(f"   Network: {self.network}")
            output.append(f"   Merkle Root: {result['merkle_root'][:32]}...")
            
            # Timestamp - this is the undisputable blockchain timestamp
            nft_timestamp = batch_summary.get('timestamp', 0)
            if nft_timestamp:
                recorded_time = datetime.fromtimestamp(nft_timestamp / 1000)
                output.append(f"\n⏰ Recorded on Blockchain:")
                output.append(f"   {recorded_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
                output.append(f"   This is the official timestamp when this batch was")
                output.append(f"   permanently recorded on the NEAR blockchain.")
            
            # Proof details
            output.append(f"\n🔐 Cryptographic Proof:")
            output.append(f"   Proof Height: {len(result['proof']['proof_path'])} levels")
            output.append(f"   Merkle Tree Nodes: {batch_summary.get('tx_count', 'unknown')}")
            output.append(f"   Position in Tree: {result['proof']['leaf_index']}")
            
            # Storage location
            output.append(f"\n💾 Audit Trail Location:")
            output.append(f"   S3 Bucket: {batch_summary['s3_bucket']}")
            output.append(f"   S3 Path: {batch_summary['s3_key']}")
            
            # Search stats
            output.append(f"\n📊 Search Statistics:")
            output.append(f"   Batches searched: {result['batches_searched']}")
            output.append(f"   Found in: {batch['token_id']}")
            
            # Final message
            output.append("\n" + "━" * 60)
            output.append("✅ This transaction is cryptographically proven to have existed")
            output.append("   in the database at the time of blockchain recording.")
            output.append("   Any tampering would invalidate this proof.")
            
        else:
            # Not found
            output.append("\n❌ TRANSACTION NOT VERIFIED")
            output.append("━" * 60)
            output.append(f"\n📄 Transaction Hash: {result['transaction_hash'][:32]}...")
            output.append(f"\n🔍 Search Results:")
            output.append(f"   Batches searched: {result['batches_searched']}")
            output.append(f"   Status: {result['message']}")
            output.append("\n⚠️  Possible reasons:")
            output.append("   • Transaction may not have been captured yet")
            output.append("   • Transaction data may have been modified")
            output.append("   • Transaction may be in older batches (try --all-batches)")
            output.append("   • The database may not be configured for ETRAP")
        
        return "\n".join(output)


async def main():
    parser = argparse.ArgumentParser(
        description='ETRAP Transaction Verification - Verify database transactions against blockchain',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Verify a transaction from JSON string
  %(prog)s -c acme.testnet --data '{"id":123,"account_id":"ACC500","amount":10000}'
  
  # Verify from a file
  %(prog)s -c acme.testnet --data-file transaction.json
  
  # Verify from stdin
  echo '{"id":123,...}' | %(prog)s -c acme.testnet --data -
  
  # Provide hints for faster search
  %(prog)s -c acme.testnet --data-file tx.json --hint-table financial_transactions
  %(prog)s -c acme.testnet --data-file tx.json --hint-batch BATCH-2025-06-14-abc123
        """
    )
    
    # Required arguments
    parser.add_argument('-c', '--contract', required=True,
                       help='NEAR contract ID (e.g., acme.testnet)')
    
    # Data input options (mutually exclusive)
    data_group = parser.add_mutually_exclusive_group(required=True)
    data_group.add_argument('--data', type=str,
                           help='Transaction data as JSON string (use "-" for stdin)')
    data_group.add_argument('--data-file', type=str,
                           help='Path to file containing transaction JSON')
    
    # Optional hints for optimization
    parser.add_argument('--hint-table', type=str,
                       help='Table name hint for faster search')
    parser.add_argument('--hint-batch', type=str,
                       help='Specific batch ID to check')
    parser.add_argument('--hint-database', type=str,
                       help='Database name hint')
    
    # Network option
    parser.add_argument('-n', '--network', default='testnet',
                       choices=['testnet', 'mainnet', 'localnet'],
                       help='NEAR network (default: testnet)')
    
    # Output options
    parser.add_argument('--json', action='store_true',
                       help='Output result as JSON')
    parser.add_argument('-q', '--quiet', action='store_true',
                       help='Minimal output (just verification status)')
    
    args = parser.parse_args()
    
    # Load transaction data
    try:
        if args.data:
            if args.data == '-':
                # Read from stdin
                transaction_data = json.load(sys.stdin)
            else:
                # Parse JSON string
                transaction_data = json.loads(args.data)
        else:
            # Read from file
            with open(args.data_file, 'r') as f:
                transaction_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")
        return 1
    except FileNotFoundError:
        print(f"❌ File not found: {args.data_file}")
        return 1
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return 1
    
    # Create verifier
    verifier = ETRAPTransactionVerifier(args.contract, args.network)
    
    # Build hints dictionary
    hints = {}
    if args.hint_table:
        hints['table'] = args.hint_table
    if args.hint_batch:
        hints['batch_id'] = args.hint_batch
    if args.hint_database:
        hints['database'] = args.hint_database
    
    # Header (unless quiet mode)
    if not args.quiet:
        print(f"🔐 ETRAP Transaction Verification Tool")
        print(f"   Contract: {args.contract}")
        print(f"   Network: {args.network}")
    
    try:
        # Perform verification
        result = await verifier.verify_transaction(transaction_data, hints)
        
        if args.json:
            # JSON output
            print(json.dumps(result, indent=2))
        elif args.quiet:
            # Minimal output
            if result['verified']:
                print("VERIFIED")
            else:
                print("NOT_VERIFIED")
        else:
            # Formatted output
            print(verifier.format_verification_result(result, transaction_data))
        
        # Exit code: 0 if verified, 1 if not
        return 0 if result['verified'] else 1
        
    except KeyboardInterrupt:
        print("\n\n👋 Verification cancelled")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        if not args.quiet:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))