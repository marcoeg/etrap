#!/bin/bash
set -euo pipefail

# PostgreSQL Setup Script for ETRAP Debezium Integration
# Generates and optionally executes PostgreSQL configuration for Change Data Capture

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_FILE="$SCRIPT_DIR/setup-postgresql.sql.template"

# Usage function
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

PostgreSQL Setup for ETRAP Debezium Integration
Configures PostgreSQL database for Change Data Capture with Debezium.

Required Parameters:
    --database <name>           Database name to configure (e.g., etrapdb)
    --debezium-user <user>      Debezium username (e.g., debezium)
    --debezium-password <pass>  Debezium user password

Optional Parameters:
    --replication-slot <name>   Replication slot name (default: etrap_debezium_slot)
    --publication <name>        Publication name (default: etrap_publication)
    --postgres-host <host>      PostgreSQL host (default: localhost)
    --postgres-port <port>      PostgreSQL port (default: 5432)
    --postgres-admin <user>     PostgreSQL admin user (default: postgres)
    --output-file <file>        Output SQL file (default: setup-postgresql.sql)
    --execute                   Execute the SQL script directly
    --help                      Show this help message

Configuration File Examples:
    This script also generates example configuration files for:
    - postgresql.conf (replication settings)
    - pg_hba.conf (authentication settings)

Examples:
    # Generate SQL script only
    $0 --database etrapdb --debezium-user debezium --debezium-password mypassword

    # Generate and execute SQL script
    $0 --database etrapdb --debezium-user debezium --debezium-password mypassword --execute

    # Custom configuration
    $0 --database mydb --debezium-user myuser --debezium-password mypass \\
       --replication-slot my_slot --publication my_pub \\
       --postgres-host 10.0.0.12 --postgres-port 5433

Prerequisites:
    1. PostgreSQL server must be running and accessible
    2. Admin user (postgres) must have superuser privileges
    3. Target database must already exist
    4. For --execute option: psql must be installed and accessible

EOF
    exit 1
}

# Default values
DATABASE_NAME=""
DEBEZIUM_USER=""
DEBEZIUM_PASSWORD=""
REPLICATION_SLOT="etrap_debezium_slot"
PUBLICATION_NAME="etrap_publication"
POSTGRES_HOST="localhost"
POSTGRES_PORT="5432"
POSTGRES_ADMIN="postgres"
OUTPUT_FILE="setup-postgresql.sql"
EXECUTE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --database)
            DATABASE_NAME="$2"
            shift 2
            ;;
        --debezium-user)
            DEBEZIUM_USER="$2"
            shift 2
            ;;
        --debezium-password)
            DEBEZIUM_PASSWORD="$2"
            shift 2
            ;;
        --replication-slot)
            REPLICATION_SLOT="$2"
            shift 2
            ;;
        --publication)
            PUBLICATION_NAME="$2"
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
        --postgres-admin)
            POSTGRES_ADMIN="$2"
            shift 2
            ;;
        --output-file)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        --execute)
            EXECUTE=true
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
if [ -z "$DATABASE_NAME" ] || [ -z "$DEBEZIUM_USER" ] || [ -z "$DEBEZIUM_PASSWORD" ]; then
    echo "ERROR: Required parameters --database, --debezium-user, and --debezium-password must be provided"
    usage
fi

# Check if template file exists
if [ ! -f "$TEMPLATE_FILE" ]; then
    echo "ERROR: Template file not found: $TEMPLATE_FILE"
    exit 1
fi

echo "=== PostgreSQL Setup for ETRAP ==="
echo "Database: $DATABASE_NAME"
echo "Debezium User: $DEBEZIUM_USER"
echo "Replication Slot: $REPLICATION_SLOT"
echo "Publication: $PUBLICATION_NAME"
echo "Output File: $OUTPUT_FILE"
echo ""

# Generate SQL script from template
echo "Generating SQL setup script..."
sed \
    -e "s/\${DATABASE_NAME}/$DATABASE_NAME/g" \
    -e "s/\${DEBEZIUM_USER}/$DEBEZIUM_USER/g" \
    -e "s/\${DEBEZIUM_PASSWORD}/$DEBEZIUM_PASSWORD/g" \
    -e "s/\${REPLICATION_SLOT}/$REPLICATION_SLOT/g" \
    -e "s/\${PUBLICATION_NAME}/$PUBLICATION_NAME/g" \
    "$TEMPLATE_FILE" > "$OUTPUT_FILE"

echo "✅ Generated SQL script: $OUTPUT_FILE"

# Generate postgresql.conf example
cat > "postgresql.conf.example" << EOF
# PostgreSQL Configuration for ETRAP Debezium Integration
# Add these settings to your postgresql.conf file

# Replication settings for Change Data Capture
wal_level = logical
max_replication_slots = 4
max_wal_senders = 4

# Optional: Improve replication performance
wal_sender_timeout = 60s
wal_receiver_timeout = 60s

# Optional: Archive settings (for production)
# archive_mode = on
# archive_command = 'cp %p /path/to/archive/%f'

# After modifying postgresql.conf, restart PostgreSQL server
EOF

echo "✅ Generated postgresql.conf.example"

# Generate pg_hba.conf example
cat > "pg_hba.conf.example" << EOF
# pg_hba.conf entries for ETRAP Debezium Integration
# Add these lines to your pg_hba.conf file

# Allow debezium user to connect to database
host    $DATABASE_NAME    $DEBEZIUM_USER    0.0.0.0/0    md5

# Allow debezium user replication connections
host    replication       $DEBEZIUM_USER    0.0.0.0/0    md5

# For local connections only (more secure):
# host    $DATABASE_NAME    $DEBEZIUM_USER    127.0.0.1/32    md5
# host    replication       $DEBEZIUM_USER    127.0.0.1/32    md5

# For specific network (recommended for production):
# host    $DATABASE_NAME    $DEBEZIUM_USER    10.0.0.0/8      md5
# host    replication       $DEBEZIUM_USER    10.0.0.0/8      md5

# After modifying pg_hba.conf, reload PostgreSQL configuration:
# SELECT pg_reload_conf();
EOF

echo "✅ Generated pg_hba.conf.example"

# Execute SQL script if requested
if [ "$EXECUTE" = true ]; then
    echo ""
    echo "Executing SQL script on PostgreSQL server..."
    echo "Host: $POSTGRES_HOST:$POSTGRES_PORT"
    echo "Admin User: $POSTGRES_ADMIN"
    echo ""
    
    # Check if psql is available
    if ! command -v psql >/dev/null 2>&1; then
        echo "ERROR: psql command not found. Please install PostgreSQL client tools."
        exit 1
    fi
    
    # Test connection first
    echo "Testing connection to PostgreSQL..."
    if ! psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_ADMIN" -d "$DATABASE_NAME" -c "SELECT 1;" >/dev/null 2>&1; then
        echo "ERROR: Cannot connect to PostgreSQL server"
        echo "Please check:"
        echo "  - Server is running on $POSTGRES_HOST:$POSTGRES_PORT"
        echo "  - Database '$DATABASE_NAME' exists"
        echo "  - User '$POSTGRES_ADMIN' has access"
        echo "  - Password authentication is working"
        exit 1
    fi
    
    echo "✅ Connection successful, executing setup script..."
    
    # Execute the SQL script
    if psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_ADMIN" -d "$DATABASE_NAME" -f "$OUTPUT_FILE"; then
        echo ""
        echo "✅ PostgreSQL setup completed successfully!"
        echo ""
        echo "Next steps:"
        echo "1. Review and apply postgresql.conf.example settings"
        echo "2. Review and apply pg_hba.conf.example settings"
        echo "3. Restart/reload PostgreSQL as needed"
        echo "4. Test Debezium connection:"
        echo "   psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $DEBEZIUM_USER -d $DATABASE_NAME"
    else
        echo "❌ SQL script execution failed. Check the output above for errors."
        exit 1
    fi
else
    echo ""
    echo "SQL script generated but not executed."
    echo ""
    echo "To execute manually:"
    echo "  psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_ADMIN -d $DATABASE_NAME -f $OUTPUT_FILE"
    echo ""
    echo "Or run this script with --execute flag:"
    echo "  $0 --database $DATABASE_NAME --debezium-user $DEBEZIUM_USER --debezium-password \"***\" --execute"
fi

echo ""
echo "Configuration files generated:"
echo "  📄 $OUTPUT_FILE - SQL setup script"
echo "  📄 postgresql.conf.example - PostgreSQL configuration"
echo "  📄 pg_hba.conf.example - Authentication configuration"
echo ""
echo "For more information, see the Docker README: $SCRIPT_DIR/README.md"