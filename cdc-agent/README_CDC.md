# ETRAP CDC Agent

This document provides the technical documentation for the ETRAP CDC Agent component.

## Overview

The ETRAP CDC Agent is the core component that captures database changes and creates immutable audit trails on the NEAR blockchain. It consumes Change Data Capture (CDC) events from PostgreSQL via Debezium and Redis, batches them intelligently, and creates blockchain-backed proofs.


### Setup and Installation
```bash
python3 -m venv venv
source venv/bin/activate  
pip install -r requirements.txt
```

## Architecture

### Data Flow

1. **PostgreSQL Database** → Changes occur in tables
2. **Debezium** → Captures changes as CDC events
3. **Redis Streams** → Events published to streams (pattern: `etrap.public.*`)
4. **CDC Agent** → Consumes events, creates batches
5. **S3 Storage** → Stores detailed batch data and Merkle trees
6. **NEAR Blockchain** → NFTs minted with Merkle roots

### Key Design Decisions

- **Hybrid Storage**: Detailed data in S3, only hashes on blockchain
- **Intelligent Batching**: Reduces blockchain transactions while maintaining granularity
- **Generic Design**: No table-specific code, works with any schema
- **Merkle Trees**: Enables efficient proof of individual transactions

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEAR_ACCOUNT` | NEAR account for minting NFTs | None (required) |
| `NEAR_ENV` | NEAR network (testnet/mainnet) | testnet |
| `ETRAP_RPC_ENDPOINT` | Custom NEAR RPC endpoint | testnet: https://test.rpc.fastnear.com, mainnet: https://rpc.mainnet.near.org |
| `REDIS_HOST` | Redis server hostname | localhost |
| `REDIS_PORT` | Redis server port | 6379 |
| `REDIS_PASSWORD` | Redis password | None (optional) |
| `ETRAP_S3_BUCKET` | S3 bucket for batch storage | etrap-demo |
| `ETRAP_ORG_ID` | Organization identifier | demo-org |
| `AWS_ACCESS_KEY_ID` | AWS access key for S3 | None (optional) |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key for S3 | None (optional) |
| `AWS_DEFAULT_REGION` | AWS region | us-west-2 |

Example:
```bash
export AWS_DEFAULT_REGION="us-west-2"
export AWS_ACCESS_KEY_ID="AK.."
export AWS_SECRET_ACCESS_KEY="OrH.."
export ETRAP_ORG_ID="acme"
export ETRAP_S3_BUCKET="etrap-acme"
export NEAR_ACCOUNT="acme.testnet"
export NEAR_ENV="testnet" 
```
### Batching Parameters

The agent uses intelligent batching with these configurable parameters:

```python
batch_size = 1000        # Maximum events per batch
batch_timeout = 60       # Read timeout in seconds
min_batch_size = 1       # Minimum events to create batch
force_batch_after = 300  # Force batch creation after 5 minutes
```

## Data Structures

### Batch Reference Metadata (S3)
 The `batch-data.json`file
  contains the complete batch metadata including batch info, detailed transaction records with their
  hashes and Merkle leaf positions, the full Merkle tree structure with proof paths, search indices
  organized by timestamp/operation/date, and compliance/verification data - essentially everything needed
   to cryptographically verify any individual transaction within that batch.
```json
{
  "batch_info": {
    "batch_id": "BATCH-2025-06-14-abc123",
    "created_at": 1749864039000,
    "organization_id": "demo-org",
    "database_name": "etrapdb",
    "etrap_agent_version": "1.0.0"
  },
  "transactions": [
    {
      "metadata": {
        "transaction_id": "BATCH-2025-06-14-abc123-0",
        "timestamp": 1749864039877,
        "operation_type": "INSERT",
        "database_name": "etrapdb",
        "table_affected": "financial_transactions",
        "change_data": {...}
      },
      "merkle_leaf": {
        "index": 0,
        "hash": "abc123...",
        "raw_data_hash": "def456..."
      }
    }
  ],
  "merkle_tree": {
    "algorithm": "sha256",
    "root": "merkle_root_hash",
    "height": 3,
    "nodes": [...],
    "proof_index": {...}
  },
  "indices": {
    "by_timestamp": {...},
    "by_operation": {...},
    "by_date": {...}
  }
}
```

### Additional Metadata Files (S3)
- `merkle-tree.json`: Contains the standalone Merkle tree structure with algorithm, root hash, all nodes
  with their levels and indices, and complete proof paths for cryptographic verification of individual
  transactions.

- `indices` files: Contain optimized lookup tables that map timestamps, operation types, and dates to their
   corresponding transaction IDs for fast searching and filtering within the batch.

The Merkle tree data exists in BOTH files:
  - `batch-data.json` contains the complete Merkle tree (embedded)
  - `merkle-tree.json` contains the same Merkle tree data (standalone)

>This redundancy means verification tools can use either file - the complete `batch-data.json` or just the
`merkle-tree.json` depending on their needs.


### NFT Metadata (NEAR)

```json
{
  "token_id": "BATCH-2025-06-14-abc123",
  "owner_id": "acme.testnet",
  "metadata": {
    "title": "ETRAP Batch BATCH-2025-06-14-abc123",
    "description": "Integrity certificate for 25 transactions",
    "reference": "https://s3.amazonaws.com/bucket/path"
  },
  "batch_summary": {
    "database_name": "etrapdb",
    "table_names": ["financial_transactions"],
    "timestamp": 1749864039877,
    "tx_count": 25,
    "merkle_root": "abc123...",
    "s3_bucket": "etrap-demo",
    "s3_key": "etrapdb/financial_transactions/BATCH-..."
  }
}
```

## CDC Event Processing

### Supported Operations

- `INSERT` (c) - New records
- `UPDATE` (u) - Modified records
- `DELETE` (d) - Removed records
- `SNAPSHOT` (r) - Initial data load

### Field Encoding

The agent handles base64-encoded numeric values from Debezium:

```python
def decode_field_value(self, value):
    # Detects base64 encoded values
    # Decodes to bytes
    # Interprets as big-endian integer for numeric values
    # Returns proper integer or string value
```

## Merkle Tree Implementation

### Tree Construction

1. Each transaction hash becomes a leaf node
2. Pairs of nodes are hashed together to create parent nodes
3. Process continues until single root hash remains
4. Full proof paths stored for each transaction

### Proof Verification

```python
# Start with leaf hash
current_hash = transaction_hash

# Apply each proof element
for sibling_hash in proof_path:
    if position == 'left':
        current_hash = hash(sibling_hash + current_hash)
    else:
        current_hash = hash(current_hash + sibling_hash)

# Verify against root
valid = (current_hash == merkle_root)
```

## S3 Storage Structure

```
bucket/
├── database_name/
│   └── table_name/
│       └── BATCH-YYYY-MM-DD-uuid/
│           ├── batch-data.json      # Complete batch data
│           ├── merkle-tree.json     # Merkle tree structure
│           └── indices/
│               ├── by_timestamp.json
│               ├── by_operation.json
│               └── by_date.json
```

Example:
- bucket: etrap-lunaris - always etrap-{organization_id}
- database: etrapdb
- table: financial_transactions
- BATCH-2025-06-26-17b79479-T1
```
$ aws s3 ls s3://etrap-lunaris/etrapdb/financial_transactions/BATCH-2025-06-26-17b79479-T1/ --recursive
2025-06-26 11:08:22    2189021 etrapdb/financial_transactions/BATCH-2025-06-26-17b79479-T1/batch-data.json
2025-06-26 11:08:22      34434 etrapdb/financial_transactions/BATCH-2025-06-26-17b79479-T1/indices/by_date.json
2025-06-26 11:08:22      34432 etrapdb/financial_transactions/BATCH-2025-06-26-17b79479-T1/indices/by_operation.json
2025-06-26 11:08:22      34637 etrapdb/financial_transactions/BATCH-2025-06-26-17b79479-T1/indices/by_timestamp.json
2025-06-26 11:08:22    1158479 etrapdb/financial_transactions/BATCH-2025-06-26-17b79479-T1/merkle-tree.json

```

## Error Handling

- **Redis Connection**: Automatic reconnection with backoff
- **NFT Minting**: Retry logic with exponential backoff
- **S3 Upload**: Transactional with rollback on failure
- **Batch Processing**: Failed batches don't block subsequent ones

## Performance Considerations

- **Batch Size**: Larger batches reduce NFT costs but increase latency
- **Timeout Settings**: Balance between responsiveness and efficiency
- **S3 Optimization**: Uses multipart uploads for large batches
- **Memory Usage**: Streaming processing for large transactions

## Monitoring

Key metrics to monitor:

- Total batches created
- Average batch size
- NFT minting success rate
- Processing latency
- Redis stream lag

## Security

- **No Private Keys**: Uses NEAR credentials from ~/.near-credentials/
- **S3 Encryption**: Supports SSE-S3 and SSE-KMS
- **Network Security**: TLS for all external connections
- **Access Control**: IAM policies for S3 access

## Troubleshooting

### Common Issues

1. **"No streams found"**
   - Check Debezium is running
   - Verify Redis connection
   - Ensure correct stream pattern

2. **"NFT minting failed"**
   - Check NEAR account balance
   - Verify credentials exist
   - Check network connectivity

3. **"S3 upload failed"**
   - Verify AWS credentials
   - Check bucket permissions
   - Ensure bucket exists

### Debug Mode

Set environment variable for verbose logging:
```bash
export ETRAP_DEBUG=true
```

## Development


### Code Structure

```
etrap_cdc_agent.py
├── ETRAPCDCAgent class
│   ├── __init__()              # Configuration
│   ├── consume_cdc_events()    # Main loop
│   ├── process_and_store_batch() # Batch processing
│   ├── create_merkle_tree()    # Proof generation
│   ├── mint_nft()              # Blockchain interaction
│   └── store_in_s3()           # Storage
```

## Integration

### With Debezium

Configure Debezium to publish to Redis:
```json
{
  "name": "etrap-connector",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "tasks.max": "1",
    "database.hostname": "postgres",
    "database.port": "5432",
    "database.user": "postgres",
    "database.password": "password",
    "database.dbname": "etrapdb",
    "redis.address": "redis://localhost:6379",
    "redis.key": "etrap"
  }
}
```

### With NEAR

Requires deployed ETRAP smart contract with these methods:
- `mint_batch(token_id, batch_summary, token_metadata)`
- `get_batch_summary(token_id)`
- `get_recent_batches(limit)`

## Maintenance

### Log Rotation

Configure logrotate for agent logs:
```
/var/log/etrap-cdc-agent.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
}
```

### Backup Strategy

- S3 versioning enabled for batch data
- Regular NEAR account key backups
- Redis persistence for stream recovery

## Version History

- v1.0.0 - Initial release with core CDC functionality
- v1.0.1 - Fixed base64 encoding for numeric values
- v1.0.2 - Added intelligent batching parameters

---

For more information, see the main [README](../README.md).


## Copyright

Copyright (c) 2025 Graziano Labs Corp. All rights reserved.
