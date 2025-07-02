# ETRAP: Enterprise Transaction Receipt Anchoring Platform
## Complete Design and Implementation Documentation

**Version:** 1.0.1  
**Date:** January 2025  
**Copyright:** © 2025 Graziano Labs Corp. All rights reserved.

---

## Table of Contents

1. [Executive Overview](#1-executive-overview)
2. [System Architecture](#2-system-architecture)
3. [Repository Structure](#3-repository-structure)
4. [Core Components](#4-core-components)
5. [Data Flow and Processing](#5-data-flow-and-processing)
6. [Privacy and Security Model](#6-privacy-and-security-model)
7. [Deployment Architecture](#7-deployment-architecture)
8. [Implementation Details](#8-implementation-details)
9. [Verification Process](#9-verification-process)
10. [Integration Patterns](#10-integration-patterns)
11. [Monitoring and Operations](#11-monitoring-and-operations)
12. [Future Roadmap](#12-future-roadmap)

### Appendices
- [Appendix A: Smart Contract API Reference](#appendix-a-smart-contract-api-reference)
- [Appendix B: Python SDK API Reference](#appendix-b-python-sdk-api-reference)
- [Appendix C: MCP Server Tools Reference](#appendix-c-mcp-server-tools-reference)
- [Appendix D: Error Codes Reference](#appendix-d-error-codes-reference)
- [Appendix E: Configuration Reference](#appendix-e-configuration-reference)
- [Appendix F: ETRAP CLI Reference](#appendix-f-etrap-cli-reference)

---

## 1. Executive Overview

### 1.1 What is ETRAP?

ETRAP (Enterprise Transaction Receipt Anchoring Platform) is a blockchain-based audit trail system that captures database changes and creates immutable proofs on the NEAR blockchain. The platform combines traditional database reliability with blockchain immutability, creating tamper-proof audit trails for regulatory compliance and data integrity verification.

### 1.2 Key Features

- **Zero Data Exposure**: No sensitive data ever leaves customer premises
- **Blockchain Proof**: Immutable audit trails anchored on NEAR Protocol
- **Real-time Verification**: Sub-second transaction verification using Merkle proofs
- **Regulatory Compliance**: Meets SOX, GDPR, HIPAA, and MIFID II requirements
- **Generic Architecture**: Works with any PostgreSQL database schema
- **Cost Efficient**: Batching reduces blockchain costs by 1000x

### 1.3 Etymology

The Greek word "έτραπ" (etrap) is the strong aorist active form of the verb "τρέπω" (trepo) meaning "to turn" or "to change direction" - fitting for a platform that tracks database changes and transformations.

---

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                           ETRAP SYSTEM ARCHITECTURE                           │
├───────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  CUSTOMER PREMISES(ON-PREMISES)                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │                                                                         │  │
│  │  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐           │  │
│  │  │  PostgreSQL  │      │   Debezium   │      │    Redis     │           │  │
│  │  │   Database   │─────▶│     CDC      │─────▶│   Streams    │           │  │
│  │  │              │      │              │      │              │           │  │
│  │  └──────────────┘      └──────────────┘      └──────────────┘           │  │
│  │         │                      │                      │                 │  │
│  │         │                      │                      │                 │  │
│  │         ▼                      ▼                      ▼                 │  │
│  │  ┌────────────────────────────────────────────────────────────────┐     │  │
│  │  │                     ETRAP CDC AGENT                            │     │  │
│  │  │  ┌───────────────────────────────────────────────────────────┐ │     │  │
│  │  │  │  1. Consume CDC Events from Redis Streams                 │ │     │  │
│  │  │  │  2. Strip All Sensitive Data                              │ │     │  │
│  │  │  │  3. Create SHA-256 Hashes of Transactions                 │ │     │  │
│  │  │  │  4. Build Merkle Trees from Transaction Batches           │ │     │  │
│  │  │  │  5. Prepare Metadata (NO ACTUAL DATA)                     │ │     │  │
│  │  │  └───────────────────────────────────────────────────────────┘ │     │  │
│  │  └──────────────────────────────┬────────────┬────────────────────┘     │  │
│  └─────────────────────────────────┼────────────┼──────────────────────────┘  │
│                                    │            │                             │
│ ═══════════════════════════════════╪════════════╪════════════════════════════ │
│  CLOUD / PUBLIC NETWORK            │            │    (Only Hashes Leave)      │
│                                    ▼            ▼                             │
│                          ┌──────────────┐ ┌──────────────┐                    │
│                          │   AWS S3     │ │    NEAR      │                    │
│                          │              │ │  Blockchain  │                    │
│                          │ • Hashes     │ │              │                    │
│                          │ • Merkle Tree│ │ • NFT Token  │                    │
│                          │ • Metadata   │ │ • Merkle Root│                    │
│                          │ • NO DATA    │ │ • Timestamp  │                    │
│                          └──────────────┘ └──────────────┘                    │
│                                    │            │                             │
│                                    ▼            ▼                             │
│                          ┌─────────────────────────────────┐                  │
│                          │      VERIFICATION LAYER         │                  │
│                          │  • ETRAP SDK (Python)           │                  │
│                          │  • MCP Server (AI Integration)  │                  │
│                          │  • CLI Tools                    │                  │
│                          └─────────────────────────────────┘                  │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Component Interaction Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                      COMPONENT INTERACTION FLOW                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   Database Change                                                   │
│         │                                                           │
│         ▼                                                           │
│   WAL → Debezium                                                    │
│         │                                                           │
│         ▼                                                           │
│   CDC Event Created                                                 │
│         │                                                           │
│         ▼                                                           │
│   Redis Stream Entry                                                │
│         │                                                           │
│   ┌─────┴─────┐                                                     │
│   │           │                                                     │
│   │ CDC Agent │ ◀── Consumes Events                                 │
│   │           │                                                     │
│   └─────┬─────┘                                                     │
│         │                                                           │
│         ▼                                                           │
│   Batch Formation                                                   │
│   (1000 events or 5 min)                                            │
│         │                                                           │
│         ▼                                                           │
│   Hash Generation                                                   │
│   SHA256(tx_data)                                                   │
│         │                                                           │
│         ▼                                                           │
│   Merkle Tree Build                                                 │
│         │                                                           │
│    ┌────┴────┐                                                      │
│    ▼         ▼                                                      │
│   S3       NEAR                                                     │
│  Store    Mint NFT                                                  │
│    │         │                                                      │
│    └────┬────┘                                                      │
│         │                                                           │
│         ▼                                                           │
│   Verification Ready                                                │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Repository Structure

### 3.1 Repository Overview

| Repository | URL | Purpose | Language |
|------------|-----|---------|----------|
| **etrap** | https://github.com/marcoeg/etrap | Main CDC agent and infrastructure | Python |
| **etrap-notary** | https://github.com/marcoeg/etrap-notary | NEAR smart contract | Rust |
| **etrap-sdk** | https://github.com/marcoeg/etrap-sdk | Python SDK for verification | Python |
| **etrap-mcp** | https://github.com/marcoeg/etrap-mcp | MCP server for AI integration | Python |

### 3.2 Repository Details

#### 3.2.1 etrap (Main Repository)
```
etrap/
├── cdc-agent/
│   ├── etrap_cdc_agent.py      # Main CDC processing agent
│   ├── requirements.txt         # Python dependencies
│   └── tests/                   # Unit tests
├── docker/
│   ├── docker-compose.yml       # Complete stack deployment
│   ├── Dockerfile.agent         # CDC agent container
│   ├── Dockerfile.debezium      # Debezium server container
│   └── README.md               # Docker deployment guide
├── scripts/
│   ├── onboard_organization.sh  # NEAR account setup
│   ├── generate_etrap_docker.sh # Docker configuration
│   └── deploy.sh               # Deployment automation
├── docs/
│   └── *.md                    # Documentation files
└── LICENSE
```

#### 3.2.2 etrap-notary (Smart Contract)
```
etrap-notary/
├── src/
│   └── lib.rs                  # NEAR smart contract implementation
├── scripts/
│   ├── build.sh               # Contract build script
│   ├── etrap_deploy.sh        # Deployment examples
│   ├── check_gas_usage.sh     # Gas monitoring
│   └── test_*.sh              # Various test scripts
├── out/
│   └── etrap_contract.wasm    # Compiled contract
├── Cargo.toml                 # Rust dependencies
└── README.md                  # Contract documentation
```

#### 3.2.3 etrap-sdk (Python SDK)
```
etrap-sdk/
├── src/etrap_sdk/
│   ├── __init__.py
│   ├── client.py             # Main ETRAP client and verification
│   ├── models.py             # Pydantic data models
│   ├── utils.py              # Utility functions
│   ├── exceptions.py         # Error definitions
│   └── py.typed              # Type annotations marker
├── examples/
│   ├── etrap_verify_sdk.py   # Primary verification tool
│   ├── basic_usage.py        # Basic SDK usage examples
│   ├── list_batches.py       # Batch listing example
│   ├── debug_batch.py        # Batch debugging tool
│   └── analyze_batch_structure.py  # Batch analysis
├── tests/
│   └── test_*.py             # Test suite
├── pyproject.toml            # Project configuration (UV/Hatch)
└── README.md                 # SDK documentation
```

#### 3.2.4 etrap-mcp (MCP Server)
```
etrap-mcp/
├── mcp_etrap/
│   ├── __init__.py
│   ├── app.py               # FastMCP server implementation
│   ├── mcp_config.py        # Configuration management
│   └── tools/               # MCP tool definitions
│       ├── __init__.py
│       ├── verify_transaction.py  # Transaction verification tool
│       ├── verify_batch.py        # Batch verification tool
│       ├── get_batch.py           # Batch retrieval tool
│       ├── list_batches.py        # Batch listing tool
│       ├── search_batches.py      # Batch search tool
│       ├── get_contract_info.py   # Contract info tool
│       └── get_config.py          # Configuration tool
├── main.py                  # Entry point
├── pyproject.toml           # Project configuration (UV)
├── test_mcp_stdio.py        # MCP server testing
└── README.md                # MCP documentation
```

---

## 4. Core Components

### 4.1 PostgreSQL Database (Customer Infrastructure)

The source of truth for all business data, remaining entirely within customer control.

**Key Characteristics:**
- No modifications required to existing schemas
- Works with any table structure
- Logical replication enabled for CDC
- All data remains on-premises

### 4.2 Debezium CDC Connector (Customer Infrastructure)

Captures database changes without impacting performance.

**Configuration Example:**
```json
{
  "name": "etrap-connector",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "database.hostname": "localhost",
    "database.port": "5432",
    "database.user": "etrap_user",
    "database.password": "${POSTGRES_PASSWORD}",
    "database.dbname": "production_db",
    "database.server.name": "etrap",
    "table.include.list": "public.*",
    "plugin.name": "pgoutput",
    "publication.autocreate.mode": "filtered",
    "redis.address": "redis://localhost:6379",
    "redis.key": "etrap"
  }
}
```

### 4.3 Redis Streams (Customer Infrastructure)

High-performance message broker for CDC events.

**Stream Structure:**
```
Stream Pattern: etrap.{schema}.{table}
Example: etrap.public.financial_transactions

Message Structure:
┌────────────────┬──────────────────────────────┐
│  Message ID    │  1749864039877-0             │
├────────────────┼──────────────────────────────┤
│  Fields        │  key: {"id": 123}            │
│                │  value: {CDC event JSON}     │
└────────────────┴──────────────────────────────┘
```

### 4.4 ETRAP CDC Agent (Customer Infrastructure)

The core processing engine that ensures data privacy while creating blockchain proofs.

**Key Functions:**
```python
class ETRAPCDCAgent:
    def __init__(self, config):
        # Redis connection
        # S3 client setup
        # NEAR client initialization
        # Batching parameters
        
    def consume_cdc_events(self):
        # Main event loop
        # Intelligent batching logic
        # Batch processing triggers
        
    def process_batch(self, events):
        # Strip sensitive data
        # Create transaction hashes
        # Build Merkle tree
        # Store in S3
        # Mint NFT on NEAR
        
    def create_merkle_tree(self, hashes):
        # SHA-256 based tree construction
        # Proof generation
        # Root calculation
```

### 4.5 NEAR Smart Contract (Public Blockchain)

Provides immutable anchoring for audit trails.

**Contract Structure:**
```rust
#[near_bindgen]
pub struct ETRAPContract {
    // NFT implementation
    tokens: NonFungibleToken,
    
    // Batch metadata storage
    batch_summaries: LookupMap<TokenId, BatchSummary>,
    
    // Indices for efficient queries
    tokens_by_database: LookupMap<String, IterableSet<TokenId>>,
    tokens_by_month: LookupMap<String, Vector<TokenId>>,
    tokens_by_timestamp: IterableMap<u64, TokenId>,
    tokens_by_table: LookupMap<String, IterableSet<TokenId>>,
    
    // Recent tokens cache
    recent_tokens: Vector<TokenId>,
    
    // Settings
    etrap_settings: ETRAPSettings,
}
```

---

## 5. Data Flow and Processing

### 5.1 Transaction Journey

```
1. Database Transaction
   └─> INSERT INTO transactions VALUES (...)

2. CDC Capture (Debezium)
   └─> {
         "op": "c",
         "after": {
           "id": 123,
           "amount": 1500.00,
           "account": "ACC456"
         },
         "source": {
           "table": "transactions",
           "ts_ms": 1749864039877
         }
       }

3. Redis Stream Entry
   └─> etrap.public.transactions
       └─> 1749864039877-0

4. CDC Agent Processing
   └─> Batch accumulation (up to 1000 events)
   └─> Data stripping (remove sensitive values)
   └─> Hash generation: SHA256(normalized_data)
   └─> Result: "7d865e959b2466918c..."

5. Merkle Tree Construction
   └─> Leaf nodes: [hash1, hash2, ..., hash1000]
   └─> Tree building with SHA256
   └─> Root: "5f3a8b2c7d9e1a4b..."

6. External Storage (S3)
   └─> /etrapdb/transactions/BATCH-2025-01-15-001/
       ├── batch-data.json (hashes only)
       ├── merkle-tree.json
       └── indices/

7. Blockchain Anchoring (NEAR)
   └─> NFT Token: BATCH-2025-01-15-001
   └─> Merkle Root: "5f3a8b2c7d9e1a4b..."
   └─> No transaction data
```

### 5.2 Batching Logic

```
┌─────────────────────────────────────────────────┐
│              BATCHING DECISION TREE             │
├─────────────────────────────────────────────────┤
│                                                 │
│  New Events Available?                          │
│         │                                       │
│    ┌────┴────┐                                  │
│    │   NO    │──▶ Wait with timeout             │
│    └─────────┘                                  │
│         │                                       │
│    ┌────┴────┐                                  │
│    │   YES   │                                  │
│    └─────────┘                                  │
│         │                                       │
│         ▼                                       │
│  Batch Size >= 1000?                            │
│         │                                       │
│         ├──YES──▶ Process Batch Immediately     │
│         │                                       │
│         NO                                      │
│         │                                       │
│         ▼                                       │
│  Time Since Last > 5 min?                       │
│         │                                       │
│         ├──YES──▶ Process Current Batch         │
│         │                                       │
│         NO                                      │
│         │                                       │
│         ▼                                       │
│  Continue Collecting Events                     │
│                                                 │
└─────────────────────────────────────────────────┘
```

### 5.3 Merkle Tree Structure

```
Example: 8 Transaction Batch

Level 3 (Root):           R
                         / \
Level 2:              H01   H23
                     /  \   /  \
Level 1:          H0   H1 H2   H3
                  / \ / \ / \ / \
Level 0:        T0 T1 T2 T3 T4 T5 T6 T7

Where:
- T0-T7: Transaction hashes (SHA256)
- H0 = SHA256(T0 || T1)
- H01 = SHA256(H0 || H1)
- R = SHA256(H01 || H23)

Proof for T2:
Path: [T3, H0, H23]
Verification: SHA256(SHA256(SHA256(T2||T3)||H0)||H23) == R
```

---

## 6. Privacy and Security Model

### 6.1 Data Sovereignty Architecture

```
┌──────────────────────────────────────────────────────────┐
│                  DATA PRIVACY BOUNDARIES                 │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ON-PREMISES (Customer Controlled)                       │
│  ┌─────────────────────────────────────────────────────┐ │
│  │  What Stays Inside:                                 │ │
│  │  • Complete database records                        │ │
│  │  • Transaction values and amounts                   │ │
│  │  • Customer names, IDs, account numbers             │ │
│  │  • Business logic and relationships                 │ │
│  │  • All PII and sensitive data                       │ │
│  │  • Actual SQL queries and operations                │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                          │
│  ═══════════════ SECURITY BOUNDARY ═══════════════       │
│                                                          │
│  EXTERNAL (Cloud/Blockchain)                             │
│  ┌─────────────────────────────────────────────────────┐ │
│  │  What Goes Outside:                                 │ │
│  │  • SHA-256 hashes of transactions                   │ │
│  │  • Merkle tree structures                           │ │
│  │  • Operation types (INSERT/UPDATE/DELETE)           │ │
│  │  • Timestamps                                       │ │
│  │  • Table names (metadata only)                      │ │
│  │  • Row counts                                       │ │
│  │  • Batch identifiers                                │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 6.2 Security Features

1. **Cryptographic Integrity**
   - SHA-256 hashing for all transactions
   - Merkle tree proofs for verification
   - ECDSA signatures on blockchain

2. **Access Control**
   - Customer-controlled S3 buckets
   - NEAR account permissions
   - Read-only verification tools

3. **Audit Trail Security**
   - Immutable blockchain records
   - Tamper-evident Merkle trees
   - Time-stamped anchoring

---

## 7. Deployment Architecture

### 7.1 Docker Deployment

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:14
    environment:
      POSTGRES_DB: etrapdb
      POSTGRES_USER: etrap
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    command: 
      - "postgres"
      - "-c"
      - "wal_level=logical"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - etrap_network

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    networks:
      - etrap_network

  debezium:
    build: 
      context: .
      dockerfile: Dockerfile.debezium
    environment:
      POSTGRES_HOST: postgres
      POSTGRES_USER: etrap
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      REDIS_HOST: redis
    depends_on:
      - postgres
      - redis
    networks:
      - etrap_network

  etrap-agent:
    build:
      context: .
      dockerfile: Dockerfile.agent
    environment:
      REDIS_HOST: redis
      NEAR_ACCOUNT: ${NEAR_ACCOUNT}
      NEAR_ENV: ${NEAR_ENV}
      AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID}
      AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY}
      ETRAP_S3_BUCKET: ${ETRAP_S3_BUCKET}
    volumes:
      - ~/.near-credentials:/home/etrap/.near-credentials:ro
    depends_on:
      - redis
      - debezium
    networks:
      - etrap_network

volumes:
  postgres_data:
  redis_data:

networks:
  etrap_network:
    driver: bridge
```

### 7.2 Deployment Steps

```bash
# 1. NEAR Account Setup
./scripts/onboard_organization.sh
# Creates: organization.near account
# Deploys: Smart contract
# Outputs: Credentials

# 2. Docker Configuration
./scripts/generate_etrap_docker.sh
# Input: Organization details
# Output: Configured docker-compose.yml

# 3. Deploy Stack
docker-compose up -d
# Starts: All ETRAP components
# Begins: Automatic CDC capture
```


---

## 8. Implementation Details

### 8.1 CDC Agent Implementation

```python
# Key implementation patterns from etrap_cdc_agent.py

class ETRAPCDCAgent:
    def __init__(self, config):
        # Configuration
        self.batch_size = 1000
        self.batch_timeout = 60  # seconds
        self.min_batch_size = 1
        self.force_batch_after = 300  # 5 minutes
        
        # Initialize connections
        self.redis_client = redis.Redis(...)
        self.s3_client = boto3.client('s3', ...)
        self.near_client = self.init_near_client()
        
    def process_batch(self, events):
        """Core batch processing logic"""
        # 1. Group events by table
        events_by_table = self.group_by_table(events)
        
        for table, table_events in events_by_table.items():
            # 2. Create batch metadata
            batch_id = self.generate_batch_id()
            
            # 3. Process transactions (strip data, create hashes)
            transactions = []
            for event in table_events:
                tx_metadata = self.create_transaction_metadata(event)
                tx_hash = self.hash_transaction(event)
                transactions.append({
                    'metadata': tx_metadata,
                    'hash': tx_hash
                })
            
            # 4. Build Merkle tree
            merkle_tree = self.build_merkle_tree(
                [tx['hash'] for tx in transactions]
            )
            
            # 5. Create batch reference data
            batch_data = {
                'batch_info': {
                    'batch_id': batch_id,
                    'created_at': int(time.time() * 1000),
                    'organization_id': self.organization_id,
                    'database_name': database
                },
                'transactions': transactions,
                'merkle_tree': merkle_tree
            }
            
            # 6. Store in S3
            self.store_batch_in_s3(database, batch_id, table, batch_data)
            
            # 7. Mint NFT
            self.mint_nft(batch_id, merkle_tree['root'], len(transactions))
```

### 8.2 Smart Contract Implementation

```rust
// Key patterns from lib.rs

#[near_bindgen]
impl ETRAPContract {
    #[payable]
    pub fn mint_batch(
        &mut self,
        token_id: TokenId,
        receiver_id: AccountId,
        token_metadata: TokenMetadata,
        batch_summary: BatchSummary,
    ) -> Token {
        // Validate inputs
        require!(!self.etrap_settings.paused, "Contract is paused");
        require!(
            self.tokens.nft_token(token_id.clone()).is_none(),
            "Token already exists"
        );
        
        // Calculate fees
        let storage_deposit = env::storage_byte_cost() * 4000;
        let etrap_fee = self.etrap_settings.fee_amount;
        let total_required = storage_deposit + etrap_fee;
        
        require!(
            env::attached_deposit() >= total_required,
            "Insufficient deposit"
        );
        
        // Transfer fee to treasury
        if etrap_fee > 0 {
            Promise::new(self.etrap_settings.etrap_treasury.clone())
                .transfer(etrap_fee);
        }
        
        // Mint NFT and update indices
        self.internal_mint_with_indices(
            token_id,
            receiver_id,
            token_metadata,
            batch_summary
        )
    }
    
    pub fn verify_document_in_batch(
        &self,
        token_id: TokenId,
        document_hash: String,
        merkle_proof: Vec<String>,
        leaf_index: u32,
    ) -> bool {
        // Get batch summary
        let batch_summary = self.batch_summaries
            .get(&token_id)
            .expect("Batch not found");
        
        // Verify merkle proof
        let mut current_hash = document_hash;
        let mut current_index = leaf_index;
        
        for proof_element in merkle_proof {
            let combined = if current_index % 2 == 0 {
                format!("{}{}", current_hash, proof_element)
            } else {
                format!("{}{}", proof_element, current_hash)
            };
            
            current_hash = Self::sha256(&combined);
            current_index /= 2;
        }
        
        current_hash == batch_summary.merkle_root
    }
}
```

### 8.3 Verification Process Implementation

```python
# From etrap-sdk client.py

class ETRAPClient:
    def __init__(self, organization_id, network="testnet", s3_config=None):
        self.organization_id = organization_id
        self.near_client = self._init_near_client(network)
        self.s3_client = boto3.client('s3', **s3_config) if s3_config else None
        
    async def verify_transaction(self, transaction_data, hints=None):
        """Complete transaction verification process"""
        
        # 1. Normalize and compute hash
        normalized = normalize_transaction_data(transaction_data)
        tx_hash = compute_transaction_hash(normalized, normalize=False)
        
        # 2. Find relevant batch using hints or search
        if hints and hints.batch_id:
            batch = await self.get_batch(hints.batch_id)
            if batch:
                result = await self._verify_in_batch(tx_hash, batch, hints.expected_operation)
                return result
        
        # 3. Time range or general search
        if hints and hints.time_range:
            batches = await self._get_batches_by_time_range(
                hints.time_range.start,
                hints.time_range.end,
                database=hints.database_name,
                limit=100
            )
        else:
            batches = await self._get_recent_batches(100)
        
        # 4. Verify in each candidate batch
        for batch in batches:
            result = await self._verify_in_batch(tx_hash, batch, hints.expected_operation)
            if result:
                return result
        
        return VerificationResult(
            verified=False,
            transaction_hash=tx_hash,
            error="Transaction not found in any batch"
        )
```

---

## 9. Verification Process

### 9.1 Verification Flow

```
┌──────────────────────────────────────────────────────┐
│              VERIFICATION PROCESS                    │
├──────────────────────────────────────────────────────┤
│                                                      │
│  1. User provides transaction details                │
│     └─> Transaction ID, Timestamp, Table             │
│                                                      │
│  2. Query NEAR blockchain                            │
│     └─> Find batches in time range                   │
│     └─> Get merkle roots and metadata                │
│                                                      │
│  3. For each candidate batch:                        │
│     └─> Fetch batch data from S3                     │
│     └─> Search for transaction                       │
│     └─> Extract merkle proof                         │
│                                                      │
│  4. Verify merkle proof                              │
│     └─> Reconstruct path to root                     │
│     └─> Compare with blockchain root                 │
│                                                      │
│  5. Return verification result                       │
│     └─> Valid/Invalid status                         │
│     └─> Blockchain proof details                     │
│     └─> Timestamp and batch info                     │
│                                                      │
└──────────────────────────────────────────────────────┘
```

### 9.2 CLI Verification Example

```bash
# Verify a specific transaction using the SDK tool
python etrap-sdk/examples/etrap_verify_sdk.py \
    --organization myorg \
    --data '{"id": 123, "amount": "1000.00", "account_id": "ACC001", "type": "C"}' \
    --hint-time-start "2025-01-15T10:00:00" \
    --hint-time-end "2025-01-15T11:00:00" \
    --network testnet

# Output:
✅ Transaction Verified

Transaction Details:
├── Hash: 7d865e959b2466918c9863afca942d0fb89d7c9ac0c99bafc3749504ded97730
├── Operation: INSERT
├── Database: etrapdb
└── Table: financial_transactions

Blockchain Proof:
├── Batch ID: BATCH-2025-01-15-042
├── NFT Token: BATCH-2025-01-15-042  
├── Merkle Root: 0x5f3a8b2c7d9e1a4b...
├── NEAR Contract: myorg.testnet
└── Verification Time: 324ms

Verification: VALID ✓
```

---

## 10. Integration Patterns

### 10.1 Application Integration

```python
# Example: Integrate ETRAP verification into existing application

from etrap_sdk import ETRAPClient

class AuditableTransactionService:
    def __init__(self):
        self.etrap = ETRAPClient(
            near_account="myorg.near",
            near_network="mainnet",
            s3_bucket="etrap-myorg"
        )
        
    def process_transaction(self, transaction_data):
        # 1. Process transaction normally
        tx_id = self.database.insert(transaction_data)
        
        # 2. Later, verify it was captured
        verification = self.etrap.verify_transaction(
            transaction_id=tx_id,
            timestamp=transaction_data['created_at']
        )
        
        if not verification['verified']:
            self.alert_compliance_team(
                "Transaction not anchored to blockchain",
                tx_id
            )
            
        return tx_id
        
    def generate_audit_report(self, start_date, end_date):
        # Get all batches in date range
        batches = self.etrap.get_batches_by_time_range(
            start_date, 
            end_date
        )
        
        report = {
            'period': f"{start_date} to {end_date}",
            'total_batches': len(batches),
            'total_transactions': sum(b['tx_count'] for b in batches),
            'blockchain_proofs': [b['merkle_root'] for b in batches]
        }
        
        return report
```

### 10.2 MCP Server Integration

```python
# Example: AI Assistant Integration via FastMCP

from fastmcp import FastMCP
from etrap_sdk import ETRAPClient, SearchCriteria, DateRange

app = FastMCP("ETRAP MCP Server")
etrap_client = ETRAPClient(organization_id="myorg")

@app.tool()
async def search_transactions(
    database: str,
    table: str = None,
    start_date: str = None,
    end_date: str = None,
    operation_type: str = None
) -> dict:
    """Search for transactions in ETRAP"""
    
    criteria = SearchCriteria()
    if start_date and end_date:
        criteria.date_range = DateRange(start=start_date, end=end_date)
    if operation_type:
        criteria.operation_type = [operation_type]
    
    results = await etrap_client.search_batches(criteria)
    
    return {
        "summary": f"Found {len(results.matching_batches)} batches",
        "batches": [batch.dict() for batch in results.matching_batches],
        "search_time_ms": results.search_time_ms
    }
```

---

## 11. Monitoring and Operations

### 11.1 Monitoring Architecture

```
┌────────────────────────────────────────────────────┐
│              MONITORING STACK                       │
├────────────────────────────────────────────────────┤
│                                                     │
│  Metrics Collection                                 │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │ Prometheus  │  │   Grafana    │  │ Alerting  │ │
│  └──────┬──────┘  └──────┬───────┘  └─────┬─────┘ │
│         │                 │                 │       │
│  ┌──────┴─────────────────┴─────────────────┴────┐ │
│  │              Metrics Endpoints                 │ │
│  ├────────────────┬──────────────┬───────────────┤ │
│  │  CDC Agent     │    Redis     │  NEAR Query   │ │
│  │  • Batch size  │  • Stream lag│  • Gas costs  │ │
│  │  • Process time│  • Memory    │  • NFT count  │ │
│  │  • Error rate  │  • Queue size│  • Success %  │ │
│  └────────────────┴──────────────┴───────────────┘ │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### 11.2 Key Metrics

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| CDC Lag | < 1 minute | > 5 minutes |
| Redis Stream Length | < 10,000 | > 50,000 |
| Batch Processing Time | < 30 seconds | > 60 seconds |
| NFT Minting Success | > 99.9% | < 99% |
| S3 Upload Time | < 5 seconds | > 10 seconds |
| Verification Latency | < 200ms | > 500ms |

### 11.3 Operational Procedures

```bash
# Daily Operations Checklist

# 1. Check system health
docker-compose ps                           # Container status
docker logs etrap-agent --tail=100         # Agent health
redis-cli info replication                 # Redis connectivity

# 2. Monitor batch creation rate
python validate_batch.py --contract myorg.testnet --recent 20 --stats

# 3. Verify recent batches
python validate_batch.py --contract myorg.testnet --recent 10
python validate_batch.py --contract myorg.testnet --days 1

# 4. Check NEAR costs and usage
near view myorg.testnet get_recent_batches '{"limit": 10}'
near view-state myorg.testnet --finality final | grep storage_usage

# 5. Review error logs
docker logs etrap-agent --since=24h | grep ERROR
docker logs debezium --since=24h | grep ERROR
docker logs redis --since=24h | grep WARNING

# 6. S3 storage verification
aws s3 ls s3://etrap-myorg/ --recursive --summarize
aws s3api head-bucket --bucket etrap-myorg

# 7. CDC lag monitoring
redis-cli xinfo stream etrap.public.financial_transactions
redis-cli xinfo groups etrap.public.financial_transactions

# 8. Database replication slot health
psql -h localhost -U etrap -d etrapdb -c "SELECT * FROM pg_replication_slots;"
```

---
 
---

## Appendix A: Smart Contract API Reference

### Contract Initialization

```rust
pub fn new(
    organization_id: AccountId,
    organization_name: String,
    etrap_treasury: AccountId,
    etrap_fee_amount: f64,
) -> Self
```

**Parameters:**
- `organization_id`: NEAR account ID of the organization
- `organization_name`: Human-readable organization name
- `etrap_treasury`: Account to receive ETRAP fees
- `etrap_fee_amount`: Fee amount in NEAR

### Core Methods

#### mint_batch
```rust
#[payable]
pub fn mint_batch(
    &mut self,
    token_id: TokenId,
    receiver_id: AccountId,
    token_metadata: TokenMetadata,
    batch_summary: BatchSummary,
) -> Token
```

**Purpose:** Creates a new NFT representing a batch of transactions

**Parameters:**
- `token_id`: Unique identifier for the batch
- `receiver_id`: Account that will own the NFT
- `token_metadata`: Standard NEP-177 metadata
- `batch_summary`: Batch-specific metadata

**Required Deposit:** Storage cost + ETRAP fee

**Example:**
```bash
near call etrap.myorg.near mint_batch '{
  "token_id": "BATCH-2025-01-15-001",
  "receiver_id": "myorg.near",
  "token_metadata": {
    "title": "Batch 2025-01-15 #001",
    "issued_at": "1749864039877"
  },
  "batch_summary": {
    "database_name": "production",
    "table_names": ["transactions"],
    "timestamp": 1749864039877,
    "tx_count": 1000,
    "merkle_root": "5f3a8b2c7d9e1a4b...",
    "s3_bucket": "etrap-myorg",
    "s3_key": "production/BATCH-2025-01-15-001/",
    "size_bytes": 524288,
    "operation_counts": {
      "inserts": 600,
      "updates": 300,
      "deletes": 100
    }
  }
}' --accountId myorg.near --deposit 0.1
```

#### verify_document_in_batch
```rust
pub fn verify_document_in_batch(
    &self,
    token_id: TokenId,
    document_hash: String,
    merkle_proof: Vec<String>,
    leaf_index: u32,
) -> bool
```

**Purpose:** Verifies a transaction belongs to a batch using merkle proof

**Parameters:**
- `token_id`: The batch NFT token ID
- `document_hash`: Hash of the document to verify
- `merkle_proof`: Array of hashes forming the proof path
- `leaf_index`: Position in the merkle tree

**Returns:** `true` if verification succeeds

**Example:**
```bash
near view etrap.myorg.near verify_document_in_batch '{
  "token_id": "BATCH-2025-01-15-001",
  "document_hash": "7d865e959b2466918c9863afca942d0fb89d7c9ac0c99bafc3749504ded97730",
  "merkle_proof": [
    "9b2466918c9863afca942d0fb89d7c9ac0c99bafc3749504ded97730",
    "c3e0e8a5e8a5c3e0e8a5e8a5c3e0e8a5e8a5c3e0e8a5e8a5c3e0e8a5"
  ],
  "leaf_index": 42
}'
```

### Query Methods

#### get_recent_batches
```rust
pub fn get_recent_batches(&self, limit: Option<u64>) -> Vec<BatchInfo>
```

**Purpose:** Retrieves the most recently created batches

**Parameters:**
- `limit`: Maximum number of batches (default: 20, max: 100)

#### get_batches_by_database
```rust
pub fn get_batches_by_database(
    &self,
    database: String,
    from_index: Option<u64>,
    limit: Option<u64>,
) -> BatchSearchResult
```

**Purpose:** Search batches by database name with pagination

#### get_batches_by_time_range
```rust
pub fn get_batches_by_time_range(
    &self,
    start_timestamp: u64,
    end_timestamp: u64,
    database: Option<String>,
    limit: Option<u64>,
) -> Vec<BatchInfo>
```

**Purpose:** Find batches within a time range

#### get_batches_by_table
```rust
pub fn get_batches_by_table(
    &self,
    table_name: String,
    limit: Option<u64>,
) -> Vec<BatchInfo>
```

**Purpose:** Find batches affecting a specific table

### Admin Methods

#### set_paused
```rust
#[private]
pub fn set_paused(&mut self, paused: bool)
```

**Purpose:** Pause/unpause contract operations

#### update_treasury
```rust
#[private]
pub fn update_treasury(&mut self, new_treasury: AccountId)
```

**Purpose:** Update fee collection address

### Data Structures

#### BatchSummary
```rust
pub struct BatchSummary {
    pub database_name: String,
    pub table_names: Vec<String>,
    pub timestamp: u64,
    pub tx_count: u32,
    pub merkle_root: String,
    pub s3_bucket: String,
    pub s3_key: String,
    pub size_bytes: u64,
    pub operation_counts: OperationCounts,
}
```

#### TokenMetadata (NEP-177)
```rust
pub struct TokenMetadata {
    pub title: Option<String>,
    pub description: Option<String>,
    pub media: Option<String>,
    pub media_hash: Option<String>,
    pub copies: Option<u64>,
    pub issued_at: Option<String>,
    pub expires_at: Option<String>,
    pub starts_at: Option<String>,
    pub updated_at: Option<String>,
    pub extra: Option<String>,
    pub reference: Option<String>,
    pub reference_hash: Option<String>,
}
```

---

## Appendix B: Python SDK API Reference

### Client Initialization

```python
from etrap_sdk import ETRAPClient, S3Config

client = ETRAPClient(
    organization_id="myorg",
    network="mainnet",  # or "testnet"
    s3_config=S3Config(
        bucket_name="etrap-myorg",
        region="us-west-2",
        access_key_id="...",
        secret_access_key="..."
    )
)
```

### Transaction Verification

#### verify_transaction
```python
async def verify_transaction(
    self,
    transaction_data: Dict[str, Any],
    hints: Optional[VerificationHints] = None,
    use_contract_verification: bool = False
) -> VerificationResult
```

**Purpose:** Verify a specific transaction was anchored to blockchain

**Parameters:**
- `transaction_data`: Complete transaction data dictionary
- `hints`: Optional optimization hints for faster verification
- `use_contract_verification`: Use smart contract verification (slower but authoritative)

**Returns:**
```python
@dataclass
class VerificationResult:
    verified: bool
    transaction_hash: str
    batch_id: Optional[str] = None
    merkle_proof: Optional[MerkleProof] = None
    blockchain_timestamp: Optional[datetime] = None
    gas_used: Optional[str] = None
    error: Optional[str] = None
    operation_type: Optional[str] = None
```

**Example:**
```python
from etrap_sdk import VerificationHints, TimeRange

result = await client.verify_transaction(
    transaction_data={
        "id": 123,
        "amount": "1000.00",
        "account_id": "ACC001",
        "created_at": "2025-01-15T10:30:00"
    },
    hints=VerificationHints(
        time_range=TimeRange(
            start=datetime(2025, 1, 15, 10, 0, 0),
            end=datetime(2025, 1, 15, 11, 0, 0)
        ),
        database_name="production",
        expected_operation="INSERT"
    )
)

if result.verified:
    print(f"✅ Verified in batch {result.batch_id}")
    print(f"Operation: {result.operation_type}")
else:
    print(f"❌ Verification failed: {result.error}")
```

### Batch Operations

#### get_batch
```python
async def get_batch(self, batch_id: str) -> Optional[BatchInfo]
```

**Purpose:** Retrieve batch information from blockchain

**Returns:**
```python
@dataclass
class BatchInfo:
    batch_id: str
    database_name: str
    table_names: List[str]
    transaction_count: int
    merkle_root: str
    timestamp: datetime
    s3_location: S3Location
    size_bytes: int
```

#### list_batches
```python
async def list_batches(
    self,
    filter: Optional[BatchFilter] = None,
    limit: int = 100,
    offset: int = 0,
    order_by: str = "timestamp_desc"
) -> BatchList
```

**Purpose:** List batches with optional filtering and pagination

### Report Generation

#### search_batches
```python
async def search_batches(
    self,
    criteria: SearchCriteria
) -> SearchResults
```

**Purpose:** Search for batches matching specific criteria

**Example:**
```python
from etrap_sdk import SearchCriteria, DateRange

criteria = SearchCriteria(
    date_range=DateRange(
        start="2025-01-01",
        end="2025-01-31"
    ),
    operation_type=["INSERT", "UPDATE"]
)

results = await client.search_batches(criteria)
print(f"Found {len(results.matching_batches)} batches")
```

### Utility Functions

#### compute_merkle_root
```python
def compute_merkle_root(
    self,
    transaction_hashes: List[str]
) -> str
```

**Purpose:** Calculate merkle root for a list of hashes

#### verify_merkle_proof
```python
def verify_merkle_proof(
    self,
    leaf_hash: str,
    proof_path: List[str],
    leaf_index: int,
    expected_root: str
) -> bool
```

**Purpose:** Verify a merkle proof locally

### Error Handling

```python
from etrap_sdk.exceptions import (
    ETRAPError,
    VerificationError,
    BatchNotFoundError,
    NetworkError
)

try:
    result = await client.verify_transaction(transaction_data)
except BatchNotFoundError:
    print("No batch found for the specified criteria")
except VerificationError as e:
    print(f"Verification failed: {e}")
except NetworkError:
    print("Network connection error")
```

---

## Appendix C: MCP Server Tools Reference

### Tool Overview

The ETRAP MCP Server provides the following tools for AI integration:

### verify_transaction

**Purpose:** Verify a specific transaction's blockchain proof

**Parameters:**
```python
{
    "transaction_id": str,
    "timestamp": str,  # ISO 8601 format
    "table": Optional[str],
    "database": Optional[str]
}
```

**Response:**
```python
{
    "verified": bool,
    "batch_id": Optional[str],
    "merkle_root": Optional[str],
    "blockchain_proof": {
        "network": str,
        "contract": str,
        "transaction_hash": str,
        "block_height": int
    },
    "error": Optional[str]
}
```

**Example Usage in Claude:**
```
User: "Verify that transaction TX-2025-01-15-123456 from this morning is on the blockchain"

Assistant uses verify_transaction tool with:
{
  "transaction_id": "TX-2025-01-15-123456",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### search_transactions

**Purpose:** Search for transactions matching criteria

**Parameters:**
```python
{
    "database": Optional[str],
    "table": Optional[str],
    "operation_type": Optional[Literal["INSERT", "UPDATE", "DELETE"]],
    "start_date": Optional[str],
    "end_date": Optional[str],
    "limit": Optional[int]
}
```

**Response:**
```python
{
    "transactions": List[{
        "transaction_id": str,
        "operation": str,
        "table": str,
        "timestamp": str,
        "batch_id": str,
        "verified": bool
    }],
    "total_count": int,
    "has_more": bool
}
```

### generate_compliance_report

**Purpose:** Generate audit compliance reports

**Parameters:**
```python
{
    "report_type": Literal["SOX", "GDPR", "HIPAA", "CUSTOM"],
    "start_date": str,
    "end_date": str,
    "databases": Optional[List[str]],
    "include_proofs": Optional[bool]
}
```

**Response:**
```python
{
    "report_id": str,
    "period": {
        "start": str,
        "end": str
    },
    "statistics": {
        "total_transactions": int,
        "total_batches": int,
        "databases_covered": List[str],
        "compliance_score": float
    },
    "findings": List[{
        "category": str,
        "status": Literal["PASS", "FAIL", "WARNING"],
        "details": str
    }],
    "blockchain_proofs": Optional[List[str]]
}
```

### analyze_integrity

**Purpose:** Analyze data integrity across time periods

**Parameters:**
```python
{
    "database": str,
    "table": Optional[str],
    "analysis_type": Literal["gaps", "anomalies", "patterns", "all"],
    "time_period": Literal["hour", "day", "week", "month", "custom"],
    "custom_start": Optional[str],
    "custom_end": Optional[str]
}
```

**Response:**
```python
{
    "analysis_id": str,
    "findings": {
        "gaps": Optional[List[{
            "start_time": str,
            "end_time": str,
            "expected_count": int,
            "actual_count": int
        }]],
        "anomalies": Optional[List[{
            "timestamp": str,
            "type": str,
            "description": str,
            "severity": Literal["low", "medium", "high"]
        }]],
        "patterns": Optional[{
            "peak_hours": List[str],
            "average_rate": float,
            "trend": Literal["increasing", "stable", "decreasing"]
        }]
    }
}
```

### get_cost_analysis

**Purpose:** Analyze blockchain and storage costs

**Parameters:**
```python
{
    "period": Literal["day", "week", "month", "year", "all"],
    "breakdown_by": Optional[Literal["database", "table", "operation"]],
    "currency": Optional[Literal["NEAR", "USD"]]
}
```

**Response:**
```python
{
    "period": str,
    "costs": {
        "blockchain": {
            "gas_used": str,
            "near_amount": str,
            "usd_equivalent": Optional[str]
        },
        "storage": {
            "s3_size_gb": float,
            "monthly_cost_usd": str
        },
        "total_usd": Optional[str]
    },
    "breakdown": Optional[List[{
        "category": str,
        "percentage": float,
        "cost": str
    }]],
    "recommendations": Optional[List[str]]
}
```

### MCP Configuration

```json
{
  "mcpServers": {
    "etrap": {
      "command": "python",
      "args": ["-m", "mcp_etrap.app"],
      "env": {
        "ETRAP_ORGANIZATION": "myorg",
        "ETRAP_NETWORK": "mainnet",
        "AWS_ACCESS_KEY_ID": "your-access-key",
        "AWS_SECRET_ACCESS_KEY": "your-secret-key",
        "AWS_DEFAULT_REGION": "us-west-2"
      }
    }
  }
}
```

---

## Appendix D: Error Codes Reference

### Error Code Structure

```
Format: EXXX
Categories:
- E1XXX: Validation Errors
- E2XXX: Blockchain Errors
- E3XXX: Database Errors
- E4XXX: Network Errors
- E5XXX: Authentication Errors
- E6XXX: System Errors
```

### Common Error Codes

| Code | Name | Description | HTTP Status | Retryable |
|------|------|-------------|-------------|-----------|
| E1001 | INVALID_TRANSACTION_ID | Transaction ID format invalid | 400 | No |
| E1002 | MISSING_TIMESTAMP | Timestamp required for search | 400 | No |
| E1003 | INVALID_BATCH_SIZE | Batch exceeds size limits | 400 | No |
| E2001 | MERKLE_VERIFICATION_FAILED | Proof doesn't match root | 400 | No |
| E2002 | NFT_ALREADY_EXISTS | Token ID already minted | 409 | No |
| E2003 | INSUFFICIENT_BALANCE | Not enough NEAR for fees | 402 | No |
| E2004 | CONTRACT_PAUSED | Contract temporarily paused | 503 | Yes |
| E3001 | DATABASE_CONNECTION_FAILED | Cannot connect to database | 500 | Yes |
| E3002 | CDC_LAG_EXCEEDED | CDC lag above threshold | 503 | Yes |
| E4001 | S3_UPLOAD_FAILED | Failed to store batch data | 500 | Yes |
| E4002 | NEAR_RPC_ERROR | Blockchain communication error | 503 | Yes |
| E5001 | INVALID_CREDENTIALS | Authentication failed | 401 | No |
| E5002 | INSUFFICIENT_PERMISSIONS | Not authorized for operation | 403 | No |
| E6001 | OUT_OF_MEMORY | System memory exhausted | 500 | Yes |
| E6002 | CONFIGURATION_ERROR | Invalid configuration | 500 | No |

### Error Response Format

```json
{
  "error": {
    "code": "E2001",
    "name": "MERKLE_VERIFICATION_FAILED",
    "message": "Merkle proof verification failed for transaction TX-123",
    "details": {
      "transaction_id": "TX-123",
      "batch_id": "BATCH-001",
      "expected_root": "5f3a8b2c...",
      "calculated_root": "7d865e95..."
    },
    "timestamp": "2025-01-15T10:30:45.123Z",
    "request_id": "req-456"
  }
}
```

---

## Appendix E: Configuration Reference

### Environment Variables

#### Core Configuration

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `ETRAP_ORG_ID` | Organization identifier | Yes | - |
| `ETRAP_ENV` | Environment (dev/staging/prod) | No | dev |
| `ETRAP_LOG_LEVEL` | Logging verbosity | No | INFO |

#### Database Configuration

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `POSTGRES_HOST` | PostgreSQL hostname | Yes | - |
| `POSTGRES_PORT` | PostgreSQL port | No | 5432 |
| `POSTGRES_USER` | Database user | Yes | - |
| `POSTGRES_PASSWORD` | Database password | Yes | - |
| `POSTGRES_DB` | Database name | Yes | - |

#### Redis Configuration

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `REDIS_HOST` | Redis hostname | Yes | - |
| `REDIS_PORT` | Redis port | No | 6379 |
| `REDIS_PASSWORD` | Redis password | No | - |
| `REDIS_DB` | Redis database number | No | 0 |

#### NEAR Configuration

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `NEAR_ACCOUNT` | NEAR account ID | Yes | - |
| `NEAR_NETWORK` | Network (testnet/mainnet) | No | testnet |
| `NEAR_CONTRACT` | Contract account ID | No | Same as NEAR_ACCOUNT |

#### AWS Configuration

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `AWS_ACCESS_KEY_ID` | AWS access key | Yes | - |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | Yes | - |
| `AWS_REGION` | AWS region | No | us-west-2 |
| `ETRAP_S3_BUCKET` | S3 bucket name | No | etrap-{org_id} |

#### Agent Configuration

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `BATCH_SIZE` | Max events per batch | No | 1000 |
| `BATCH_TIMEOUT` | Batch timeout (seconds) | No | 60 |
| `MIN_BATCH_SIZE` | Minimum batch size | No | 1 |
| `FORCE_BATCH_AFTER` | Force batch after (seconds) | No | 300 |

### Configuration File (etrap.yaml)

```yaml
# etrap.yaml - ETRAP Configuration File

organization:
  id: myorg
  name: "My Organization"
  
environment: production

database:
  host: ${POSTGRES_HOST}
  port: 5432
  user: ${POSTGRES_USER}
  password: ${POSTGRES_PASSWORD}
  database: ${POSTGRES_DB}
  ssl_mode: require

redis:
  host: ${REDIS_HOST}
  port: 6379
  password: ${REDIS_PASSWORD}
  
cdc:
  debezium:
    version: "2.5"
    connector: postgresql
    slot_name: etrap_slot
    publication_name: etrap_pub
    
  streams:
    pattern: "etrap.*"
    consumer_group: etrap-agent
    consumer_name: agent-${HOSTNAME}
    
agent:
  batching:
    size: 1000
    timeout: 60
    min_size: 1
    force_after: 300
    
  processing:
    workers: 4
    max_retries: 3
    retry_delay: 2
    
near:
  account: ${NEAR_ACCOUNT}
  network: mainnet
  contract: ${NEAR_CONTRACT}
  fee_amount: 0.01
  
aws:
  region: us-west-2
  s3:
    bucket: ${ETRAP_S3_BUCKET}
    storage_class: STANDARD_IA
    encryption: AES256
    
monitoring:
  prometheus:
    enabled: true
    port: 9090
    
  health_check:
    port: 8080
    path: /health
    
logging:
  level: INFO
  format: json
  outputs:
    - stdout
    - file: /var/log/etrap/agent.log
```

### Docker Compose Override

```yaml
# docker-compose.override.yml
# Local development overrides

version: '3.8'

services:
  etrap-agent:
    environment:
      - ETRAP_LOG_LEVEL=DEBUG
      - BATCH_SIZE=10
      - BATCH_TIMEOUT=10
    volumes:
      - ./cdc-agent:/app
      - ./test-data:/test-data
    ports:
      - "9090:9090"  # Prometheus metrics
      - "8080:8080"  # Health check
```

---

## Appendix F: ETRAP CLI Tools Reference

ETRAP provides several command-line tools for verification and analysis. These tools are located in different repositories based on their purpose.

### Primary CLI Tools

#### etrap_verify_sdk.py (SDK-based verification)

**Location:** `etrap-sdk/examples/etrap_verify_sdk.py`

**Purpose:** Primary verification tool using the ETRAP SDK

**Installation:**
```bash
cd etrap-sdk
pip install -e .
```

**Usage:**
```bash
# Basic transaction verification
python examples/etrap_verify_sdk.py \
    --organization myorg \
    --data '{"id": 123, "amount": "1000.00", "account_id": "ACC001"}' \
    --network testnet

# With optimization hints (faster verification)
python examples/etrap_verify_sdk.py \
    --organization myorg \
    --data '{"id": 123, "amount": "1000.00", "account_id": "ACC001"}' \
    --hint-batch-id BATCH-2025-01-15-001

# With time range hints
python examples/etrap_verify_sdk.py \
    --organization myorg \
    --data '{"id": 123, "amount": "1000.00", "account_id": "ACC001"}' \
    --hint-time-start "2025-01-15T10:00:00" \
    --hint-time-end "2025-01-15T11:00:00"

# JSON output for automation
python examples/etrap_verify_sdk.py \
    --organization myorg \
    --data '{"id": 123, "amount": "1000.00", "account_id": "ACC001"}' \
    --output-format json
```

**Key Features:**
- Operation disambiguation (INSERT/UPDATE/DELETE)
- Performance optimization with hints
- Comprehensive error reporting
- JSON and human-readable output
- Support for all SDK verification methods

#### validate_batch.py (Batch analysis and validation)

**Location:** `etrap/attic/validate_batch.py`

**Purpose:** Query and validate batches without table-specific knowledge

**Usage:**
```bash
# Show recent batches
python validate_batch.py --contract myorg.testnet --recent 10

# Search by database
python validate_batch.py --contract myorg.testnet --database etrapdb

# Search by time range (last 7 days)
python validate_batch.py --contract myorg.testnet --days 7

# Search by table
python validate_batch.py --contract myorg.testnet --table financial_transactions

# Get specific batch details
python validate_batch.py --contract myorg.testnet --batch-id BATCH-2025-01-15-001

# Download S3 data for a batch
python validate_batch.py --contract myorg.testnet --batch-id BATCH-2025-01-15-001 --download-s3

# Show statistics
python validate_batch.py --contract myorg.testnet --stats

# Interactive mode
python validate_batch.py --contract myorg.testnet --interactive
```

#### validate_transaction.py (Table-specific validation)

**Location:** `etrap/attic/validate_transaction.py`

**Purpose:** Validate specific transactions against NFT batches

**Usage:**
```bash
# Validate a financial transaction
python validate_transaction.py \
    --token-id BATCH-2025-01-15-001 \
    --account-id ACC500 \
    --amount 10000 \
    --type C

# Validate an audit log entry
python validate_transaction.py \
    --token-id BATCH-2025-01-15-002 \
    --table audit_logs \
    --operation INSERT
```

#### etrap_verify.py (Legacy verification tool)

**Location:** `etrap/attic/etrap_verify.py`

**Purpose:** Original verification tool with search capabilities

**Usage:**
```bash
# Search and verify transactions with WHERE clauses
python etrap_verify.py \
    --contract myorg.testnet \
    --database etrapdb \
    --table financial_transactions \
    --where "account_id=ACC500 AND amount>5000"

# Search with date filters
python etrap_verify.py \
    --contract myorg.testnet \
    --database etrapdb \
    --table financial_transactions \
    --after "7 days ago" \
    --before today \
    --where "amount>1000"

# Generate audit report
python etrap_verify.py \
    --contract myorg.testnet \
    --database etrapdb \
    --table financial_transactions \
    --where "account_id=ACC500" \
    --report

# Detailed verification info
python etrap_verify.py \
    --contract myorg.testnet \
    --database etrapdb \
    --table financial_transactions \
    --where "id=66" \
    --detailed
```

**Supported WHERE clause operators:**
- `=` Equal to
- `!=` Not equal to  
- `>` Greater than
- `<` Less than
- `>=` Greater than or equal
- `<=` Less than or equal
- `LIKE` Pattern matching (use % as wildcard)

**Examples:**
- `account_id=ACC500`
- `amount>5000`
- `reference LIKE '%deposit%'`
- `account_id=ACC500 AND amount>1000 AND type=C`

### SDK Example Tools

#### list_batches.py

**Location:** `etrap-sdk/examples/list_batches.py`

**Purpose:** List and analyze batches using the SDK

#### debug_batch.py

**Location:** `etrap-sdk/examples/debug_batch.py`

**Purpose:** Debug and analyze specific batch structures

#### basic_usage.py

**Location:** `etrap-sdk/examples/basic_usage.py`

**Purpose:** Basic SDK usage examples and patterns

### Environment Configuration

All tools require proper environment setup:

```bash
# NEAR configuration
export NEAR_ACCOUNT="myorg.testnet"
export NEAR_NETWORK="testnet"  # or "mainnet"

# AWS configuration (for S3 access)
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_DEFAULT_REGION="us-west-2"

# Optional: ETRAP organization (for SDK tools)
export ETRAP_ORGANIZATION="myorg"
```

### Output Formats

#### Text Format (Default)
```
✅ Transaction Verified

Transaction Details:
├── ID: 123
├── Account: ACC001
├── Amount: 1000.00
└── Operation: INSERT

Blockchain Proof:
├── Batch ID: BATCH-2025-01-15-001
├── Merkle Root: 0x5f3a8b2c7d9e1a4b...
├── NEAR Block: 142,857,000
└── Verification: VALID ✓
```

#### JSON Format
```json
{
  "verified": true,
  "transaction_hash": "7d865e959b2466918c...",
  "batch_id": "BATCH-2025-01-15-001",
  "merkle_proof": {
    "leaf_hash": "7d865e959b2466918c...",
    "proof_path": ["...", "..."],
    "merkle_root": "5f3a8b2c7d9e1a4b...",
    "is_valid": true
  },
  "blockchain_timestamp": "2025-01-15T10:30:00.123Z",
  "operation_type": "INSERT"
}
```

### Performance Optimization

1. **Use Specific Tools**: Choose the right tool for your use case
2. **Provide Hints**: Use batch_id or time_range hints when available
3. **Narrow Searches**: Use specific databases, tables, or WHERE clauses
4. **Cache Results**: Tools cache blockchain queries locally

### Error Handling

Tools provide clear error messages and appropriate exit codes:

```bash
# Transaction not found
❌ Error: Transaction not found in any batch for the specified criteria

# Network connectivity
❌ Error: Cannot connect to NEAR network (testnet)
   Check your internet connection and NEAR_NETWORK setting

# Missing configuration
❌ Error: AWS credentials not configured
   Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables
```

### Integration Examples

#### Automated Verification Script
```bash
#!/bin/bash
# daily_verification.sh

# Get yesterday's transactions from your database
TRANSACTIONS=$(your_db_query "SELECT id, amount, account_id FROM transactions WHERE date = yesterday()")

# Verify each transaction
echo "$TRANSACTIONS" | while IFS=',' read id amount account; do
    python etrap-sdk/examples/etrap_verify_sdk.py \
        --organization myorg \
        --data "{\"id\": $id, \"amount\": \"$amount\", \"account_id\": \"$account\"}" \
        --output-format json > verification_$id.json
    
    if [ $? -eq 0 ]; then
        echo "✅ Transaction $id verified"
    else
        echo "❌ Transaction $id failed verification"
    fi
done
```

#### Batch Analysis Pipeline
```python
#!/usr/bin/env python3
# analyze_daily_batches.py

import subprocess
import json
from datetime import datetime, timedelta

# Get yesterday's batches
yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

result = subprocess.run([
    'python', 'validate_batch.py',
    '--contract', 'myorg.testnet',
    '--date', yesterday,
    '--format', 'json'
], capture_output=True, text=True)

if result.returncode == 0:
    batches = json.loads(result.stdout)
    
    for batch in batches:
        print(f"Batch {batch['batch_id']}: {batch['tx_count']} transactions")
        
        # Detailed analysis
        subprocess.run([
            'python', 'validate_batch.py',
            '--contract', 'myorg.testnet',
            '--batch-id', batch['batch_id'],
            '--download-s3'
        ])
```

---

## Conclusion

ETRAP represents a paradigm shift in enterprise audit trail management, combining the reliability of traditional databases with the immutability of blockchain technology. By ensuring that no sensitive data ever leaves customer premises while still providing cryptographic proof of integrity, ETRAP meets the strictest compliance requirements while maintaining complete data sovereignty.

The platform's modular architecture, comprehensive APIs, and integration capabilities make it suitable for organizations of any size, from startups to global enterprises. As regulatory requirements continue to evolve and data integrity becomes increasingly critical, ETRAP provides the foundation for trustworthy, verifiable, and compliant data management.

For more information, visit the GitHub repositories or contact Graziano Labs Corp.

---

**Copyright © 2025 Graziano Labs Corp. All rights reserved.**