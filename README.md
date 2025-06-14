# ETRAP CDC Agent - Enterprise Transaction Recording and Audit Platform

A production-ready Change Data Capture (CDC) agent that creates immutable audit trails on the NEAR blockchain, providing cryptographic proof of database transactions for regulatory compliance and legal proceedings.

## 🚀 Key Features

- **Real-time CDC**: Captures all database changes via Debezium/Redis
- **Blockchain Anchoring**: Creates NFTs on NEAR blockchain with Merkle roots
- **Cryptographic Verification**: Proves specific transactions occurred with Merkle proofs
- **Privacy Compliant**: No transaction data leaves your premises
- **Generic Architecture**: Works with any PostgreSQL database schema
- **Regulatory Compliance**: Court-admissible transaction proofs
- **Pure Verification Model**: You provide data, we prove authenticity

## 📋 Components

### 1. CDC Agent (`etrap_cdc_agent.py`)
Captures database changes and creates blockchain-backed audit trails:
- Consumes CDC events from Redis streams
- Intelligent batching for efficiency
- Merkle tree generation
- S3 storage for detailed data
- NFT minting on NEAR

### 2. Transaction Verifier (`etrap_verify.py`)
Verifies transactions without exposing data:
- Pure verification model (you provide data to verify)
- Cryptographic proof using Merkle trees
- Shows blockchain recording timestamp
- Privacy compliant (no data search)
- Audit-ready output formats

## 🛠️ Installation

```bash
# Clone the repository
git clone https://github.com/marcoeg/etrap-cdc-agent.git
cd etrap-cdc-agent

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

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

## 📖 Usage

### Running the CDC Agent

```bash
python etrap_cdc_agent.py
```

### Verifying Transactions

```bash
# Verify a specific transaction
python etrap_verify.py -c acme.testnet --data '{
  "id": 123,
  "account_id": "ACC500",
  "amount": 10000.00,
  "type": "C"
}'

# Verify from database export
python etrap_verify.py -c acme.testnet --data-file transaction.json

# Quick verification (quiet mode)
python etrap_verify.py -c acme.testnet --data-file tx.json --quiet
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

- [CDC Agent Documentation](README_CDC.md)
- [Transaction Verifier Guide](README_etrap_verify.md)
- [Implementation Summary](summary.txt)

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