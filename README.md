# ETRAP

ETRAP (Enterprise Transaction Receipt Anchoring Platform) is a blockchain-based audit trail platform 
that captures database changes and creates immutable proofs on the NEAR blockchain. The platform 
combines the reliability of traditional databases with the immutability of blockchain technology, 
creating a tamper-proof audit trail for regulatory compliance and data integrity verification

The platform consists of four main components operating in a secure pipeline: first, PostgreSQL database changes are captured by Debezium CDC (Change Data Capture) and streamed through Redis, all running on-premises within the customer's infrastructure. The ETRAP CDC Agent then consumes these events, strips all sensitive data, creates cryptographic hashes, and builds Merkle trees from batches of transactions. Only these hashes and metadata are sent externally to AWS S3 for detailed storage and to the NEAR blockchain where they're minted as NFTs, creating an immutable timestamp and proof of existence. 

> *Origin of the name. The Greek word "έτραπ" (etrap) is the strong aorist active form of the verb "τρέπω" (trepo) meaning "to turn" or "to change direction" - which is quite fitting for a platform that tracks database changes and transformations.*

## 🏗️ Architecture
```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌─────────────────────────┐
│  PostgreSQL  │ ──> │  Debezium    │ ──> │    Redis     │ ──> │   ETRAP CDC AGENT       │
│  Database    │     │     CDC      │     │   Streams    │     │  - Hashing              │
│  (On-Prem)   │     │  (On-Prem)   │     │  (On-Prem)   │     │  - Merkle Tree          │
└──────────────┘     └──────────────┘     └──────────────┘     │  - Batch Metadata       │
                                                               └────────────┬────────────┘
                                                                            │ 
                              ┌─────────────────────────────────────────────┤
                              ▼                                             ▼
                     ┌────────────────────┐                        ┌────────────────────┐
                     │    AWS S3          │                        │   NEAR Blockchain  │
                     │  - Hashes          │                        │  - NFT Token       │
                     │  - Merkle Tree     │                        │  - Merkle Root     │
                     │  - Metadata        │                        │  - Timestamp       │
                     └────────────────────┘                        └────────────────────┘
```
This hybrid architecture ensures complete data sovereignty—no actual transaction data ever leaves the customer's premises—while still providing court-admissible blockchain proof of data integrity, making it ideal for regulatory compliance in financial services, healthcare, and government sectors where data privacy is paramount.

## ✨Key Features

- **Real-time CDC**: Captures all database changes via Debezium/Redis
- **Blockchain Anchoring**: Creates NFTs on NEAR blockchain with Merkle roots
- **Cryptographic Verification**: Proves specific transactions occurred with Merkle proofs
- **Privacy Compliant**: No transaction data leaves your premises
- **Generic Architecture**: Works with any PostgreSQL database schema
- **Regulatory Compliance**: Court-admissible transaction proofs
- **Pure Verification Model**: You provide data, we prove authenticity
- **CLI for Verification**: Simple and intuitive interface for verifying transactions
- **Python SDK**: Python SDK for ETRAP with integration examples

For detailed design documentation check the [ETRAP Design Document](etrap-design-document.md)

## 📋 Components in this repo

### 1. Infrastructure 

Each customer organization gets their own containerized deployment that includes:
- **Debezium Server** - Captures PostgreSQL database changes via CDC
- **Redis Server** - Streams CDC events for processing
- **ETRAP CDC Agent** - Processes events and creates blockchain proofs on NEAR Protocol 

The containerized infrastructure reference deployment is in the `./docker` directory of this repo. 

[Generating ETRAP docker containers](./docker/README.md)

>The reference infrastructure is based on PostgreSQL. Since Debezium can capture changes in a variety of databases, it
can easily adapted to other databases.

### 2. ETRAP CDC Agent 

A production-ready Change Data Capture (CDC) agent that creates immutable audit trails on the NEAR blockchain, providing cryptographic proof of database transactions for regulatory compliance and legal proceedings.

Python code is in the `cdc-agent` directory.

Captures database changes and creates blockchain-backed audit trails:
- Consumes CDC events from Redis streams
- Intelligent batching for efficiency
- Merkle tree generation
- S3 storage for metadata
- NFT minting on NEAR

[ETRAP CDC Agent Documentation](./cdc-agent/README_CDC.md)

> Verification of transactions may be done with the read-only `etrap_verify_sdk.py` utility in the ETRAP [Python SDK repo](https://github.com/marcoeg/etrap-sdk). 

## ETRAP Repos
Other relevant repos are:

- [ETRAP NEAR Smart Contract](https://github.com/marcoeg/etrap-notary)
- [ETRAP Python SDK (includes verification CLI)](https://github.com/marcoeg/etrap-sdk)

## 🛠️ Installation

### Complete Setup Process

The ETRAP deployment requires completing these components:

**Prerequisites (can be done in parallel):**
1. **PostgreSQL Setup** - Configure database for Change Data Capture (CDC)
2. **NEAR Setup** - Deploy blockchain components

**Final Step (requires both prerequisites):**
3. **Docker Setup** - Generate and deploy containers

All commands should be run from the main ETRAP directory:

```bash
# 1. PostgreSQL Setup (database team can do this)
./docker/setup-postgresql.sh \
  --database etrapdb \
  --debezium-user debezium \
  --debezium-password your_secure_password \
  --execute

# 2. NEAR Setup (blockchain team can do this in parallel)
./onboard_organization.sh \
  --organization-name "Your Organization" \
  --organization-id "yourorg" \
  --near-network testnet

# 3. Docker Generation (requires steps 1 & 2 complete)
./generate_etrap_docker.sh \
  --organization-name "Your Organization" \
  --organization-id "yourorg" \
  --postgres-host "your-db-host" \
  --postgres-database "etrapdb" \
  --postgres-username "debezium" \
  --postgres-password "your_secure_password" \
  --near-network "testnet" \
  --aws-access-key-id "AKIA..." \
  --aws-secret-access-key "xyz..."
```

### Detailed Documentation

- [PostgreSQL Setup Guide](./docker/README.md#postgresql-setup) - Database configuration for CDC
- [NEAR Onboarding Guide](./onboarding.md) - Blockchain account and smart contract deployment
- [Docker Container Guide](./docker/README.md) - Container generation and deployment


## 🔒 Security

- Sensitive data stored in private S3 buckets
- Only hashes and metadata on public blockchain
- AWS IAM for access control
- Read-only verification tools

## 📝 Documentation

- [Onboarding a new organization](./onboarding.md)
- [Generating ETRAP docker](./docker/README.md)
- [CDC Agent Documentation](./cdc-agent/README_CDC.md)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.


## 🪪 License

MIT. See `./LICENSE`


## 📄 Copyright

Copyright (c) 2025 Graziano Labs Corp. All rights reserved.


## 📧 Contact

For questions or support, please open an issue in the GitHub repository.

---
