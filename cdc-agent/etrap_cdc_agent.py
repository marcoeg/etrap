#!/usr/bin/env python3
# etrap_cdc_agent.py - Complete agent with NFT minting and S3 metadata storage

import redis
import json
import base64
import hashlib
import time
import boto3
import uuid
import os
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Any, Optional

# NEAR imports - using near-api-py (pure Python, no Rust dependencies)
try:
    from near_api.account import Account
    from near_api.signer import Signer, KeyPair
    from near_api.providers import JsonProvider
    NEAR_AVAILABLE = True
except ImportError:
    NEAR_AVAILABLE = False
    print("⚠️  near-api-py not installed. Install with: pip install near-api-py")

class ETRAPCDCAgent:
    def __init__(self, 
                 redis_host='localhost', 
                 redis_port=6379, 
                 redis_password=None,
                 s3_bucket=None,
                 organization_id='demo-org',
                 aws_access_key_id=None,
                 aws_secret_access_key=None,
                 aws_region='us-west-2'):
        
        # Redis setup
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            password=redis_password,
            decode_responses=True
        )
        
        # S3 setup with explicit credentials
        if aws_access_key_id and aws_secret_access_key:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name=aws_region
            )
        else:
            # Falls back to environment variables or IAM role
            self.s3_client = boto3.client('s3', region_name=aws_region)
        
        self.s3_bucket = s3_bucket or f"etrap-{organization_id}"
        self.organization_id = organization_id
        self.aws_region = aws_region
        
        # NEAR configuration
        self.near_account = os.getenv('NEAR_ACCOUNT')
        self.near_network = os.getenv('NEAR_ENV', 'testnet')
        self.near_client = None
        self.near_provider = None
        self.max_mint_retries = 3
        self.mint_retry_delay = 2  # seconds
        
        # Enhanced Batching configuration
        self.batch_size = 1000              # Maximum events per batch
        self.batch_timeout = 60             # Timeout in seconds for reading new messages
        self.min_batch_size = 1             # Minimum events required to create a batch
        self.force_batch_after = 300        # Force batch creation after 5 minutes if events pending
        self.consumer_group = "etrap-agent"
        self.consumer_name = "agent-1"
        self.stream_pattern = "etrap.public.*"
        
        # State tracking for batching
        self.pending_events = []            # Events waiting to be batched
        self.last_batch_time = time.time()  # Track when last batch was created
        self.batch_stats = {                # Statistics for monitoring
            'total_batches': 0,
            'total_events': 0,
            'empty_timeouts': 0,
            'nfts_minted': 0,
            'nft_failures': 0
        }
        
        # Initialize S3 bucket if needed
        self.ensure_s3_bucket()
        
        # Initialize NEAR if configured
        if self.near_account and NEAR_AVAILABLE:
            self.init_near_client()
    
    def ensure_s3_bucket(self):
        """Create S3 bucket if it doesn't exist"""
        try:
            self.s3_client.head_bucket(Bucket=self.s3_bucket)
            print(f"✅ Using S3 bucket: {self.s3_bucket}")
        except:
            try:
                # Create bucket - handle region-specific requirements
                if self.aws_region == 'us-east-1':
                    self.s3_client.create_bucket(Bucket=self.s3_bucket)
                else:
                    self.s3_client.create_bucket(
                        Bucket=self.s3_bucket,
                        CreateBucketConfiguration={'LocationConstraint': self.aws_region}
                    )
                print(f"✅ Created S3 bucket: {self.s3_bucket}")
            except Exception as e:
                print(f"⚠️  S3 bucket error: {e}")
                print("   Running in local mode without S3")
                self.s3_client = None
    
    def init_near_client(self):
        """Initialize NEAR client using credentials from ~/.near-credentials/"""
        try:
            # Setup provider
            if self.near_network == 'mainnet':
                rpc_url = "https://rpc.mainnet.near.org"
            else:
                rpc_url = "https://rpc.testnet.near.org"
            
            self.near_provider = JsonProvider(rpc_url)
            
            # Load credentials from ~/.near-credentials/
            home = os.path.expanduser("~")
            key_path = os.path.join(home, '.near-credentials', self.near_network, f"{self.near_account}.json")
            
            if os.path.exists(key_path):
                with open(key_path, 'r') as f:
                    key_data = json.load(f)
                    private_key = key_data.get('private_key', key_data.get('secret_key'))
                
                # Create KeyPair and Signer
                key_pair = KeyPair(private_key)
                signer = Signer(self.near_account, key_pair)
                self.near_client = Account(self.near_provider, signer, self.near_account)
                
                print(f"✅ NEAR client initialized for {self.near_account} on {self.near_network}")
            else:
                print(f"⚠️  NEAR credentials not found at {key_path}")
                self.near_client = None
                
        except Exception as e:
            print(f"⚠️  NEAR client initialization failed: {e}")
            self.near_client = None
    
    def setup_consumer_groups(self):
        """Create consumer groups for all matching streams"""
        streams = self.redis_client.keys(self.stream_pattern)
        for stream in streams:
            try:
                self.redis_client.xgroup_create(stream, self.consumer_group, id='0')
                print(f"Created consumer group for {stream}")
            except redis.ResponseError as e:
                if "BUSYGROUP" in str(e):
                    pass  # Group already exists
                else:
                    raise
    
    def decode_field_value(self, value):
        """Decode potentially encoded field values"""
        if isinstance(value, str):
            # Check if it looks like base64
            if value and value[-1] == '=' and all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=' for c in value):
                try:
                    decoded = base64.b64decode(value)
                    
                    # Check if this could be a numeric value (1-8 bytes)
                    if 1 <= len(decoded) <= 8:
                        # Try to interpret as big-endian integer (cents)
                        try:
                            int_value = int.from_bytes(decoded, byteorder='big')
                            # Check if it's in a reasonable range for cents
                            if 0 < int_value < 10**12:  # Up to 10 billion dollars
                                # Return the raw integer - let the caller decide if it's cents
                                return int_value
                        except:
                            pass
                    
                    # If not numeric, try to decode as string
                    try:
                        # First try UTF-8
                        decoded_str = decoded.decode('utf-8')
                        return decoded_str
                    except UnicodeDecodeError:
                        # Fall back to latin-1 which accepts all byte values
                        try:
                            decoded_str = decoded.decode('latin-1')
                            # Only return if it contains mostly printable characters
                            if sum(c.isprintable() for c in decoded_str) > len(decoded_str) * 0.8:
                                return decoded_str
                        except:
                            pass
                    
                    # If all else fails, return the original base64 value
                    return value
                    
                except Exception:
                    # If base64 decode fails, return original
                    pass
        
        return value
    
    def decode_record(self, record):
        """Recursively decode all fields in a record"""
        if isinstance(record, dict):
            return {k: self.decode_record(v) for k, v in record.items()}
        elif isinstance(record, list):
            return [self.decode_record(item) for item in record]
        else:
            return self.decode_field_value(record)
    
    def consume_cdc_events(self):
        """CDC event consumer with intelligent batching"""
        self.setup_consumer_groups()
        
        print(f"📋 Batching Configuration:")
        print(f"   Max batch size: {self.batch_size} events")
        print(f"   Min batch size: {self.min_batch_size} events")
        print(f"   Read timeout: {self.batch_timeout}s")
        print(f"   Force batch after: {self.force_batch_after}s")
        if self.near_client:
            print(f"   🔗 NEAR account: {self.near_account} ({self.near_network})")
        else:
            print(f"   ⚠️  NEAR minting disabled (no account configured)")
        print("-" * 60)
        
        while True:
            try:
                streams = self.redis_client.keys(self.stream_pattern)
                if not streams:
                    print("No streams found, waiting...")
                    time.sleep(5)
                    continue
                
                # Calculate dynamic timeout based on pending events
                time_since_last_batch = time.time() - self.last_batch_time
                
                # If we have pending events, calculate remaining time until force
                if self.pending_events:
                    remaining_force_time = max(0, self.force_batch_after - time_since_last_batch)
                    timeout_ms = min(self.batch_timeout * 1000, remaining_force_time * 1000)
                else:
                    # No pending events, use full timeout
                    timeout_ms = self.batch_timeout * 1000
                
                # Prepare streams for reading
                stream_dict = {stream: '>' for stream in streams}
                
                # Read new messages (up to remaining batch capacity)
                remaining_capacity = self.batch_size - len(self.pending_events)
                
                messages = self.redis_client.xreadgroup(
                    self.consumer_group,
                    self.consumer_name,
                    stream_dict,
                    count=remaining_capacity,
                    block=int(timeout_ms)
                )
                
                # Process new messages
                new_events_count = 0
                if messages:
                    for stream, stream_messages in messages:
                        for msg_id, data in stream_messages:
                            if data:
                                event = self.parse_generic_cdc_event(stream, msg_id, data)
                                if event:
                                    self.pending_events.append(event)
                                    new_events_count += 1
                                    # Acknowledge message
                                    self.redis_client.xack(stream, self.consumer_group, msg_id)
                
                # Batching decision logic
                should_process = False
                reason = ""
                
                if len(self.pending_events) >= self.batch_size:
                    # Batch is full
                    should_process = True
                    reason = "Batch size reached"
                    
                elif len(self.pending_events) >= self.min_batch_size:
                    # We have minimum events, check other conditions
                    
                    if not messages:
                        # Timeout occurred with pending events
                        should_process = True
                        reason = f"Timeout reached with {len(self.pending_events)} events"
                        
                    elif time_since_last_batch >= self.force_batch_after:
                        # Force timeout reached
                        should_process = True
                        reason = f"Force timeout ({self.force_batch_after}s) reached"
                
                # Process batch if conditions are met
                if should_process and self.pending_events:
                    print(f"\n🔄 Batch trigger: {reason}")
                    print(f"   New events in this read: {new_events_count}")
                    print(f"   Total pending events: {len(self.pending_events)}")
                    print(f"   Time since last batch: {time_since_last_batch:.1f}s")
                    
                    # Process the batch (synchronous now)
                    self.process_and_store_batch(self.pending_events)
                    
                    # Update statistics
                    self.batch_stats['total_batches'] += 1
                    self.batch_stats['total_events'] += len(self.pending_events)
                    
                    # Reset state
                    self.pending_events = []
                    self.last_batch_time = time.time()
                    
                else:
                    # No batch created
                    if not messages and not self.pending_events:
                        # True idle state - no messages and no pending events
                        self.batch_stats['empty_timeouts'] += 1
                        print(f"⏳ {datetime.now().strftime('%H:%M:%S')} - No activity "
                              f"(idle timeouts: {self.batch_stats['empty_timeouts']})")
                        
                    elif self.pending_events:
                        # We have pending events but not enough to batch yet
                        events_needed = self.min_batch_size - len(self.pending_events)
                        if events_needed > 0:
                            print(f"📊 {datetime.now().strftime('%H:%M:%S')} - "
                                  f"Pending: {len(self.pending_events)} events "
                                  f"(waiting for {events_needed} more)")
                        else:
                            print(f"📊 {datetime.now().strftime('%H:%M:%S')} - "
                                  f"Pending: {len(self.pending_events)} events "
                                  f"(ready to batch, waiting for timeout)")
                        
                    # Show periodic statistics
                    if self.batch_stats['total_batches'] > 0 and \
                       self.batch_stats['total_batches'] % 10 == 0:
                        avg_batch_size = self.batch_stats['total_events'] / self.batch_stats['total_batches']
                        nft_success_rate = (self.batch_stats['nfts_minted'] / 
                                          (self.batch_stats['nfts_minted'] + self.batch_stats['nft_failures']) * 100 
                                          if (self.batch_stats['nfts_minted'] + self.batch_stats['nft_failures']) > 0 else 0)
                        print(f"\n📈 Statistics: {self.batch_stats['total_batches']} batches, "
                              f"{self.batch_stats['total_events']} events "
                              f"(avg: {avg_batch_size:.1f} events/batch)")
                        if self.near_client:
                            print(f"   NFTs: {self.batch_stats['nfts_minted']} minted, "
                                  f"{self.batch_stats['nft_failures']} failed "
                                  f"({nft_success_rate:.1f}% success rate)")
                        
            except Exception as e:
                print(f"❌ Error consuming events: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(5)
    
    def parse_generic_cdc_event(self, stream, msg_id, data):
        """Parse CDC event without assuming table structure"""
        try:
            # Handle empty or missing value data
            value_str = data.get('value', '{}')
            if not value_str or value_str.strip() == '':
                value_str = '{}'
            value_data = json.loads(value_str)
            
            # Handle empty or missing key data  
            key_str = data.get('key', '{}') if 'key' in data else '{}'
            if not key_str or key_str.strip() == '':
                key_str = '{}'
            key_data = json.loads(key_str)
            
            operation = value_data.get('op')
            operation_map = {'c': 'INSERT', 'u': 'UPDATE', 'd': 'DELETE', 'r': 'SNAPSHOT'}
            mapped_operation = operation_map.get(operation, operation)
            
            before_data = self.decode_record(value_data.get('before'))
            after_data = self.decode_record(value_data.get('after'))
            
            # Validate DELETE events have proper before data
            if mapped_operation == 'DELETE' and not before_data:
                print(f"⚠️  Warning: DELETE event missing 'before' data - stream: {stream}, msg_id: {msg_id}")
                print(f"   Raw value_data: {value_data}")
                # Return None to skip this malformed DELETE event
                return None
            
            source = value_data.get('source', {})
            
            return {
                'stream': stream,
                'message_id': msg_id,
                'operation': mapped_operation,
                'key': key_data,
                'before': before_data,
                'after': after_data,
                'source': source,
                'timestamp': source.get('ts_ms', int(time.time() * 1000))
            }
        except Exception as e:
            print(f"Error parsing event: {e}")
            return None
    
    def process_and_store_batch(self, batch: List[Dict[str, Any]]):
        """Process batch, mint NFTs, then store in S3"""
        base_batch_id = f"BATCH-{datetime.now().strftime('%Y-%m-%d')}-{uuid.uuid4().hex[:8]}"
        
        print(f"\n{'='*60}")
        print(f"Processing batch")
        print(f"Events: {len(batch)}")
        print(f"{'='*60}")
        
        # Group by table
        events_by_table = defaultdict(list)
        for event in batch:
            table_key = f"{event['source'].get('schema', 'public')}.{event['source'].get('table', 'unknown')}"
            events_by_table[table_key].append(event)
        
        # Process each table's batch
        table_index = 0
        for table_key, events in events_by_table.items():
            # Create unique batch ID for each table
            batch_id = f"{base_batch_id}-T{table_index}" if len(events_by_table) > 1 else base_batch_id
            table_index += 1
            schema, table = table_key.split('.')
            database = events[0]['source'].get('db', 'unknown')
            
            # Create batch metadata according to ETRAP design
            batch_data = self.create_batch_reference_data(
                batch_id, database, schema, table, events
            )
            
            # Print summary
            print(f"\n📊 Table: {table_key}")
            print(f"   Events: {len(events)}")
            print(f"   Batch ID: {batch_id}")
            print(f"   Merkle Root: {batch_data['merkle_tree']['root'][:32]}...")
            
            # Prepare NFT metadata
            nft_success = False
            blockchain_data = None
            
            if self.near_client:
                # Convert to contract format
                batch_summary = self.create_batch_summary_for_contract(batch_data, database, table)
                token_metadata = self.create_token_metadata_for_contract(batch_id, database, table, len(events))
                
                # Mint NFT with retry
                blockchain_data = self.mint_nft_with_retry(
                    token_id=batch_id,
                    batch_summary=batch_summary,
                    token_metadata=token_metadata,
                    table=table
                )
                
                if blockchain_data and blockchain_data['success']:
                    nft_success = True
                    self.batch_stats['nfts_minted'] += 1
                    print(f"   ✅ NFT minted successfully!")
                    print(f"      Transaction: {blockchain_data['tx_hash'][:16]}...")
                    
                    # Update batch data with blockchain info
                    batch_data['verification']['anchoring_data'] = {
                        'block_height': blockchain_data['block_height'],
                        'tx_hash': blockchain_data['tx_hash'],
                        'gas_used': blockchain_data['gas_used'],
                        'etrap_fee': blockchain_data.get('etrap_fee', '0')
                    }
                else:
                    self.batch_stats['nft_failures'] += 1
                    print(f"   ❌ NFT minting failed - data will be stored in S3 only")
            else:
                print(f"   ℹ️  NEAR minting disabled - storing in S3 only")
            
            # Store in S3 (whether NFT minting succeeded or not)
            if self.s3_client:
                s3_success = self.store_batch_in_s3(database, batch_id, table, batch_data)
                if s3_success and nft_success:
                    print(f"   🎉 Complete: NFT minted and data stored in S3")
                elif s3_success:
                    print(f"   ✅ Data stored in S3 (can retry NFT minting later)")
            else:
                print(f"   ⚠️  No S3 storage available")
    
    def create_batch_summary_for_contract(self, batch_data: Dict, database: str, table: str) -> Dict:
        """Create BatchSummary matching the smart contract structure"""
        # Calculate operation counts
        ops_summary = {'inserts': 0, 'updates': 0, 'deletes': 0}
        for tx in batch_data['transactions']:
            op = tx['metadata']['operation_type']
            if op == 'INSERT':
                ops_summary['inserts'] += 1
            elif op == 'UPDATE':
                ops_summary['updates'] += 1
            elif op == 'DELETE':
                ops_summary['deletes'] += 1
        
        # Get timestamp range
        timestamps = [tx['metadata']['timestamp'] for tx in batch_data['transactions']]
        
        return {
            'database_name': database,
            'table_names': [table],  # Single table per batch in current implementation
            'timestamp': min(timestamps),  # Use earliest timestamp
            'tx_count': len(batch_data['transactions']),
            'merkle_root': batch_data['merkle_tree']['root'],
            's3_bucket': self.s3_bucket,
            's3_key': f"{database}/{table}/{batch_data['batch_info']['batch_id']}/",
            'size_bytes': len(json.dumps(batch_data).encode('utf-8')),  # Approximate size
            'operation_counts': ops_summary
        }
    
    def create_token_metadata_for_contract(self, batch_id: str, database: str, table: str, event_count: int) -> Dict:
        """Create TokenMetadata for the NFT"""
        return {
            'title': f"ETRAP Batch {batch_id}",
            'description': f"Integrity certificate for {event_count} transactions from table {table}",
            'media': None,
            'media_hash': None,
            'copies': 1,
            'issued_at': str(int(time.time() * 1000)),
            'expires_at': None,
            'starts_at': None,
            'updated_at': None,
            'extra': None,
            'reference': f"https://s3.amazonaws.com/{self.s3_bucket}/{database}/{table}/{batch_id}/batch-data.json",
            'reference_hash': None
        }
    
    def mint_nft_with_retry(self, token_id: str, batch_summary: Dict, 
                           token_metadata: Dict, table: str) -> Optional[Dict]:
        """Mint NFT with retry logic"""
        for attempt in range(self.max_mint_retries):
            try:
                print(f"   🔗 Minting NFT (attempt {attempt + 1}/{self.max_mint_retries})...")
                
                # Call the contract (0.5 NEAR deposit)
                result = self.near_client.function_call(
                    self.near_account,  # contract_id (same as account for your setup)
                    "mint_batch",
                    {
                        "token_id": token_id,
                        "receiver_id": self.near_account,
                        "token_metadata": token_metadata,
                        "batch_summary": batch_summary
                    },
                    gas=100000000000000,  # 100 TGas
                    amount=500000000000000000000000  # 0.5 NEAR
                )
                
                # Check if transaction was successful
                if 'error' not in result:
                    # Extract transaction details
                    tx_hash = result.get('transaction', {}).get('hash', '')
                    tx_outcome = result.get('transaction_outcome', {})
                    
                    # Look for fee info in logs
                    logs = tx_outcome.get('outcome', {}).get('logs', [])
                    etrap_fee = "0"
                    for log in logs:
                        if "etrap_fee" in log:
                            # Try to extract fee from log
                            try:
                                import re
                                fee_match = re.search(r'"etrap_fee":"(\d+)"', log)
                                if fee_match:
                                    etrap_fee = fee_match.group(1)
                            except:
                                pass
                    
                    return {
                        'success': True,
                        'tx_hash': tx_hash,
                        'block_height': str(tx_outcome.get('block_hash', '')),
                        'gas_used': str(tx_outcome.get('outcome', {}).get('gas_burnt', 0)),
                        'etrap_fee': etrap_fee,
                        'logs': logs
                    }
                else:
                    error_msg = result.get('error', 'Unknown error')
                    raise Exception(f"Transaction failed: {error_msg}")
                    
            except Exception as e:
                print(f"      ⚠️  Attempt {attempt + 1} failed: {e}")
                if attempt < self.max_mint_retries - 1:
                    time.sleep(self.mint_retry_delay * (2 ** attempt))
                else:
                    print(f"      ❌ NFT minting failed after {self.max_mint_retries} attempts")
                    return {'success': False, 'error': str(e)}
        
        return None
    
    def create_batch_reference_data(self, batch_id: str, database: str, schema: str, 
                                    table: str, events: List[Dict]) -> Dict:
        """Create complete batch reference data as per ETRAP design"""
        # Process transactions
        transactions = []
        transaction_hashes = []
        
        for idx, event in enumerate(events):
            # Create transaction metadata
            tx_data = {
                'transaction_id': f"{batch_id}-{idx}",
                'timestamp': event['timestamp'],
                'operation_type': event['operation'],
                'database_name': database,
                'table_affected': table,
                'rows_affected': {
                    'inserted': 1 if event['operation'] == 'INSERT' else 0,
                    'updated': 1 if event['operation'] == 'UPDATE' else 0,
                    'deleted': 1 if event['operation'] == 'DELETE' else 0
                },
                'hash': None,  # Will be set below
                'user_id': event['source'].get('user', 'system'),
                'lsn': event['source'].get('lsn'),
                'transaction_db_id': event['source'].get('txId')
                # Note: change_data removed for privacy compliance
            }
            
            # Create deterministic hash of the transaction
            # For INSERT/UPDATE, hash the 'after' data; for DELETE, hash the 'before' data
            if event['operation'] in ['INSERT', 'UPDATE'] and event['after']:
                # Normalize the data to match database format before hashing
                # This is necessary because Debezium converts timestamps to epoch format
                normalized_data = event['after'].copy()
                
                # Convert epoch timestamps back to ISO format for any field ending in '_at'
                for field, value in normalized_data.items():
                    if field.endswith('_at'):
                        # Check if it's already in ISO format (string)
                        if isinstance(value, str):
                            # Already in ISO format, no conversion needed
                            continue
                        # Check if it's an epoch timestamp that needs conversion
                        elif isinstance(value, (int, float)) and value > 1000000000000:
                            # Convert epoch microseconds or milliseconds to ISO format
                            if value > 1000000000000000:  # Microseconds (16+ digits)
                                dt = datetime.fromtimestamp(value / 1000000)
                            else:  # Milliseconds (13 digits)
                                dt = datetime.fromtimestamp(value / 1000)
                            # Format to match PostgreSQL timestamp format
                            iso_str = dt.strftime('%Y-%m-%dT%H:%M:%S.%f')
                            # Remove trailing zeros but keep at least milliseconds
                            iso_str = iso_str.rstrip('0').rstrip('.')
                            if '.' not in iso_str:
                                iso_str += '.000'
                            normalized_data[field] = iso_str
                
                tx_data_to_hash = json.dumps(normalized_data, sort_keys=True, separators=(',', ':'))
            elif event['operation'] == 'DELETE' and event['before']:
                # Normalize the data for DELETE operations too
                normalized_data = event['before'].copy()
                
                # Convert epoch timestamps back to ISO format
                for field, value in normalized_data.items():
                    if field.endswith('_at'):
                        # Check if it's already in ISO format (string)
                        if isinstance(value, str):
                            continue
                        # Check if it's an epoch timestamp
                        elif isinstance(value, (int, float)) and value > 1000000000000:
                            if value > 1000000000000000:  # Microseconds
                                dt = datetime.fromtimestamp(value / 1000000)
                            else:  # Milliseconds
                                dt = datetime.fromtimestamp(value / 1000)
                            iso_str = dt.strftime('%Y-%m-%dT%H:%M:%S.%f')
                            iso_str = iso_str.rstrip('0').rstrip('.')
                            if '.' not in iso_str:
                                iso_str += '.000'
                            normalized_data[field] = iso_str
                
                tx_data_to_hash = json.dumps(normalized_data, sort_keys=True, separators=(',', ':'))
            else:
                # Fallback to full event structure
                tx_data_to_hash = json.dumps({
                    'operation': event['operation'],
                    'key': event['key'],
                    'before': event['before'],
                    'after': event['after']
                }, sort_keys=True, separators=(',', ':'))
            
            tx_hash = hashlib.sha256(tx_data_to_hash.encode()).hexdigest()
            
            # DEBUG: Show what we're hashing for ACC999
            # if normalized_data.get('account_id') == 'ACC999':
            #     print(f"\n🔍 DEBUG - ACC999 Transaction:")
            #     print(f"   Normalized data: {json.dumps(normalized_data, indent=2)}")
            #     print(f"   JSON for hash: {tx_data_to_hash}")
            #     print(f"   Computed hash: {tx_hash}")
            
            tx_data['hash'] = tx_hash
            transaction_hashes.append(tx_hash)
            
            # Create detailed transaction record
            detailed_record = {
                'metadata': tx_data,
                'merkle_leaf': {
                    'index': idx,
                    'hash': tx_hash,
                    'raw_data_hash': hashlib.sha256(str(event).encode()).hexdigest()
                },
                'data_location': {
                    'encrypted': False,
                    'storage_path': f"{database}/{table}/{batch_id}/transactions/tx-{idx}.json",
                    'retention_expires': None
                }
            }
            
            transactions.append(detailed_record)
        
        # Build Merkle tree
        merkle_tree_data = self.build_merkle_tree_with_proofs(transaction_hashes)
        
        # Create indices for efficient lookup
        indices = {
            'by_timestamp': defaultdict(list),
            'by_operation': defaultdict(list),
            'by_date': defaultdict(list)
        }
        
        for tx in transactions:
            ts = tx['metadata']['timestamp']
            date = datetime.fromtimestamp(ts/1000).strftime('%Y-%m-%d')
            tx_id = tx['metadata']['transaction_id']
            
            indices['by_timestamp'][str(ts)].append(tx_id)
            indices['by_operation'][tx['metadata']['operation_type']].append(tx_id)
            indices['by_date'][date].append(tx_id)
        
        # Convert defaultdicts to regular dicts for JSON serialization
        indices = {k: dict(v) for k, v in indices.items()}
        
        # Create complete batch reference data
        batch_reference_data = {
            'batch_info': {
                'batch_id': batch_id,
                'created_at': int(time.time() * 1000),
                'organization_id': self.organization_id,
                'database_name': database,
                'etrap_agent_version': '1.0.0'
            },
            'transactions': transactions,
            'merkle_tree': merkle_tree_data,
            'indices': indices,
            'compliance': {
                'rules_applied': ['SOX', 'GDPR'],  # Example rules
                'data_classifications': ['financial'],
                'retention_policy': 'indefinite',
                'compliance_checks': []
            },
            'verification': {
                'batch_signature': hashlib.sha256(
                    (batch_id + merkle_tree_data['root']).encode()
                ).hexdigest(),
                'signing_algorithm': 'sha256',
                'signer_public_key': 'etrap-agent-key',
                'attestations': [],
                'anchoring_data': {  # Will be updated after NFT minting
                    'block_height': 0,
                    'tx_hash': '',
                    'gas_used': '0',
                    'etrap_fee': '0'
                }
            }
        }
        
        return batch_reference_data
    
    def build_merkle_tree_with_proofs(self, leaf_hashes: List[str]) -> Dict:
        """Build complete Merkle tree with all nodes and proofs"""
        if not leaf_hashes:
            return None
        
        # Pad to next power of 2 for consistent tree structure
        import math
        original_count = len(leaf_hashes)
        next_power = 2 ** math.ceil(math.log2(len(leaf_hashes))) if len(leaf_hashes) > 1 else 1
        
        # Pad with deterministic padding hashes to reach next power of 2
        padded_hashes = leaf_hashes[:]
        padding_base = leaf_hashes[-1] if leaf_hashes else "0" * 64
        while len(padded_hashes) < next_power:
            # Create unique padding hash by appending padding index
            padding_hash = hashlib.sha256(f"{padding_base}-pad-{len(padded_hashes)}".encode()).hexdigest()
            padded_hashes.append(padding_hash)
        
        # Initialize tree structure
        nodes = []
        proof_index = {}
        
        # Create leaf nodes for padded hashes
        current_level = []
        for idx, leaf_hash in enumerate(padded_hashes):
            node = {
                'index': len(nodes),
                'hash': leaf_hash,
                'level': 0,
                'is_original': idx < original_count  # Track original vs padded
            }
            nodes.append(node)
            current_level.append(node)
        
        # Initialize proof paths only for original leaves
        for idx in range(original_count):
            tx_id = f"tx-{idx}"
            proof_index[tx_id] = {
                'leaf_index': idx,
                'proof_path': [],
                'sibling_positions': []
            }
        
        # Build tree levels
        level = 1
        tree_nodes = [current_level]
        
        while len(current_level) > 1:
            next_level = []
            
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1]  # Now guaranteed to exist due to padding
                
                # Create parent node
                parent_hash = hashlib.sha256(
                    (left['hash'] + right['hash']).encode()
                ).hexdigest()
                
                parent = {
                    'index': len(nodes),
                    'hash': parent_hash,
                    'level': level,
                    'left_child': left['index'],
                    'right_child': right['index']
                }
                
                nodes.append(parent)
                next_level.append(parent)
            
            tree_nodes.append(next_level)
            current_level = next_level
            level += 1
        
        # Build proof paths for original transactions only
        for tx_idx in range(original_count):
            proof_path = []
            sibling_positions = []
            
            current_idx = tx_idx
            for level_nodes in tree_nodes[:-1]:  # Exclude root level
                # Find sibling
                if current_idx % 2 == 0:  # Even index, sibling is on right
                    sibling_idx = current_idx + 1
                    sibling_pos = 'right'
                else:  # Odd index, sibling is on left
                    sibling_idx = current_idx - 1
                    sibling_pos = 'left'
                
                # Sibling is guaranteed to exist due to padding
                proof_path.append(level_nodes[sibling_idx]['hash'])
                sibling_positions.append(sibling_pos)
                
                current_idx = current_idx // 2
            
            tx_id = f"tx-{tx_idx}"
            proof_index[tx_id]['proof_path'] = proof_path
            proof_index[tx_id]['sibling_positions'] = sibling_positions
        
        return {
            'algorithm': 'sha256',
            'root': nodes[-1]['hash'] if nodes else '',
            'height': level,
            'nodes': nodes,
            'proof_index': proof_index,
            'original_count': original_count,
            'padded_count': len(padded_hashes)
        }
    
    def store_batch_in_s3(self, database: str, batch_id: str, table: str, batch_data: Dict) -> bool:
        """Store batch data in S3 according to ETRAP structure"""
        base_path = f"{database}/{table}/{batch_id}"
        
        try:
            # Store complete batch data
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=f"{base_path}/batch-data.json",
                Body=json.dumps(batch_data, indent=2),
                ContentType='application/json'
            )
            
            # Store merkle tree separately for quick access
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=f"{base_path}/merkle-tree.json",
                Body=json.dumps(batch_data['merkle_tree'], indent=2),
                ContentType='application/json'
            )
            
            # Store indices
            for index_name, index_data in batch_data['indices'].items():
                self.s3_client.put_object(
                    Bucket=self.s3_bucket,
                    Key=f"{base_path}/indices/{index_name}.json",
                    Body=json.dumps(index_data, indent=2),
                    ContentType='application/json'
                )
            
            print(f"   ✅ Stored batch data in S3: {self.s3_bucket}/{base_path}")
            return True
            
        except Exception as e:
            print(f"   ⚠️  S3 storage error: {e}")
            return False


if __name__ == "__main__":
    print("🚀 ETRAP CDC Agent Starting...")
    print("📡 PostgreSQL → Debezium → Redis → S3 → NEAR")
    print("-" * 60)
    
    # Check for required environment variables
    if not os.getenv('NEAR_ACCOUNT'):
        print("⚠️  Warning: NEAR_ACCOUNT not set. NFT minting will be disabled.")
        print("   To enable NFT minting, set NEAR_ACCOUNT environment variable")
    
    # Configure with your settings
    agent = ETRAPCDCAgent(
        redis_host=os.getenv('REDIS_HOST', 'localhost'),
        redis_port=int(os.getenv('REDIS_PORT', '6379')),
        redis_password=os.getenv('REDIS_PASSWORD'),
        s3_bucket=os.getenv('ETRAP_S3_BUCKET', 'etrap-demo'),
        organization_id=os.getenv('ETRAP_ORG_ID', 'demo-org'),
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        aws_region=os.getenv('AWS_DEFAULT_REGION', 'us-west-2')
    )
    
    try:
        agent.consume_cdc_events()
    except KeyboardInterrupt:
        print("\n\n⏹️  Shutting down ETRAP CDC Agent...")
        print(f"   Total batches processed: {agent.batch_stats['total_batches']}")
        print(f"   Total events processed: {agent.batch_stats['total_events']}")
        if agent.near_client:
            print(f"   NFTs minted: {agent.batch_stats['nfts_minted']}")
            print(f"   NFT failures: {agent.batch_stats['nft_failures']}")