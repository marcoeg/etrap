# ETRAP Transaction Verification Tool

## Overview

`etrap_verify.py` is a privacy-compliant verification tool that proves specific database transactions exist in the blockchain-backed audit trail without exposing or searching through sensitive data. 

This tool implements a **pure verification model**: you provide the complete transaction data, and it cryptographically proves whether that exact transaction was recorded on the blockchain.

## Key Features

- 🔐 **Cryptographic Verification**: Proves transactions using Merkle proofs
- 🔒 **Privacy Compliant**: No transaction data leaves your premises or is stored in the cloud
- 📅 **Blockchain Timestamps**: Shows the undisputable time when data was recorded
- 🚀 **Simple Interface**: Just provide the transaction data to verify
- 🎯 **Audit-Focused**: Designed for regulatory compliance and legal proceedings

## How It Works

1. **You provide**: Complete transaction data (from your database export)
2. **Tool computes**: Deterministic hash of the transaction
3. **Searches**: Recent blockchain batches for matching hash
4. **Verifies**: Merkle proof to ensure transaction integrity
5. **Returns**: Blockchain timestamp and cryptographic proof

## Installation

```bash
# Prerequisites
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set AWS credentials for S3 access
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-east-1
```

## Usage

### Basic Verification

```bash
# Verify using exact database values (automatic normalization)
./etrap_verify.py -c acme.testnet --data '{
  "id": 109,
  "account_id": "ACC999",
  "amount": 999.99,
  "type": "C",
  "created_at": "2025-06-14 07:10:55.461133",
  "reference": "TEST-VERIFY"
}'

# The tool automatically handles:
# - Numeric amounts: 999.99 → "999.99"
# - Timestamp separators: "2025-06-14 07:10:55" → "2025-06-14T07:10:55"
# - Timestamp precision: 6 decimal places → 3 decimal places

# You can also provide pre-normalized data
./etrap_verify.py -c acme.testnet --data '{
  "id": 109,
  "account_id": "ACC999",
  "amount": "999.99",
  "type": "C",
  "created_at": "2025-06-14T07:10:55.461",
  "reference": "TEST-VERIFY"
}'

# Verify from a file
./etrap_verify.py -c acme.testnet --data-file transaction.json

# Verify from stdin (great for piping from SQL query)
echo '{"id":109,"account_id":"ACC999","amount":999.99,"type":"C","created_at":"2025-06-14 07:10:55.461133","reference":"TEST-VERIFY"}' | ./etrap_verify.py -c acme.testnet --data -
```

### Data Format Normalization

The verification tool automatically normalizes your input data to match how the CDC agent processes it:

| Field Type | Database Format | Normalized Format | Notes |
|------------|----------------|-------------------|-------|
| **Amounts** | `999.99` (number) | `"999.99"` (string) | Numeric values converted to strings |
| **Timestamps** | `2025-06-14 07:10:55` | `2025-06-14T07:10:55` | Space replaced with 'T' separator |
| **Precision** | `.461133` (6 decimals) | `.461` (3 decimals) | Microseconds truncated to milliseconds |
| **No decimals** | `07:10:55` | `07:10:55.000` | Missing milliseconds added as .000 |

**Examples:**
```sql
-- Query your database
SELECT * FROM financial_transactions WHERE id = 109;
-- Returns: 109|ACC999|999.99|C|2025-06-14 07:10:55.461133|TEST-VERIFY

-- Copy the exact values for verification - no manual formatting needed!
```

### Optimization Hints

For faster verification, provide hints about where to look:

```bash
# Hint: specific table
./etrap_verify.py -c acme.testnet --data-file tx.json --hint-table financial_transactions

# Hint: specific batch ID (if known)
./etrap_verify.py -c acme.testnet --data-file tx.json --hint-batch BATCH-2025-06-14-abc123

# Hint: database name
./etrap_verify.py -c acme.testnet --data-file tx.json --hint-database production_db
```

### Output Formats

```bash
# Default: Human-readable output
./etrap_verify.py -c acme.testnet --data-file tx.json

# JSON output (for automation)
./etrap_verify.py -c acme.testnet --data-file tx.json --json

# Quiet mode (just VERIFIED or NOT_VERIFIED)
./etrap_verify.py -c acme.testnet --data-file tx.json --quiet
```

## Example Output

### Successful Verification

```
🔐 ETRAP Transaction Verification Tool
   Contract: acme.testnet
   Network: testnet

🔍 ETRAP Transaction Verification
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Transaction Hash: 7d865e959b2466918c9863afca942d0f...

🔎 Searching recent batches...
   Found 25 recent batches to check
   Found in batch 3 of 25

✅ TRANSACTION VERIFIED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📄 Transaction Details:
   Hash: 7d865e959b2466918c9863afca942d0f...
   Operation: INSERT
   Database: etrapdb
   Table: financial_transactions

🔗 Blockchain Record:
   NFT Token ID: BATCH-2025-06-14-8ad04ff5
   Contract: acme.testnet
   Network: testnet
   Merkle Root: 82fc5cd323d178dcf2737e44b0358aa8...

⏰ Recorded on Blockchain:
   2025-06-14 00:54:15 UTC
   This is the official timestamp when this batch was
   permanently recorded on the NEAR blockchain.

🔐 Cryptographic Proof:
   Proof Height: 3 levels
   Merkle Tree Nodes: 15
   Position in Tree: 7

💾 Audit Trail Location:
   S3 Bucket: etrap-acme
   S3 Path: etrapdb/financial_transactions/BATCH-2025-06-14-8ad04ff5/

📊 Search Statistics:
   Batches searched: 3
   Found in: BATCH-2025-06-14-8ad04ff5

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ This transaction is cryptographically proven to have existed
   in the database at the time of blockchain recording.
   Any tampering would invalidate this proof.
```

### Failed Verification

```
❌ TRANSACTION NOT VERIFIED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📄 Transaction Hash: abc123def456...

🔍 Search Results:
   Batches searched: 100
   Status: Transaction not found in recent batches

⚠️  Possible reasons:
   • Transaction may not have been captured yet
   • Transaction data may have been modified
   • Transaction may be in older batches (try --all-batches)
   • The database may not be configured for ETRAP
```

## Use Cases

### 1. Audit Verification

Auditors can verify transactions from database exports:

```bash
# Export transaction from database
psql -c "SELECT * FROM financial_transactions WHERE id=84" -t -A -F',' > tx.json

# Verify it hasn't been tampered with
./etrap_verify.py -c company.testnet --data-file tx.json
```

### 2. Legal Proceedings

Provide cryptographic proof for court:

```bash
# Verify disputed transaction
./etrap_verify.py -c company.testnet --data-file disputed_transaction.json --json > proof.json

# The proof.json contains all cryptographic evidence
```

### 3. Compliance Reporting

Verify reported transactions are authentic:

```bash
# Verify each transaction in a compliance report
for tx in transactions/*.json; do
    echo "Verifying $tx..."
    ./etrap_verify.py -c company.testnet --data-file "$tx" --quiet || echo "FAILED: $tx"
done
```

### 4. Data Integrity Checks

Ensure backups match original data:

```bash
# Compare backup data against blockchain
./etrap_verify.py -c company.testnet --data '{"id":123,...}' --quiet && echo "Backup valid"
```

## Privacy & Security

### What This Tool Does NOT Do

- ❌ Does NOT search through transaction data
- ❌ Does NOT store or transmit sensitive data
- ❌ Does NOT require access to your database
- ❌ Does NOT expose business information

### What This Tool DOES Do

- ✅ Computes hash of data you provide
- ✅ Searches only for hash matches
- ✅ Downloads only hash trees from S3
- ✅ Provides mathematical proof

### Data Flow

```
Your Data (Local) → Hash → Search Blockchain → Verify Proof
     ↓                                              ↓
 Stays Local                                 Public Hashes Only
```

## Understanding Timestamps

The tool shows the **blockchain timestamp** - when the batch was permanently recorded on NEAR. This is:

- **Undisputable**: Cannot be forged or altered
- **Authoritative**: The legal proof-of-existence time
- **May differ**: From timestamps in your transaction data

Example:
- Transaction timestamp: `2025-06-14 00:53:56` (from your data)
- Blockchain timestamp: `2025-06-14 00:54:15` (when recorded)

The blockchain timestamp proves the transaction existed **at or before** that time.

## Troubleshooting

### "Transaction not verified"

1. **Check data format**: Ensure JSON exactly matches database export
2. **Wait for batching**: Recent transactions may not be batched yet
3. **Try hints**: Use `--hint-table` for faster/deeper search
4. **Check older batches**: Transaction may be outside recent window

### "Error fetching from S3"

1. Check AWS credentials are set
2. Verify S3 bucket permissions
3. Ensure batch was properly uploaded

### Slow verification

1. Use `--hint-table` to narrow search
2. Use `--hint-batch` if you know the batch ID
3. Recent transactions are found faster

## Integration Examples

### Python Script

```python
import subprocess
import json

def verify_transaction(contract_id, transaction_data):
    cmd = [
        './etrap_verify.py',
        '-c', contract_id,
        '--data', json.dumps(transaction_data),
        '--json'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        return json.loads(result.stdout)
    else:
        raise Exception(f"Verification failed: {result.stderr}")

# Usage
tx_data = {"id": 123, "account_id": "ACC500", ...}
proof = verify_transaction('acme.testnet', tx_data)
print(f"Verified: {proof['verified']}")
```

### Bash Script

```bash
#!/bin/bash
# Verify all transactions in a directory

CONTRACT="acme.testnet"
TX_DIR="./transactions"
FAILED=0

for tx_file in "$TX_DIR"/*.json; do
    if ./etrap_verify.py -c "$CONTRACT" --data-file "$tx_file" --quiet; then
        echo "✓ $(basename "$tx_file")"
    else
        echo "✗ $(basename "$tx_file")"
        FAILED=$((FAILED + 1))
    fi
done

echo "Failed verifications: $FAILED"
exit $FAILED
```

## Best Practices

1. **Exact Data**: Ensure transaction data exactly matches database export
2. **Deterministic JSON**: Use sorted keys, consistent formatting
3. **Timezone Awareness**: Be consistent with timestamp formats
4. **Batch Processing**: Verify multiple transactions efficiently
5. **Audit Trail**: Save verification results for compliance

## Limitations

- **Recent Batches**: By default searches only recent batches (last ~100)
- **No Data Search**: Cannot search by account ID, amount, etc.
- **Requires Full Data**: Need complete transaction, not partial fields
- **Batch Timing**: Very recent transactions may not be batched yet

## Exit Codes

- `0`: Transaction verified successfully
- `1`: Transaction not verified or error occurred

## See Also

- [CDC Agent Documentation](README_CDC.md) - How transactions are captured
- [Smart Contract API](contract_api.md) - Blockchain query methods
- [Architecture Overview](README.md) - System design

---

For support or questions, please open an issue in the GitHub repository.