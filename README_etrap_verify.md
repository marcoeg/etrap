# ETRAP Transaction Search and Verification Tool

## Overview

`etrap_verify.py` is the core verification tool of the ETRAP (Enterprise Transaction Recording and Audit Platform) system. It enables searching for specific database transactions and provides cryptographic proof of their existence on the NEAR blockchain.

This tool fulfills ETRAP's primary mission: **proving that specific business transactions actually occurred**, with blockchain-backed evidence suitable for regulatory compliance, audits, and legal proceedings.

## Key Features

- 🔍 **Flexible Transaction Search**: Search any database table without knowing the schema
- 🔐 **Cryptographic Verification**: Verify transactions using Merkle proofs anchored on blockchain
- 📊 **Complex Queries**: Support for WHERE clauses with multiple conditions and operators
- 📅 **Time-Based Searches**: Find transactions within specific date ranges
- 📄 **Audit Reports**: Generate court-admissible verification reports
- 🏢 **Enterprise Ready**: Designed for compliance, regulatory, and legal use cases

## Installation

### Prerequisites

- Python 3.7+
- AWS credentials (for S3 access)
- NEAR testnet/mainnet access (no account needed for verification)

### Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Linux/Mac
# or
venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt
```

### Environment Variables (Optional)

```bash
# Only needed for S3 access
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-east-1  # or your region
```

## Usage

### Basic Syntax

```bash
python etrap_verify.py --contract <CONTRACT_ID> --database <DB_NAME> [options]
```

### Required Arguments

- `-c, --contract`: NEAR contract ID (e.g., `acme.testnet`)
- `-d, --database`: Database name to search

### Optional Arguments

- `-t, --table`: Specific table name (searches all tables if omitted)
- `-w, --where`: WHERE clause conditions
- `--after`: Start time for search range
- `--before`: End time for search range
- `--date`: Search specific date
- `--report`: Generate audit report file
- `--detailed`: Show detailed verification information
- `-n, --network`: NEAR network (default: testnet)

## Examples

### 1. Find High-Value Transactions

```bash
# Find all transactions over $10,000 for account ACC500
python etrap_verify.py -c acme.testnet -d etrapdb -t financial_transactions \
    -w "account_id=ACC500 AND amount>10000"
```

### 2. Search by Time Range

```bash
# Find transactions from the last 7 days
python etrap_verify.py -c acme.testnet -d etrapdb -t financial_transactions \
    --after "7 days ago" -w "type=C"

# Find transactions from specific date range
python etrap_verify.py -c acme.testnet -d etrapdb \
    --after "2024-01-01" --before "2024-01-31" -w "amount>5000"

# Find yesterday's audit logs
python etrap_verify.py -c acme.testnet -d etrapdb -t audit_logs \
    --date yesterday
```

### 3. Complex Queries

```bash
# Multiple conditions with AND
python etrap_verify.py -c acme.testnet -d etrapdb -t financial_transactions \
    -w "account_id=ACC500 AND amount>=1000 AND type=C"

# Pattern matching with LIKE
python etrap_verify.py -c acme.testnet -d etrapdb -t financial_transactions \
    -w "reference LIKE '%deposit%' AND amount>5000"

# Not equal operator
python etrap_verify.py -c acme.testnet -d etrapdb -t audit_logs \
    -w "operation!=DELETE AND user_id=admin"

# OR conditions - find transactions from multiple accounts
python etrap_verify.py -c acme.testnet -d etrapdb -t financial_transactions \
    -w "account_id=ACC500 OR account_id=ACC600 OR account_id=ACC700"

# Complex OR with AND - high value transactions OR specific account credits
python etrap_verify.py -c acme.testnet -d etrapdb -t financial_transactions \
    -w "amount>50000 OR (account_id=ACC500 AND type=C)"
```

### 4. Generate Audit Reports

```bash
# Generate JSON audit report
python etrap_verify.py -c acme.testnet -d etrapdb -t financial_transactions \
    -w "account_id=ACC500" --after "30 days ago" --report

# Output: ./reports/etrap_audit_report_YYYYMMDD_HHMMSS.json
```

### 5. Cross-Table Searches

```bash
# Search all tables for specific user activity
python etrap_verify.py -c acme.testnet -d etrapdb \
    --after "7 days ago" -w "user_id=john.doe"
```

## WHERE Clause Syntax

### Supported Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `=` | Equal to | `account_id=ACC500` |
| `!=` | Not equal to | `status!=CANCELLED` |
| `>` | Greater than | `amount>1000` |
| `<` | Less than | `amount<10000` |
| `>=` | Greater than or equal | `amount>=5000` |
| `<=` | Less than or equal | `amount<=20000` |
| `LIKE` | Pattern matching | `reference LIKE '%deposit%'` |

### Combining Conditions

Use `AND` to combine multiple conditions within a group:
```
account_id=ACC500 AND amount>1000 AND type=C
```

Use `OR` to match any of multiple condition groups:
```
account_id=ACC500 OR account_id=ACC600
amount>10000 OR (account_id=ACC500 AND type=C)
```

**Note**: OR has lower precedence than AND. Conditions are evaluated as groups of AND conditions joined by OR.

## Time Expressions

### Relative Time

- `N days ago` - N days before now
- `N hours ago` - N hours before now
- `N minutes ago` - N minutes before now
- `yesterday` - Yesterday at 00:00
- `today` - Today at 00:00

### Absolute Dates

Supported formats:
- `YYYY-MM-DD` (e.g., `2024-01-15`)
- `YYYY/MM/DD` (e.g., `2024/01/15`)
- `DD-MM-YYYY` (e.g., `15-01-2024`)
- `DD/MM/YYYY` (e.g., `15/01/2024`)

## Output Format

### Console Output

```
🎫 Transaction: BATCH-2025-06-14-776e2080-T0-0
✅ Status: VERIFIED on blockchain

📋 Transaction Details:
   Database: etrapdb
   Table: financial_transactions
   Operation: INSERT
   Timestamp: 2025-06-13 17:08:05

📊 Data:
   account_id: ACC500
   amount: 10000.0
   type: C
   reference: Large deposit - verification required

🔗 Blockchain Proof:
   NFT Token: BATCH-2025-06-14-776e2080-T0
   Contract: acme.testnet
   Network: testnet
   Merkle Root: e32d4c0d37240788...
```

### Audit Report Format

```json
{
  "report_id": "ETRAP-AUDIT-20250613-173631",
  "generated_at": "2025-06-13T17:36:31.820231",
  "query_parameters": {
    "database": "etrapdb",
    "table": "financial_transactions",
    "where_clause": "account_id=ACC500",
    "start_time": "2025-06-01T00:00:00",
    "end_time": "2025-06-13T23:59:59"
  },
  "contract": {
    "address": "acme.testnet",
    "network": "testnet"
  },
  "summary": {
    "total_matches": 5,
    "all_verified": true,
    "batches_involved": 2
  },
  "transactions": [...]
}
```

## Use Cases

### 1. Regulatory Compliance

Prove transactions for regulatory audits:
```bash
# Find all transactions over regulatory threshold
python etrap_verify.py -c bank.near -d core_banking \
    -t wire_transfers -w "amount>10000" \
    --after "2024-01-01" --before "2024-12-31" --report
```

### 2. Dispute Resolution

Verify specific disputed transactions:
```bash
# Verify a specific transaction ID
python etrap_verify.py -c company.near -d production \
    -t orders -w "order_id=ORD-2024-1234"
```

### 3. Access Auditing

Track who accessed sensitive data:
```bash
# Find all accesses to patient records
python etrap_verify.py -c hospital.near -d medical_db \
    -t audit_logs -w "table_name=patient_records AND operation=SELECT" \
    --after "7 days ago"
```

### 4. Financial Reconciliation

Verify financial transactions for reconciliation:
```bash
# Find all deposits for an account in a month
python etrap_verify.py -c bank.near -d transactions \
    -t deposits -w "account_number=123456789 AND type=DEPOSIT" \
    --after "2024-01-01" --before "2024-01-31"
```

## How It Works

1. **Query Smart Contract**: Finds NFT batches that might contain matching transactions
2. **Download Batch Data**: Retrieves detailed transaction data from S3
3. **Search Transactions**: Applies WHERE clause conditions to find matches
4. **Verify Merkle Proof**: Cryptographically verifies each transaction
5. **Generate Output**: Displays results or creates audit report

## Security Considerations

- **Read-Only**: This tool only reads data, never modifies anything
- **Public Blockchain**: Verification uses public NEAR blockchain data
- **Private S3**: Transaction details are in private S3 buckets (requires credentials)
- **No Sensitive Data on Chain**: Only hashes and metadata on blockchain

## Troubleshooting

### "No transactions found"

1. Check the database name is correct
2. Verify the time range includes when transactions occurred
3. Ensure WHERE clause conditions are correct
4. Try broader search criteria first

### "Error fetching from S3"

1. Verify AWS credentials are set
2. Check you have access to the S3 bucket
3. Ensure the batch was properly uploaded by CDC agent

### "RPC Error"

1. Check internet connection
2. Verify the contract ID is correct
3. Try different NEAR RPC endpoint if timeout

## Advanced Usage

### Debug Mode

Add `--debug` to see raw RPC responses and detailed processing:
```bash
python etrap_verify.py -c acme.testnet -d etrapdb --debug \
    -w "account_id=ACC500"
```

### Custom Networks

Use mainnet for production:
```bash
python etrap_verify.py -c company.near -d production \
    -n mainnet -w "amount>10000"
```

### Batch Processing

Process multiple queries from a file:
```bash
# queries.txt:
# account_id=ACC500 AND type=C
# account_id=ACC501 AND type=C
# account_id=ACC502 AND type=C

while IFS= read -r query; do
    python etrap_verify.py -c acme.testnet -d etrapdb \
        -t financial_transactions -w "$query" --report
done < queries.txt
```

## Integration

### Python API

```python
from etrap_verify import ETRAPTransactionVerifier

# Initialize verifier
verifier = ETRAPTransactionVerifier("acme.testnet", "testnet")

# Search and verify
results = await verifier.search_and_verify(
    database="etrapdb",
    table="financial_transactions",
    where_clause="account_id=ACC500 AND amount>1000",
    start_time=datetime.now() - timedelta(days=7),
    end_time=datetime.now()
)

# Generate report
report = verifier.generate_audit_report(results, query_params)
```

### Command Line Integration

```bash
# In scripts
RESULT=$(python etrap_verify.py -c acme.testnet -d etrapdb \
    -w "account_id=ACC500" --report)

# Check exit code
if [ $? -eq 0 ]; then
    echo "Verification successful"
else
    echo "Verification failed"
fi
```

## Limitations

- **OR complexity**: Parentheses in OR expressions are not supported; OR groups are evaluated left to right
- **Base64 handling**: Automatically decodes base64-encoded numeric values
- **Batch size**: Large batches may take longer to search
- **Time precision**: Timestamps are at millisecond precision
- **Reports directory**: All reports are saved to the `./reports` directory

## License

Part of the ETRAP platform. See main repository for license details.

## Support

For issues or questions:
- GitHub Issues: [etrap/issues](https://github.com/etrap/issues)
- Documentation: [etrap.io/docs](https://etrap.io/docs)
- Email: support@etrap.io