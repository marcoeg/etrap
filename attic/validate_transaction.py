#!/usr/bin/env python3
"""
ETRAP Transaction Validator
Validates that a specific transaction is included in an NFT batch using Merkle proof verification
"""

import json
import hashlib
import boto3
from typing import Dict, List, Optional, Tuple
import asyncio
from py_near import account, providers
import base64
import argparse
from datetime import datetime


class ETRAPValidator:
    def __init__(self, near_account_id: str, contract_id: str, network: str = "testnet"):
        """Initialize the validator with NEAR connection details"""
        self.near_account_id = near_account_id
        self.contract_id = contract_id
        self.network = network
        
        # Initialize NEAR RPC provider
        if network == "testnet":
            self.rpc_url = "https://rpc.testnet.near.org"
        else:
            self.rpc_url = "https://rpc.mainnet.near.org"
            
        self.provider = providers.JsonProvider(self.rpc_url)
        
        # Initialize S3 client
        self.s3 = boto3.client('s3')
    
    async def get_nft_metadata(self, token_id: str) -> Dict:
        """Retrieve NFT metadata from NEAR blockchain"""
        print(f"🔍 Fetching NFT metadata for token: {token_id}")
        
        # Prepare arguments - need to serialize to bytes
        args = json.dumps({"token_id": token_id}).encode('utf-8')
        
        # Call view method on contract
        result = await self.provider.view_call(
            self.contract_id,
            "nft_token",
            args
        )
        
        # Debug: print raw result
        if '--debug' in __import__('sys').argv:
            print(f"DEBUG: Raw result: {result}")
        
        if result:
            # The result might be in different formats depending on the RPC response
            if 'result' in result and result['result']:
                # The result is a list of bytes, convert to string
                if isinstance(result['result'], list):
                    # Convert list of bytes to bytes object
                    decoded = bytes(result['result']).decode('utf-8')
                    nft_data = json.loads(decoded)
                else:
                    # Decode base64 result if it exists
                    decoded = base64.b64decode(result['result']).decode('utf-8')
                    nft_data = json.loads(decoded)
            elif 'error' in result:
                raise Exception(f"RPC Error: {result['error']}")
            else:
                # Result might already be the NFT data
                nft_data = result
            
            # Check if we have the metadata
            if not nft_data or 'metadata' not in nft_data:
                raise Exception(f"NFT {token_id} not found or invalid response")
            
            # Parse the reference URL to get S3 bucket and key
            reference = nft_data['metadata'].get('reference', '')
            if not reference:
                raise Exception("NFT missing reference URL")
            
            # Extract bucket and key from S3 URL
            # Format: https://s3.amazonaws.com/bucket-name/path/to/file
            if 's3.amazonaws.com' in reference:
                parts = reference.split('s3.amazonaws.com/', 1)[1].split('/', 1)
                s3_bucket = parts[0]
                s3_key = parts[1].replace('/batch-data.json', '/')
            else:
                raise Exception(f"Invalid S3 reference URL: {reference}")
            
            print(f"✅ Found NFT: {nft_data['metadata']['title']}")
            print(f"   Reference: {reference}")
            
            # Create batch_summary from parsed data
            nft_data['batch_summary'] = {
                's3_bucket': s3_bucket,
                's3_prefix': s3_key,
                'token_id': token_id
            }
            
            return nft_data
        else:
            raise Exception(f"NFT {token_id} not found")
    
    def get_batch_data_from_s3(self, bucket: str, key_prefix: str) -> Dict:
        """Retrieve batch data from S3"""
        print(f"\n📦 Fetching batch data from S3...")
        print(f"   Bucket: {bucket}")
        print(f"   Key: {key_prefix}batch-data.json")
        
        try:
            response = self.s3.get_object(
                Bucket=bucket,
                Key=f"{key_prefix}batch-data.json"
            )
            
            batch_data = json.loads(response['Body'].read().decode('utf-8'))
            print(f"✅ Retrieved batch data with {len(batch_data['transactions'])} transactions")
            
            return batch_data
        except Exception as e:
            print(f"❌ Error fetching from S3: {e}")
            raise
    
    def decode_field_value(self, value):
        """Decode potentially base64 encoded field values"""
        if isinstance(value, str):
            # Check if it looks like base64
            if value and all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=' for c in value):
                try:
                    import base64
                    decoded = base64.b64decode(value)
                    
                    # Check if it's a numeric value encoded as bytes
                    if len(decoded) <= 8:
                        try:
                            # Try as big-endian integer (likely cents)
                            int_value = int.from_bytes(decoded, 'big')
                            # If it looks like cents (reasonable range), convert to dollars
                            if 0 < int_value < 10**10:  # Up to 100 million dollars
                                return int_value / 100.0
                        except:
                            pass
                    
                    # Try to decode as string
                    try:
                        return decoded.decode('utf-8', errors='ignore')
                    except:
                        return decoded.decode('latin-1', errors='ignore')
                except:
                    pass
        return value

    def find_transaction(self, batch_data: Dict, criteria: Dict) -> Optional[Dict]:
        """Find a specific transaction in the batch based on criteria"""
        print(f"\n🔎 Searching for transaction with criteria: {criteria}")
        
        for tx in batch_data['transactions']:
            match = True
            change_data = tx['metadata'].get('change_data', {})
            
            # Check each criterion
            for key, value in criteria.items():
                if key == 'account_id' and change_data.get('account_id') != value:
                    match = False
                    break
                elif key == 'amount':
                    # Decode the amount field if it's base64 encoded
                    amount_value = self.decode_field_value(change_data.get('amount', 0))
                    if float(amount_value) != value:
                        match = False
                        break
                elif key == 'type' and change_data.get('type') != value:
                    match = False
                    break
                elif key == 'operation' and tx['metadata'].get('operation_type') != value:
                    match = False
                    break
                elif key == 'table' and tx['metadata'].get('table_affected') != value:
                    match = False
                    break
            
            if match:
                print(f"✅ Found transaction: {tx['metadata']['transaction_id']}")
                return tx
        
        print("❌ Transaction not found")
        return None
    
    def sha256_hash(self, data: str) -> str:
        """Calculate SHA256 hash"""
        return hashlib.sha256(data.encode()).hexdigest()
    
    def verify_merkle_proof(self, leaf_hash: str, proof_path: List[str], merkle_root: str, sibling_positions: List[str] = None) -> bool:
        """Verify a Merkle proof"""
        print(f"\n🔐 Verifying Merkle proof...")
        print(f"   Leaf hash: {leaf_hash[:16]}...")
        print(f"   Proof length: {len(proof_path)} nodes")
        print(f"   Expected root: {merkle_root[:16]}...")
        
        current_hash = leaf_hash
        
        for i, sibling_hash in enumerate(proof_path):
            # Determine position - if not provided, assume standard binary tree positioning
            if sibling_positions:
                position = sibling_positions[i]
            else:
                # In a standard binary tree, even indices have siblings on the right
                position = 'right'
            
            if position == 'left':
                combined = sibling_hash + current_hash
            else:
                combined = current_hash + sibling_hash
            
            current_hash = self.sha256_hash(combined)
            print(f"   Level {i+1}: {current_hash[:16]}...")
        
        print(f"\n   Calculated root: {current_hash[:16]}...")
        
        if current_hash == merkle_root:
            print("✅ Merkle proof is VALID!")
            return True
        else:
            print("❌ Merkle proof is INVALID!")
            return False
    
    async def validate_transaction(self, token_id: str, search_criteria: Dict):
        """Main validation flow"""
        print(f"🚀 ETRAP Transaction Validator")
        print(f"   Contract: {self.contract_id}")
        print(f"   Network: {self.network}")
        print("=" * 60)
        
        try:
            # Step 1: Get NFT metadata from blockchain
            nft_data = await self.get_nft_metadata(token_id)
            batch_summary = nft_data['batch_summary']
            
            # Step 2: Parse table name from NFT description
            description = nft_data['metadata'].get('description', '')
            # Extract table name from description like "... from table financial_transactions"
            table_name = None
            if 'from table' in description:
                table_name = description.split('from table ')[-1].strip()
            
            # Step 2b: Get batch data from S3
            s3_location = batch_summary['s3_bucket']
            # Fix the S3 key to include database and table
            if table_name:
                # Assuming database is 'etrapdb' based on CDC output
                s3_key = f"etrapdb/{table_name}/{token_id}/"
            else:
                s3_key = batch_summary['s3_prefix']
            
            batch_data = self.get_batch_data_from_s3(s3_location, s3_key)
            
            # Step 3: Find the specific transaction
            transaction = self.find_transaction(batch_data, search_criteria)
            
            if not transaction:
                print("\n❌ Validation failed: Transaction not found in batch")
                return False
            
            # Step 4: Get the Merkle proof for this transaction
            tx_id = transaction['metadata']['transaction_id']
            # Extract the index from the transaction ID (e.g., "BATCH-2025-06-14-776e2080-T0-0" -> "tx-0")
            tx_index = tx_id.split('-')[-1]
            proof_key = f"tx-{tx_index}"
            
            if proof_key not in batch_data['merkle_tree']['proof_index']:
                print(f"❌ No Merkle proof found for transaction {tx_id} (looking for key: {proof_key})")
                return False
            
            proof_data = batch_data['merkle_tree']['proof_index'][proof_key]
            
            # Step 5: Verify the Merkle proof
            leaf_hash = transaction['merkle_leaf']['hash']
            merkle_root = batch_data['merkle_tree']['root']
            
            is_valid = self.verify_merkle_proof(
                leaf_hash,
                proof_data['proof_path'],
                merkle_root,
                proof_data.get('sibling_positions')
            )
            
            # Step 6: Display verification results
            print(f"\n📊 Merkle Root Verification:")
            print(f"   Calculated root: {merkle_root[:32]}...")
            print(f"   Batch contains {len(batch_data['transactions'])} transactions")
            
            # Display transaction details
            print(f"\n📄 Transaction Details:")
            print(f"   ID: {tx_id}")
            print(f"   Table: {transaction['metadata']['table_affected']}")
            print(f"   Operation: {transaction['metadata']['operation_type']}")
            print(f"   Timestamp: {datetime.fromtimestamp(transaction['metadata']['timestamp']/1000)}")
            
            if 'change_data' in transaction['metadata']:
                print(f"   Data: {json.dumps(transaction['metadata']['change_data'], indent=6)}")
            
            print(f"\n🏁 Final Result: {'VALID ✅' if is_valid else 'INVALID ❌'}")
            
            return is_valid
            
        except Exception as e:
            print(f"\n❌ Error during validation: {e}")
            import traceback
            traceback.print_exc()
            return False


async def main():
    parser = argparse.ArgumentParser(description='Validate ETRAP transactions')
    parser.add_argument('--contract', default='acme.testnet', help='ETRAP contract ID')
    parser.add_argument('--account', default='acme.testnet', help='NEAR account ID')
    parser.add_argument('--token-id', required=True, help='NFT token ID to validate')
    parser.add_argument('--network', default='testnet', choices=['testnet', 'mainnet'])
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    
    # Search criteria arguments
    parser.add_argument('--account-id', help='Account ID to search for')
    parser.add_argument('--amount', type=float, help='Transaction amount')
    parser.add_argument('--type', help='Transaction type (C/D/T)')
    parser.add_argument('--operation', help='Operation type (INSERT/UPDATE/DELETE)')
    parser.add_argument('--table', help='Table name')
    
    args = parser.parse_args()
    
    # Build search criteria from arguments
    search_criteria = {}
    if args.account_id:
        search_criteria['account_id'] = args.account_id
    if args.amount:
        search_criteria['amount'] = args.amount
    if args.type:
        search_criteria['type'] = args.type
    if args.operation:
        search_criteria['operation'] = args.operation
    if args.table:
        search_criteria['table'] = args.table
    
    if not search_criteria:
        print("❌ Please provide at least one search criterion")
        return
    
    # Create validator and run validation
    validator = ETRAPValidator(args.account, args.contract, args.network)
    await validator.validate_transaction(args.token_id, search_criteria)


if __name__ == "__main__":
    # Example usage for validating the $10,000 deposit:
    # python validate_transaction.py --token-id BATCH-2025-06-13-04226f18-T1 --account-id ACC500 --amount 10000 --type C
    
    # Example usage for validating one of the transfers:
    # python validate_transaction.py --token-id BATCH-2025-06-13-04226f18-T1 --account-id ACC501 --amount 3000 --type C
    
    # Example usage for validating the audit log:
    # python validate_transaction.py --token-id BATCH-2025-06-13-04226f18-T0 --table audit_logs --operation INSERT
    
    asyncio.run(main())