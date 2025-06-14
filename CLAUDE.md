# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Setup and Installation
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Linux/Mac
# or
venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt
```

### Running the CDC Agent
```bash
# Run the main CDC agent
python etrap_cdc_agent.py

# Environment variables needed:
# ETRAP_S3_BUCKET - S3 bucket name for storing batch data
# ETRAP_ORG_ID - Organization identifier
# AWS_ACCESS_KEY_ID - AWS credentials
# AWS_SECRET_ACCESS_KEY - AWS credentials
# AWS_DEFAULT_REGION - AWS region (default: us-east-1)
```

### Transaction Validation

#### Table-Specific Validation
```bash
# Validate a transaction against an NFT batch (for financial_transactions table)
python validate_transaction.py --token-id <NFT_TOKEN_ID> --account-id <ACCOUNT> --amount <AMOUNT> --type <C/D/T>

# Examples:
python validate_transaction.py --token-id BATCH-2025-06-13-04226f18-T1 --account-id ACC500 --amount 10000 --type C
python validate_transaction.py --token-id BATCH-2025-06-13-04226f18-T0 --table audit_logs --operation INSERT
```

#### Generic Batch Validation
```bash
# Query and validate batches without table-specific knowledge
python validate_batch.py --contract <CONTRACT_ID> [options]

# Show recent batches
python validate_batch.py --contract acme.testnet --recent 10

# Search by database
python validate_batch.py --contract acme.testnet --database etrapdb

# Search by time range (last 7 days)
python validate_batch.py --contract acme.testnet --days 7

# Search by table
python validate_batch.py --contract acme.testnet --table financial_transactions

# Get specific batch details
python validate_batch.py --contract acme.testnet --batch-id BATCH-2025-06-14-776e2080-T0

# Download S3 data for a batch
python validate_batch.py --contract acme.testnet --batch-id BATCH-2025-06-14-776e2080-T0 --download-s3

# Show statistics
python validate_batch.py --contract acme.testnet --stats

# Interactive mode
python validate_batch.py --contract acme.testnet --interactive
```

#### Transaction Search and Verification (Core ETRAP Use Case)
```bash
# Search and verify specific transactions across any table
python etrap_verify.py --contract <CONTRACT_ID> --database <DB_NAME> [options]

# Find transactions for specific account with amount > 5000
python etrap_verify.py -c acme.testnet -d etrapdb -t financial_transactions -w "account_id=ACC500 AND amount>5000"

# Find all credit transactions for an account
python etrap_verify.py -c acme.testnet -d etrapdb -t financial_transactions -w "account_id=ACC501 AND type=C"

# Search audit logs from yesterday
python etrap_verify.py -c acme.testnet -d etrapdb -t audit_logs --date yesterday

# Search transactions in date range
python etrap_verify.py -c acme.testnet -d etrapdb --after "7 days ago" --before today -w "amount>1000"

# Generate audit report
python etrap_verify.py -c acme.testnet -d etrapdb -t financial_transactions -w "account_id=ACC500" --report

# Show detailed verification info
python etrap_verify.py -c acme.testnet -d etrapdb -t financial_transactions -w "id=66" --detailed

# Search across all tables for user activity
python etrap_verify.py -c acme.testnet -d etrapdb --after "30 days ago" -w "user_id=admin"
```

Supported WHERE clause operators:
- `=` Equal to
- `!=` Not equal to  
- `>` Greater than
- `<` Less than
- `>=` Greater than or equal
- `<=` Less than or equal
- `LIKE` Pattern matching (use % as wildcard)

Examples:
- `account_id=ACC500`
- `amount>5000`
- `reference LIKE '%deposit%'`
- `account_id=ACC500 AND amount>1000 AND type=C`

## Architecture Overview

This is an ETRAP (Enterprise Transaction Recording and Audit Platform) CDC agent that captures database changes and creates immutable audit trails on the NEAR blockchain.

### Data Flow
1. **PostgreSQL** → Database changes occur
2. **Debezium** → Captures changes as CDC events
3. **Redis Streams** → Events are published to Redis streams (pattern: `etrap.public.*`)
4. **CDC Agent** → Consumes events, batches them intelligently
5. **S3 Storage** → Batch data and Merkle trees stored for off-chain reference
6. **NEAR Blockchain** → NFTs minted with Merkle roots for on-chain verification

### Key Components

#### ETRAPCDCAgent (`etrap_cdc_agent.py`)
- Main agent that consumes CDC events from Redis streams
- Implements intelligent batching with configurable parameters:
  - `batch_size`: Maximum events per batch (default: 1000)
  - `batch_timeout`: Read timeout in seconds (default: 60)
  - `min_batch_size`: Minimum events to create batch (default: 1)
  - `force_batch_after`: Force batch creation after N seconds (default: 300)
- Creates Merkle trees for transaction verification
- Stores comprehensive batch data in S3
- Prepares minimal NFT metadata for NEAR blockchain

#### ETRAPValidator (`validate_transaction.py`)
- Validates that specific transactions are included in NFT batches
- Retrieves NFT metadata from NEAR blockchain
- Fetches batch data from S3
- Verifies Merkle proofs to ensure transaction integrity
- Supports searching by multiple criteria (account ID, amount, type, operation, table)

### Data Structures

#### Batch Reference Data (stored in S3)
- Complete transaction records with metadata
- Merkle tree with all nodes and proof paths
- Indices for efficient lookup (by timestamp, operation, date)
- Compliance metadata (rules applied, data classifications)
- Verification signatures

#### NFT Metadata (stored on NEAR)
- Merkle root hash
- Batch summary (transaction count, timestamp range, operations)
- S3 location reference
- Organization ID and database info

### Important Implementation Details

- Uses Redis consumer groups for reliable message consumption
- Decodes base64-encoded field values in CDC events
- Builds complete Merkle trees with proof paths for each transaction
- S3 bucket creation handled automatically with region-specific logic
- NFT metadata kept minimal for cost efficiency on blockchain
- Batch IDs follow pattern: `BATCH-YYYY-MM-DD-{uuid}`