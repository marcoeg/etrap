#!/bin/bash
set -euo pipefail

# ETRAP Docker Container Generator
# Generates complete Docker setup for ETRAP customer organizations

# Script directory and template location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_DIR="$SCRIPT_DIR/docker"
BASE_DIR="$SCRIPT_DIR"

# Usage function
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

ETRAP Docker Container Generator
Generates a complete Docker setup for an ETRAP customer organization.

Required Parameters:
    --organization-name <name>      Human readable organization name (e.g., "Vantage Corp")
    --organization-id <id>          Unique identifier (e.g., "vantage")
    --postgres-host <host>          PostgreSQL server hostname/IP
    --postgres-database <db>        Database name to monitor
    --postgres-username <user>      Database username
    --postgres-password <pass>      Database password
    --near-network <network>        NEAR network (testnet/mainnet)
    --aws-access-key-id <key>       AWS access key ID
    --aws-secret-access-key <key>   AWS secret access key

Optional Parameters:
    --postgres-port <port>          PostgreSQL port (default: 5432)
    --aws-region <region>           AWS region (default: us-west-2)
    --near-private-key <key>        NEAR private key (reads from credential file if not provided)
    --force                         Overwrite existing container directory
    --help                          Show this help message

Examples:
    $0 --organization-name "Vantage Corp" \\
       --organization-id "vantage" \\
       --postgres-host "10.0.0.12" \\
       --postgres-database "etrapdb" \\
       --postgres-username "debezium" \\
       --postgres-password "password123" \\
       --near-network "testnet" \\
       --aws-access-key-id "AKIA..." \\
       --aws-secret-access-key "xyz..."

Prerequisites:
    - onboard_organization.sh must have been run successfully for this organization
    - NEAR credential file should exist at ~/.near-credentials/<network>/<org_id>.<network>.json
    - PostgreSQL server should be configured with Debezium replication slot and publication

EOF
    exit 1
}

# Default values
POSTGRES_PORT="5432"
AWS_REGION="us-west-2"
NEAR_PRIVATE_KEY=""
FORCE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --organization-name)
            ORGANIZATION_NAME="$2"
            shift 2
            ;;
        --organization-id)
            ORGANIZATION_ID="$2"
            shift 2
            ;;
        --postgres-host)
            POSTGRES_HOST="$2"
            shift 2
            ;;
        --postgres-port)
            POSTGRES_PORT="$2"
            shift 2
            ;;
        --postgres-database)
            POSTGRES_DATABASE="$2"
            shift 2
            ;;
        --postgres-username)
            POSTGRES_USERNAME="$2"
            shift 2
            ;;
        --postgres-password)
            POSTGRES_PASSWORD="$2"
            shift 2
            ;;
        --near-network)
            NEAR_NETWORK="$2"
            shift 2
            ;;
        --near-private-key)
            NEAR_PRIVATE_KEY="$2"
            shift 2
            ;;
        --aws-access-key-id)
            AWS_ACCESS_KEY_ID="$2"
            shift 2
            ;;
        --aws-secret-access-key)
            AWS_SECRET_ACCESS_KEY="$2"
            shift 2
            ;;
        --aws-region)
            AWS_REGION="$2"
            shift 2
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --help|-h)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# Validate required parameters
required_params=(
    "ORGANIZATION_NAME"
    "ORGANIZATION_ID"
    "POSTGRES_HOST"
    "POSTGRES_DATABASE"
    "POSTGRES_USERNAME"
    "POSTGRES_PASSWORD"
    "NEAR_NETWORK"
    "AWS_ACCESS_KEY_ID"
    "AWS_SECRET_ACCESS_KEY"
)

for param in "${required_params[@]}"; do
    if [ -z "${!param:-}" ]; then
        echo "ERROR: Required parameter --$(echo "$param" | tr '[:upper:]' '[:lower:]' | tr '_' '-') is missing"
        usage
    fi
done

# Validate NEAR network
if [[ "$NEAR_NETWORK" != "testnet" && "$NEAR_NETWORK" != "mainnet" ]]; then
    echo "ERROR: --near-network must be either 'testnet' or 'mainnet'"
    exit 1
fi

# Set derived values
ACCOUNT_ID="${ORGANIZATION_ID}.${NEAR_NETWORK}"
S3_BUCKET="etrap-${ORGANIZATION_ID}"
OUTPUT_DIR="$TEMPLATE_DIR/etrap-${ORGANIZATION_ID}"

# Check if output directory exists
if [ -d "$OUTPUT_DIR" ] && [ "$FORCE" = false ]; then
    echo "ERROR: Output directory $OUTPUT_DIR already exists"
    echo "Use --force to overwrite or choose a different organization ID"
    exit 1
fi

# Create output directory structure
echo "Creating Docker setup for $ORGANIZATION_NAME ($ORGANIZATION_ID)..."
rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR/config"
mkdir -p "$OUTPUT_DIR/scripts"

# Function to process template files
process_template() {
    local template_file="$1"
    local output_file="$2"
    
    if [ ! -f "$template_file" ]; then
        echo "ERROR: Template file not found: $template_file"
        exit 1
    fi
    
    # Substitute variables in template
    sed \
        -e "s/\${ORGANIZATION_NAME}/$ORGANIZATION_NAME/g" \
        -e "s/\${ORGANIZATION_ID}/$ORGANIZATION_ID/g" \
        -e "s/\${ORG_ID}/$ORGANIZATION_ID/g" \
        -e "s/\${POSTGRES_HOST}/$POSTGRES_HOST/g" \
        -e "s/\${POSTGRES_PORT}/$POSTGRES_PORT/g" \
        -e "s/\${POSTGRES_DATABASE}/$POSTGRES_DATABASE/g" \
        -e "s/\${POSTGRES_USER}/$POSTGRES_USERNAME/g" \
        -e "s/\${POSTGRES_PASSWORD}/$POSTGRES_PASSWORD/g" \
        -e "s/\${NEAR_NETWORK}/$NEAR_NETWORK/g" \
        -e "s/\${ACCOUNT_ID}/$ACCOUNT_ID/g" \
        -e "s/\${AWS_REGION}/$AWS_REGION/g" \
        -e "s/\${S3_BUCKET}/$S3_BUCKET/g" \
        "$template_file" > "$output_file"
}

# Generate main Docker files
echo "Generating Docker configuration files..."
process_template "$TEMPLATE_DIR/Dockerfile.template" "$OUTPUT_DIR/Dockerfile"
process_template "$TEMPLATE_DIR/docker-compose.yml.template" "$OUTPUT_DIR/docker-compose.yml"

# Generate configuration files
process_template "$TEMPLATE_DIR/debezium-application.properties.template" "$OUTPUT_DIR/config/debezium-application.properties"
process_template "$TEMPLATE_DIR/redis.conf.template" "$OUTPUT_DIR/config/redis.conf"

# Generate scripts
process_template "$TEMPLATE_DIR/entrypoint.sh.template" "$OUTPUT_DIR/scripts/entrypoint.sh"
process_template "$TEMPLATE_DIR/health-check.sh.template" "$OUTPUT_DIR/scripts/health-check.sh"
chmod +x "$OUTPUT_DIR/scripts/"*.sh

# Handle NEAR credentials
NEAR_CRED_FILE="$HOME/.near-credentials/$NEAR_NETWORK/$ACCOUNT_ID.json"
if [ -n "$NEAR_PRIVATE_KEY" ]; then
    echo "Using provided NEAR private key..."
    # Generate credentials file from private key
    cat > "$OUTPUT_DIR/config/near-credentials.json" << EOF
{
  "account_id": "$ACCOUNT_ID",
  "public_key": "ed25519:placeholder",
  "private_key": "$NEAR_PRIVATE_KEY"
}
EOF
elif [ -f "$NEAR_CRED_FILE" ]; then
    echo "Using existing NEAR credentials from $NEAR_CRED_FILE"
    cp "$NEAR_CRED_FILE" "$OUTPUT_DIR/config/near-credentials.json"
else
    echo "ERROR: NEAR credentials not found at $NEAR_CRED_FILE"
    echo "Either provide --near-private-key or ensure onboard_organization.sh has been run"
    exit 1
fi

# Copy ETRAP source files
echo "Copying ETRAP source files..."
cp "$BASE_DIR/cdc-agent/requirements.txt" "$OUTPUT_DIR/"
cp "$BASE_DIR/cdc-agent/etrap_cdc_agent.py" "$OUTPUT_DIR/"
#cp "$BASE_DIR/etrap_verify.py" "$OUTPUT_DIR/"

# Generate .env file
echo "Generating environment file..."
cat > "$OUTPUT_DIR/.env" << EOF
# ETRAP Environment Configuration for $ORGANIZATION_NAME
# Generated on $(date '+%Y-%m-%d %H:%M:%S')

# Organization Configuration
ORGANIZATION_NAME=$ORGANIZATION_NAME
ORGANIZATION_ID=$ORGANIZATION_ID
ORG_ID=$ORGANIZATION_ID

# NEAR Configuration
NEAR_NETWORK=$NEAR_NETWORK
NEAR_ACCOUNT_ID=$ACCOUNT_ID

# AWS Configuration
AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY
AWS_DEFAULT_REGION=$AWS_REGION

# S3 Configuration
ETRAP_S3_BUCKET=$S3_BUCKET
ETRAP_ORG_ID=$ORGANIZATION_ID

# Redis Configuration (internal)
REDIS_HOST=redis
REDIS_PORT=6379

# PostgreSQL Configuration (for reference - used in Debezium config)
POSTGRES_HOST=$POSTGRES_HOST
POSTGRES_PORT=$POSTGRES_PORT
POSTGRES_DATABASE=$POSTGRES_DATABASE
POSTGRES_USER=$POSTGRES_USERNAME
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
EOF

# Generate deployment instructions
cat > "$OUTPUT_DIR/DEPLOY.md" << EOF
# ETRAP Docker Deployment for $ORGANIZATION_NAME

## Quick Start

1. Navigate to the deployment directory:
   \`\`\`bash
   cd $OUTPUT_DIR
   \`\`\`

2. Build and start the containers:
   \`\`\`bash
   docker-compose up -d
   \`\`\`

3. Check the status:
   \`\`\`bash
   docker-compose ps
   docker-compose logs -f
   \`\`\`

## Configuration

- **Organization**: $ORGANIZATION_NAME ($ORGANIZATION_ID)
- **NEAR Network**: $NEAR_NETWORK
- **NEAR Account**: $ACCOUNT_ID
- **PostgreSQL**: $POSTGRES_HOST:$POSTGRES_PORT/$POSTGRES_DATABASE
- **S3 Bucket**: $S3_BUCKET
- **AWS Region**: $AWS_REGION

## Services

- **redis**: Redis server for message streaming
- **debezium**: Debezium server for PostgreSQL CDC
- **etrap-agent**: ETRAP CDC Agent for blockchain integration

## Management Commands

\`\`\`bash
# View logs
docker-compose logs -f [service_name]

# Restart a service
docker-compose restart [service_name]

# Stop all services
docker-compose down

# Rebuild and restart
docker-compose up -d --build

# Health check
docker-compose exec etrap-agent /app/scripts/health-check.sh all
\`\`\`

## Troubleshooting

1. Check PostgreSQL connectivity:
   \`\`\`bash
   docker-compose exec debezium /app/scripts/health-check.sh debezium
   \`\`\`

2. Verify NEAR credentials:
   \`\`\`bash
   docker-compose exec etrap-agent cat /root/.near-credentials/$NEAR_NETWORK/$ACCOUNT_ID.json
   \`\`\`

3. Monitor Redis streams:
   \`\`\`bash
   docker-compose exec redis redis-cli XINFO GROUPS etrap.public.*
   \`\`\`
EOF

echo "✅ Docker setup completed successfully!"
echo ""
echo "📁 Output directory: $OUTPUT_DIR"
echo "📝 Deployment guide: $OUTPUT_DIR/DEPLOY.md"
echo ""
echo "🚀 To start the containers:"
echo "   cd $OUTPUT_DIR"
echo "   docker-compose up -d"
echo ""
echo "📊 To monitor:"
echo "   docker-compose logs -f"