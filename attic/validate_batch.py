#!/usr/bin/env python3
"""
ETRAP Generic Batch Validator

This validator uses the smart contract's built-in indices to find and validate batches
without assuming any specific table structure or transaction fields.
"""

import asyncio
import argparse
import json
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import boto3
from py_near import account, providers
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ETRAPGenericValidator:
    def __init__(self, contract_id: str, network: str = "testnet"):
        self.contract_id = contract_id
        self.network = network
        self.near_rpc_url = f"https://rpc.{network}.near.org" if network != "localnet" else "http://localhost:3030"
        
        # Initialize S3 client
        self.s3_client = boto3.client('s3',
            region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        )
    
    async def query_contract(self, method: str, args: Dict = None) -> Any:
        """Query a view method on the contract"""
        # Initialize provider if not already done
        if not hasattr(self, 'provider'):
            self.provider = providers.JsonProvider(self.near_rpc_url)
        
        try:
            # Prepare arguments - need to serialize to bytes
            args_bytes = json.dumps(args or {}).encode('utf-8')
            
            # Call view method on contract
            result = await self.provider.view_call(
                self.contract_id,
                method,
                args_bytes
            )
            
            # Parse the result
            if result:
                # The result might be in different formats depending on the RPC response
                if 'result' in result and result['result']:
                    # The result is a list of bytes, convert to string
                    if isinstance(result['result'], list):
                        # Convert list of bytes to bytes object
                        decoded = bytes(result['result']).decode('utf-8')
                        return json.loads(decoded)
                    else:
                        # Decode base64 result if it exists
                        import base64
                        decoded = base64.b64decode(result['result']).decode('utf-8')
                        return json.loads(decoded)
                elif 'error' in result:
                    print(f"❌ RPC Error: {result['error']}")
                    return None
            return None
            
        except Exception as e:
            print(f"❌ Error calling {method}: {e}")
            return None
    
    async def get_recent_batches(self, limit: int = 10) -> List[Dict]:
        """Get recent batches from the contract"""
        print(f"\n🔍 Fetching recent batches (limit: {limit})...")
        batches = await self.query_contract("get_recent_batches", {"limit": limit})
        return batches or []
    
    async def get_batches_by_database(self, database: str, from_index: int = 0, limit: int = 10) -> Dict:
        """Get batches for a specific database"""
        print(f"\n🔍 Fetching batches for database: {database}")
        result = await self.query_contract("get_batches_by_database", {
            "database": database,
            "from_index": from_index,
            "limit": limit
        })
        return result or {"batches": [], "total_count": 0, "has_more": False}
    
    async def get_batches_by_time_range(self, start_time: datetime, end_time: datetime, 
                                       database: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Get batches within a time range"""
        start_ms = int(start_time.timestamp() * 1000)
        end_ms = int(end_time.timestamp() * 1000)
        
        print(f"\n🔍 Fetching batches from {start_time} to {end_time}")
        if database:
            print(f"   Filtered by database: {database}")
            
        args = {
            "start_timestamp": start_ms,
            "end_timestamp": end_ms,
            "limit": limit
        }
        if database:
            args["database"] = database
            
        batches = await self.query_contract("get_batches_by_time_range", args)
        return batches or []
    
    async def get_batches_by_table(self, table_name: str, limit: int = 50) -> List[Dict]:
        """Get batches that include a specific table"""
        print(f"\n🔍 Fetching batches containing table: {table_name}")
        batches = await self.query_contract("get_batches_by_table", {
            "table_name": table_name,
            "limit": limit
        })
        return batches or []
    
    async def get_batch_details(self, token_id: str) -> Optional[Dict]:
        """Get detailed information about a specific batch"""
        print(f"\n📦 Fetching details for batch: {token_id}")
        
        # Get NFT information
        token_info = await self.query_contract("nft_token", {"token_id": token_id})
        if not token_info:
            print(f"❌ Token {token_id} not found")
            return None
            
        # Get batch summary
        batch_summary = await self.query_contract("get_batch_summary", {"token_id": token_id})
        if not batch_summary:
            print(f"❌ Batch summary for {token_id} not found")
            return None
            
        return {
            "token_info": token_info,
            "batch_summary": batch_summary
        }
    
    async def verify_batch_merkle_root(self, token_id: str, transaction_hashes: List[str]) -> bool:
        """Verify that a set of transactions produces the expected merkle root"""
        batch_details = await self.get_batch_details(token_id)
        if not batch_details:
            return False
            
        expected_root = batch_details["batch_summary"]["merkle_root"]
        
        # Compute merkle root from transactions
        computed_root = await self.query_contract("compute_merkle_root", {
            "transaction_hashes": transaction_hashes,
            "use_sha256": True
        })
        
        print(f"\n🔐 Merkle Root Verification:")
        print(f"   Expected: {expected_root[:32]}...")
        print(f"   Computed: {computed_root[:32]}...")
        
        is_valid = computed_root == expected_root
        print(f"   Result: {'✅ VALID' if is_valid else '❌ INVALID'}")
        
        return is_valid
    
    def get_s3_batch_data(self, s3_bucket: str, s3_key: str) -> Optional[Dict]:
        """Retrieve batch data from S3"""
        try:
            # Ensure key ends with batch-data.json
            if not s3_key.endswith('batch-data.json'):
                s3_key = s3_key.rstrip('/') + '/batch-data.json'
                
            print(f"\n📥 Downloading from S3:")
            print(f"   Bucket: {s3_bucket}")
            print(f"   Key: {s3_key}")
            
            response = self.s3_client.get_object(
                Bucket=s3_bucket,
                Key=s3_key
            )
            
            batch_data = json.loads(response['Body'].read())
            print(f"✅ Retrieved batch data with {len(batch_data.get('transactions', []))} transactions")
            return batch_data
            
        except Exception as e:
            print(f"❌ Error fetching from S3: {e}")
            return None
    
    def display_batch_info(self, batch: Dict, detailed: bool = False):
        """Display batch information in a formatted way"""
        token_id = batch.get('token_id', 'Unknown')
        owner_id = batch.get('owner_id', 'Unknown')
        summary = batch.get('batch_summary', {})
        metadata = batch.get('metadata', {})
        
        print(f"\n{'='*60}")
        print(f"🎫 Batch: {token_id}")
        print(f"👤 Owner: {owner_id}")
        
        if metadata:
            print(f"📝 Title: {metadata.get('title', 'No title')}")
            if metadata.get('description'):
                print(f"   Description: {metadata['description']}")
        
        print(f"\n📊 Summary:")
        print(f"   Database: {summary.get('database_name', 'Unknown')}")
        print(f"   Tables: {', '.join(summary.get('table_names', []))}")
        print(f"   Transactions: {summary.get('tx_count', 0)}")
        print(f"   Timestamp: {datetime.fromtimestamp(summary.get('timestamp', 0)/1000)}")
        
        ops = summary.get('operation_counts', {})
        if ops:
            print(f"   Operations: {ops.get('inserts', 0)} inserts, "
                  f"{ops.get('updates', 0)} updates, {ops.get('deletes', 0)} deletes")
        
        print(f"   Merkle Root: {summary.get('merkle_root', '')[:32]}...")
        
        if detailed:
            print(f"\n💾 Storage:")
            print(f"   S3 Bucket: {summary.get('s3_bucket', 'Unknown')}")
            print(f"   S3 Key: {summary.get('s3_key', 'Unknown')}")
            print(f"   Size: {summary.get('size_bytes', 0):,} bytes")
        
        print(f"{'='*60}")
    
    async def display_batch_statistics(self, database: Optional[str] = None):
        """Display statistics about batches"""
        print(f"\n📈 ETRAP Batch Statistics")
        print(f"   Contract: {self.contract_id}")
        print(f"   Network: {self.network}")
        print("="*60)
        
        # Get global stats
        stats = await self.query_contract("get_batch_stats", {})
        if stats:
            print(f"\n🌍 Global Statistics:")
            print(f"   Total Batches: {stats.get('total_batches', 0)}")
            print(f"   Total Databases: {stats.get('total_databases', 0)}")
            
            databases = stats.get('databases', [])
            if databases:
                print(f"   Databases: {', '.join(databases[:5])}")
                if len(databases) > 5:
                    print(f"   ... and {len(databases) - 5} more")
        
        # Get database-specific stats if requested
        if database:
            db_result = await self.get_batches_by_database(database, limit=1)
            print(f"\n🗄️  Database '{database}' Statistics:")
            print(f"   Total Batches: {db_result.get('total_count', 0)}")
            
            if db_result.get('batches'):
                latest = db_result['batches'][0]
                latest_time = datetime.fromtimestamp(
                    latest['batch_summary']['timestamp']/1000
                )
                print(f"   Latest Batch: {latest_time}")
    
    async def interactive_search(self):
        """Interactive mode for searching batches"""
        while True:
            print("\n🔍 ETRAP Batch Search")
            print("1. Recent batches")
            print("2. Search by database")
            print("3. Search by time range")
            print("4. Search by table")
            print("5. Get batch details")
            print("6. View statistics")
            print("0. Exit")
            
            choice = input("\nSelect option: ").strip()
            
            if choice == "0":
                break
            elif choice == "1":
                limit = int(input("Number of batches (default 10): ").strip() or "10")
                batches = await self.get_recent_batches(limit)
                for batch in batches:
                    self.display_batch_info(batch)
                    
            elif choice == "2":
                database = input("Database name: ").strip()
                if database:
                    result = await self.get_batches_by_database(database)
                    print(f"\nFound {result['total_count']} batches")
                    for batch in result['batches']:
                        self.display_batch_info(batch)
                        
            elif choice == "3":
                days_back = int(input("Days back (default 7): ").strip() or "7")
                database = input("Database filter (optional): ").strip() or None
                
                end_time = datetime.now()
                start_time = end_time - timedelta(days=days_back)
                
                batches = await self.get_batches_by_time_range(
                    start_time, end_time, database
                )
                print(f"\nFound {len(batches)} batches")
                for batch in batches:
                    self.display_batch_info(batch)
                    
            elif choice == "4":
                table = input("Table name: ").strip()
                if table:
                    batches = await self.get_batches_by_table(table)
                    print(f"\nFound {len(batches)} batches")
                    for batch in batches:
                        self.display_batch_info(batch)
                        
            elif choice == "5":
                token_id = input("Batch token ID: ").strip()
                if token_id:
                    details = await self.get_batch_details(token_id)
                    if details:
                        # Create batch info structure
                        batch_info = {
                            "token_id": token_id,
                            "owner_id": details["token_info"]["owner_id"],
                            "metadata": details["token_info"].get("metadata", {}),
                            "batch_summary": details["batch_summary"]
                        }
                        self.display_batch_info(batch_info, detailed=True)
                        
                        # Offer to download S3 data
                        if input("\nDownload full batch data from S3? (y/n): ").lower() == 'y':
                            s3_data = self.get_s3_batch_data(
                                details["batch_summary"]["s3_bucket"],
                                details["batch_summary"]["s3_key"]
                            )
                            if s3_data and input("\nShow transaction count by operation? (y/n): ").lower() == 'y':
                                ops = {}
                                for tx in s3_data.get('transactions', []):
                                    op = tx['metadata']['operation_type']
                                    ops[op] = ops.get(op, 0) + 1
                                print("\nTransaction breakdown:")
                                for op, count in ops.items():
                                    print(f"   {op}: {count}")
                                    
            elif choice == "6":
                database = input("Database name (optional): ").strip() or None
                await self.display_batch_statistics(database)
            
            if choice != "0":
                input("\nPress Enter to continue...")


async def main():
    parser = argparse.ArgumentParser(
        description='ETRAP Generic Batch Validator - Query and validate batches without table-specific knowledge'
    )
    
    # Required arguments
    parser.add_argument('--contract', '-c', required=True,
                       help='NEAR contract ID (e.g., acme.testnet)')
    
    # Optional arguments
    parser.add_argument('--network', '-n', default='testnet',
                       choices=['testnet', 'mainnet', 'localnet'],
                       help='NEAR network (default: testnet)')
    
    parser.add_argument('--database', '-d',
                       help='Filter by database name')
    
    parser.add_argument('--recent', '-r', type=int,
                       help='Show N most recent batches')
    
    parser.add_argument('--days', type=int,
                       help='Show batches from last N days')
    
    parser.add_argument('--table', '-t',
                       help='Filter by table name')
    
    parser.add_argument('--batch-id', '-b',
                       help='Show details for specific batch ID')
    
    parser.add_argument('--stats', '-s', action='store_true',
                       help='Show batch statistics')
    
    parser.add_argument('--interactive', '-i', action='store_true',
                       help='Interactive search mode')
    
    parser.add_argument('--download-s3', action='store_true',
                       help='Download batch data from S3 (with --batch-id)')
    
    args = parser.parse_args()
    
    # Create validator instance
    validator = ETRAPGenericValidator(args.contract, args.network)
    
    print(f"🚀 ETRAP Generic Batch Validator")
    print(f"   Contract: {args.contract}")
    print(f"   Network: {args.network}")
    print("="*60)
    
    try:
        # Handle different modes
        if args.interactive:
            await validator.interactive_search()
            
        elif args.stats:
            await validator.display_batch_statistics(args.database)
            
        elif args.batch_id:
            # Get specific batch details
            details = await validator.get_batch_details(args.batch_id)
            if details:
                batch_info = {
                    "token_id": args.batch_id,
                    "owner_id": details["token_info"]["owner_id"],
                    "metadata": details["token_info"].get("metadata", {}),
                    "batch_summary": details["batch_summary"]
                }
                validator.display_batch_info(batch_info, detailed=True)
                
                if args.download_s3:
                    s3_data = validator.get_s3_batch_data(
                        details["batch_summary"]["s3_bucket"],
                        details["batch_summary"]["s3_key"]
                    )
                    if s3_data:
                        print(f"\n✅ Successfully downloaded batch data")
                        print(f"   Transactions: {len(s3_data.get('transactions', []))}")
                        print(f"   Merkle nodes: {len(s3_data.get('merkle_tree', {}).get('nodes', []))}")
                        
        elif args.recent:
            # Show recent batches
            batches = await validator.get_recent_batches(args.recent)
            print(f"\nFound {len(batches)} recent batches:")
            for batch in batches:
                validator.display_batch_info(batch)
                
        elif args.days:
            # Show batches from last N days
            end_time = datetime.now()
            start_time = end_time - timedelta(days=args.days)
            
            batches = await validator.get_batches_by_time_range(
                start_time, end_time, args.database
            )
            print(f"\nFound {len(batches)} batches from last {args.days} days:")
            for batch in batches:
                validator.display_batch_info(batch)
                
        elif args.table:
            # Show batches containing table
            batches = await validator.get_batches_by_table(args.table)
            print(f"\nFound {len(batches)} batches containing table '{args.table}':")
            for batch in batches:
                validator.display_batch_info(batch)
                
        elif args.database:
            # Show batches for database
            result = await validator.get_batches_by_database(args.database)
            print(f"\nFound {result['total_count']} batches for database '{args.database}':")
            for batch in result['batches']:
                validator.display_batch_info(batch)
                
        else:
            # Default: show recent batches
            batches = await validator.get_recent_batches(5)
            print(f"\nShowing 5 most recent batches (use --help for more options):")
            for batch in batches:
                validator.display_batch_info(batch)
                
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))