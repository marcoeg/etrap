# ETRAP
ETRAP (Enterprise Transaction Receipt Anchoring Platform) is a blockchain-based service that creates immutable "receipts" for enterprise database transactions, providing proof of integrity, non-repudiation, and regulatory compliance.

ETRAP (Enterprise Transaction Receipt Anchoring Platform) is a blockchain-based audit trail system
that captures database changes and creates immutable proofs on the NEAR blockchain. The system
combines the reliability of traditional databases with the immutability of blockchain technology,
creating a tamper-proof audit trail for regulatory compliance and data integrity verification.

The pipeline consists of six key stages:
1. Database changes captured by PostgreSQL (on-premises)
2. Change Data Capture (CDC) via Debezium (on-premises)
3. Event streaming through Redis (on-premises)
4. Intelligent batching by the ETRAP CDC Agent (on-premises)
5. Metadata and hash storage in AWS S3 (cloud - no sensitive data)
6. Immutable hash anchoring NFT on NEAR blockchain (public - no sensitive data)


## Key Features

- **Real-time CDC**: Captures all database changes via Debezium/Redis
- **Blockchain Anchoring**: Creates NFTs on NEAR blockchain with Merkle roots
- **Cryptographic Verification**: Proves specific transactions occurred with Merkle proofs
- **Privacy Compliant**: No transaction data leaves your premises
- **Generic Architecture**: Works with any PostgreSQL database schema
- **Regulatory Compliance**: Court-admissible transaction proofs
- **Pure Verification Model**: You provide data, we prove authenticity
- **CLI for Verification**: Simple and intuitive interface for verifying transactions
- **Python SDK**: Python SDK for ETRAP with integration examples


Critical Privacy Feature: No actual transaction data ever leaves the customer's premises. Only
cryptographic hashes and metadata are stored externally (S3 and blockchain), ensuring complete data
sovereignty and compliance with the strictest privacy regulations.

## 📋 Components in this repo

### 1. CDC Agent (`etrap_cdc_agent.py`) - Enterprise Transaction Recording and Audit Platform


A production-ready Change Data Capture (CDC) agent that creates immutable audit trails on the NEAR blockchain, providing cryptographic proof of database transactions for regulatory compliance and legal proceedings.

Captures database changes and creates blockchain-backed audit trails:
- Consumes CDC events from Redis streams
- Intelligent batching for efficiency
- Merkle tree generation
- S3 storage for detailed data
- NFT minting on NEAR

> Transaction verification is done using the `etrap-sdk` in 


## 🛠️ Installation

```bash
# Clone the repository
git clone https://github.com/marcoeg/etrap.git
cd etrap
```
## Workflow

The complete ETRAP deployment workflow is now:

  1. PostgreSQL Setup: ./docker/setup-postgresql.sh (configure CDC)
  2. NEAR Onboarding: ./onboard_organization.sh (create account/contract)
  3. Docker Generation: ./generate_etrap_docker.sh (create containers)
  4. Deployment: docker-compose up -d (run services)



## ⚙️ Configuration

### Environment Variables

```bash
# NEAR Configuration
export NEAR_ACCOUNT=your-account.testnet
export NEAR_ENV=testnet

# AWS Configuration
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret
export AWS_DEFAULT_REGION=us-east-1

# ETRAP Configuration
export ETRAP_S3_BUCKET=etrap-your-org
export ETRAP_ORG_ID=your-org
```


## 📊 Architecture

```
PostgreSQL → Debezium → Redis → CDC Agent → S3 & NEAR Blockchain
                                     ↓
                              Transaction Verifier
                                     ↓
                              Audit Reports
```

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

## 📄 Copyright


This project is proprietary.

Copyright (c) 2025 Graziano Labs Corp. All rights reserved.


## 🏢 Use Cases

- Financial transaction auditing
- Regulatory compliance (SOX, GDPR)
- Legal dispute resolution
- Access control auditing
- Data integrity verification

## 🚧 Future Enhancements

- PDF report generation
- Real-time alerting
- Multi-database federation
- UPDATE/DELETE operation tracking
- Web-based verification portal

## 📧 Contact

For questions or support, please open an issue in the GitHub repository.

---

Built with ❤️ for enterprise compliance and transparency