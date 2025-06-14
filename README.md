# ETRAP CDC Agent

## Overview

The ETRAP CDC (Change Data Capture) Agent is the core component that monitors database changes in real-time and creates immutable audit trails on the NEAR blockchain. It acts as a bridge between your enterprise database and blockchain, ensuring every critical transaction is cryptographically secured and independently verifiable.

This agent is part of the ETRAP (Enterprise Transaction Recording and Audit Platform) system, designed to provide tamper-proof audit trails for regulatory compliance, dispute resolution, and data integrity verification.

## Architecture

```
PostgreSQL → Debezium → Redis Streams → CDC Agent → Batching → S3 Storage → NEAR Blockchain
                                            ↓
                                     Merkle Tree Creation
```

### Key Components

1. **Real-time Capture**: Monitors database change logs via Debezium/Redis
2. **Intelligent Batching**: Groups transactions for cost-effective blockchain anchoring
3. **Merkle Tree Generation**: Creates cryptographic proofs for each transaction
4. **Hybrid Storage**: Stores detailed data in S3, anchors proof on NEAR blockchain
5. **NFT Minting**: Creates NFT certificates for each batch on NEAR Protocol

## Features

- 🚀 **Real-time Processing**: Captures database changes as they happen
- 📦 **Smart Batching**: Configurable batch sizes and timeouts for optimal cost
- 🔐 **Cryptographic Security**: Merkle tree proofs for every transaction
- 💾 **Hybrid Architecture**: On-premise agent with cloud storage
- 🎫 **NFT Certificates**: Blockchain-backed proof of transaction batches
- 📊 **Multi-table Support**: Handles multiple tables with separate batches
- 🔄 **Automatic Retry**: Resilient NFT minting with retry logic
- 📈 **Performance Metrics**: Built-in statistics and monitoring

## Installation

### Prerequisites

- Python 3.7+
- PostgreSQL database with Debezium CDC enabled
- Redis server for streaming CDC events
- NEAR account for blockchain anchoring
- AWS S3 bucket for batch data storage

### Setup

```bash
# Clone the repository
git clone https://github.com/etrap/cdc-agent.git
cd cdc-agent

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Linux/Mac
# or
venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file or set these environment variables:

```bash
# S3 Configuration
ETRAP_S3_BUCKET=your-bucket-name
ETRAP_ORG_ID=your-organization-id
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_DEFAULT_REGION=us-east-1

# Redis Configuration (optional, defaults shown)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# NEAR Configuration (optional for blockchain-only mode)
NEAR_ACCOUNT_ID=your-org.testnet
NEAR_PRIVATE_KEY=your-private-key
NEAR_NETWORK=testnet
```

## Configuration

The CDC agent supports various configuration options:

```python
# In etrap_cdc_agent.py or via environment variables

# Batching Configuration
batch_size = 1000          # Maximum events per batch
batch_timeout = 60         # Read timeout in seconds  
min_batch_size = 1         # Minimum events to create batch
force_batch_after = 300    # Force batch creation after N seconds

# Redis Configuration
stream_pattern = "etrap.public.*"  # Pattern for Redis streams
consumer_group = "etrap-cdc-agent"
consumer_name = "agent-1"

# Retry Configuration
max_mint_retries = 3       # NFT minting retry attempts
```

## Usage

### Basic Operation

```bash
# Run the CDC agent
python etrap_cdc_agent.py
```

The agent will:
1. Connect to Redis and start consuming CDC events
2. Batch transactions intelligently based on configuration
3. Create Merkle trees for each batch
4. Store detailed data in S3
5. Mint NFTs on NEAR blockchain with merkle roots

### Sample Output

```
🚀 ETRAP CDC Agent Starting...
📡 PostgreSQL → Debezium → Redis → S3 → NEAR
------------------------------------------------------------
✅ Using S3 bucket: etrap-acme
✅ NEAR client initialized for acme.testnet on testnet
📋 Batching Configuration:
   Max batch size: 1000 events
   Min batch size: 1 events
   Read timeout: 60s
   Force batch after: 300s
   🔗 NEAR account: acme.testnet (testnet)
------------------------------------------------------------

📊 Table: public.financial_transactions
   Events: 6
   Batch ID: BATCH-2025-06-14-776e2080-T0
   Merkle Root: e32d4c0d37240788167a7ddd5ef7a415...
   🔗 Minting NFT (attempt 1/3)...
   ✅ NFT minted successfully!
      Transaction: 4ize64V9emANJaDk...
   ✅ Stored batch data in S3: etrap-acme/etrapdb/financial_transactions/BATCH-2025-06-14-776e2080-T0
   🎉 Complete: NFT minted and data stored in S3
```

## Data Flow

### 1. CDC Event Capture

Debezium captures database changes and publishes to Redis streams:
```
etrap.public.financial_transactions
etrap.public.audit_logs
etrap.public.inventory
```

### 2. Event Processing

The agent:
- Decodes base64-encoded field values
- Groups events by table
- Applies batching logic

### 3. Batch Creation

For each batch, the agent creates:
- Unique batch ID: `BATCH-YYYY-MM-DD-{uuid}`
- Transaction metadata with timestamps
- Complete Merkle tree with proofs
- Search indices for efficient lookup

### 4. Data Storage

#### S3 Structure
```
etrap-{organization}/
├── {database}/
│   ├── {table}/
│   │   ├── {batch-id}/
│   │   │   ├── batch-data.json      # Complete batch reference
│   │   │   ├── merkle-tree.json     # Merkle tree structure
│   │   │   └── indices/
│   │   │       ├── by-date.json
│   │   │       ├── by-operation.json
│   │   │       └── by-timestamp.json
```

#### NFT Metadata (on NEAR)
```json
{
  "title": "ETRAP Batch BATCH-2025-06-14-776e2080-T0",
  "description": "Integrity certificate for 6 transactions from table financial_transactions",
  "reference": "https://s3.amazonaws.com/etrap-acme/BATCH-2025-06-14-776e2080-T0/batch-data.json"
}
```

## Batching Strategy

The agent uses intelligent batching to balance cost and latency:

1. **Size-based**: Batch created when reaching `batch_size` limit
2. **Time-based**: Batch created after `batch_timeout` with pending events
3. **Force timeout**: Batch forced after `force_batch_after` seconds
4. **Minimum size**: Only creates batch if >= `min_batch_size` events

Example scenarios:
- High volume: Batches at 1000 events (size limit)
- Low volume: Batches every 5 minutes (force timeout)
- Burst traffic: Immediate batching when threshold met

## Data Structures

### Batch Reference Data (S3)

```json
{
  "batch_info": {
    "batch_id": "BATCH-2025-06-14-776e2080-T0",
    "created_at": 1749855196423,
    "organization_id": "acme",
    "database_name": "etrapdb",
    "etrap_agent_version": "1.0.0"
  },
  "transactions": [
    {
      "metadata": {
        "transaction_id": "BATCH-2025-06-14-776e2080-T0-0",
        "timestamp": 1749855135648,
        "operation_type": "INSERT",
        "database_name": "etrapdb",
        "table_affected": "financial_transactions",
        "change_data": {
          "account_id": "ACC500",
          "amount": "D0JA",  // Base64 encoded
          "type": "C"
        }
      },
      "merkle_leaf": {
        "index": 0,
        "hash": "3bca0b81b1b9045b..."
      }
    }
  ],
  "merkle_tree": {
    "root": "e32d4c0d37240788...",
    "proof_index": {
      "tx-0": {
        "proof_path": ["hash1", "hash2"],
        "sibling_positions": ["right", "left"]
      }
    }
  }
}
```

## Monitoring and Statistics

The agent provides real-time statistics:

```
📈 Statistics: 10 batches, 847 events (avg: 84.7 events/batch)
   NFTs: 10 minted, 0 failed (100.0% success rate)
```

Monitor these metrics:
- Total batches created
- Average batch size
- NFT minting success rate
- Empty timeouts (idle periods)
- Events per second

## Error Handling

### Automatic Retry

- NFT minting: Retries up to 3 times with exponential backoff
- S3 uploads: Built-in AWS SDK retry logic
- Redis connection: Automatic reconnection

### Failure Modes

1. **NFT minting fails**: Data still stored in S3, can retry later
2. **S3 upload fails**: Transaction held until successful
3. **Redis disconnection**: Resumes from last acknowledged message

## Security Considerations

### Data Privacy
- Sensitive data never leaves your infrastructure
- Only hashes and metadata on blockchain
- S3 data encrypted at rest
- Customer controls all access keys

### Blockchain Security
- Each organization has separate NEAR account
- Private keys never leave your infrastructure
- Smart contract enforces access controls
- Immutable once minted

## Performance Tuning

### High Volume Databases

```python
# Increase batch size for cost optimization
batch_size = 5000
batch_timeout = 30  # Reduce timeout
```

### Low Volume Databases

```python
# Smaller batches for faster verification
batch_size = 100
force_batch_after = 600  # 10 minutes
```

### Memory Optimization

```python
# For very large transactions
max_memory_buffer = 100  # MB
enable_compression = True
```

## Troubleshooting

### Common Issues

1. **"No streams found"**
   - Check Debezium is running
   - Verify Redis connection
   - Ensure correct stream pattern

2. **"NFT minting failed"**
   - Verify NEAR account has funds
   - Check private key is correct
   - Ensure contract is deployed

3. **"S3 upload failed"**
   - Verify AWS credentials
   - Check bucket exists and has permissions
   - Ensure region is correct

### Debug Mode

```bash
# Enable debug logging
export ETRAP_DEBUG=true
python etrap_cdc_agent.py
```

### Health Check

```bash
# Check agent status
curl http://localhost:8080/health

# Response
{
  "status": "healthy",
  "redis": "connected",
  "s3": "accessible",
  "near": "synced",
  "pending_events": 42
}
```

## Integration

### Docker Deployment

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY etrap_cdc_agent.py .
CMD ["python", "etrap_cdc_agent.py"]
```

```bash
docker run -d \
  --name etrap-cdc-agent \
  -e ETRAP_S3_BUCKET=my-bucket \
  -e NEAR_ACCOUNT_ID=myorg.near \
  -e REDIS_HOST=redis.internal \
  etrap/cdc-agent:latest
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: etrap-cdc-agent
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: cdc-agent
        image: etrap/cdc-agent:latest
        env:
        - name: ETRAP_S3_BUCKET
          value: my-bucket
        - name: NEAR_ACCOUNT_ID
          valueFrom:
            secretKeyRef:
              name: near-credentials
              key: account-id
```

### Monitoring Integration

```python
# Prometheus metrics endpoint
http://localhost:9090/metrics

# Metrics exposed:
etrap_batches_created_total
etrap_events_processed_total
etrap_nft_mints_total
etrap_nft_mint_failures_total
etrap_processing_duration_seconds
```

## Advanced Configuration

### Multi-Database Support

```python
# Process multiple databases
databases = {
    "production_db": {
        "stream_pattern": "etrap.public.*",
        "batch_size": 1000
    },
    "analytics_db": {
        "stream_pattern": "etrap.analytics.*",
        "batch_size": 5000
    }
}
```

### Custom Filtering

```python
# Only process specific tables
included_tables = ["financial_transactions", "audit_logs"]
excluded_tables = ["temp_*", "staging_*"]

# Only process certain operations
included_operations = ["INSERT", "UPDATE"]
```

### Compliance Rules

```python
# Apply compliance-specific rules
compliance_rules = {
    "SOX": {
        "min_batch_size": 1,  # No batching for SOX
        "force_immediate": True
    },
    "GDPR": {
        "exclude_columns": ["personal_data", "email"]
    }
}
```

## Maintenance

### Log Rotation

```bash
# Configure log rotation
/var/log/etrap/cdc-agent.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
}
```

### Backup Strategy

- S3 data: Enable versioning and cross-region replication
- Redis: Regular snapshots of consumer group offset
- Configuration: Version control all settings

### Upgrades

```bash
# Zero-downtime upgrade process
1. Deploy new version alongside old
2. Stop old version consumption
3. New version resumes from last offset
4. Remove old version
```

## License

Part of the ETRAP platform. See main repository for license details.

## Support

- Documentation: [etrap.io/docs](https://etrap.io/docs)
- Issues: [github.com/etrap/cdc-agent/issues](https://github.com/etrap/cdc-agent/issues)
- Email: support@etrap.io
- Slack: [etrap-community.slack.com](https://etrap-community.slack.com)