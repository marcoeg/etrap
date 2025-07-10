# PostgreSQL Setup on Ubuntu EC2 Instance

This guide documents the complete setup of PostgreSQL 14 with the AWS DMS sample database on an Ubuntu 22.04 EC2 instance.

## Server Information
- **OS**: Ubuntu 22.04.1 LTS (ARM/aarch64)
- **Instance**: AWS EC2 with 8GB disk

## Prerequisites - Disk Space Cleanup

Before installing PostgreSQL, ensure adequate disk space (started at 44% full):

```bash
# 1. Remove disabled snap packages
sudo snap list --all | awk '/disabled/{print $1, $3}' | while read name rev; do 
    sudo snap remove "$name" --revision="$rev"
done

# 2. Clean snap cache
sudo rm -rf /var/lib/snapd/cache/*

# 3. Clean apt cache
sudo apt-get clean
sudo apt-get autoremove -y

# 4. Clean journal logs
sudo journalctl --vacuum-size=10M

# 5. Remove old kernels (if you have newer ones)
# First check what you have:
dpkg -l 'linux-*' | grep ^ii | grep -E 'linux-(image|headers|modules)' | awk '{print $2, $3}'
# Then remove old ones (example):
sudo apt-get purge linux-headers-6.8.0-1031-aws linux-image-6.8.0-1031-aws linux-modules-6.8.0-1031-aws
sudo apt-get autoremove -y
```

Result: Freed ~400MB, disk usage reduced from 44% to 39%.

## PostgreSQL Installation

```bash
# 1. Update package list
sudo apt update

# 2. Install PostgreSQL 14
sudo apt install -y postgresql postgresql-contrib

# 3. When prompted about restarting services, select <Ok> to restart all services

# 4. Verify installation
sudo systemctl status postgresql
sudo systemctl status postgresql@14-main
```

## Database and User Setup

```bash
# 1. Create application user and database
sudo -u postgres psql << EOF
CREATE USER etrapuser WITH PASSWORD 'ducati996';
CREATE DATABASE dms_sample OWNER etrapuser;
GRANT ALL PRIVILEGES ON DATABASE dms_sample TO etrapuser;
EOF

# 2. Create schema
sudo -u postgres psql -d dms_sample -c "CREATE SCHEMA dms_sample;"

# 3. Grant schema permissions
sudo -u postgres psql -d dms_sample << EOF
GRANT ALL ON SCHEMA dms_sample TO etrapuser;
EOF
```

## Configure Remote Access

```bash
# 1. Edit PostgreSQL configuration
sudo nano /etc/postgresql/14/main/postgresql.conf
# Find and change:
# listen_addresses = 'localhost' → listen_addresses = '*'

# 2. Edit authentication configuration
sudo nano /etc/postgresql/14/main/pg_hba.conf
# Add this line at the end:
# host    all             all             0.0.0.0/0            md5

# 3. Restart PostgreSQL
sudo systemctl restart postgresql

# 4. Ensure AWS Security Group allows inbound TCP port 5432
```

## Install AWS DMS Sample Database

```bash
# 1. Clone the sample database repository
cd /tmp
git clone https://github.com/aws-samples/aws-database-migration-samples.git
cd aws-database-migration-samples/PostgreSQL/sampledb/v1

# 2. Copy the reduced installation script
# Create install-postgresql-reduced.sql with the reduced data set
# (or copy from your local machine)

# 3. Run the installation script
sudo -u postgres psql -d dms_sample -f install-postgresql-reduced.sql
```

### About the Reduced Script

The `install-postgresql-reduced.sql` script creates a smaller dataset:
- 10,000 person records (instead of millions)
- 30% of sporting events
- Proportionally reduced tickets and transactions
- Total database size: ~104MB

Key modifications:
- Limited person generation to 100x100 with LIMIT 10000
- Deleted 70% of sporting events after generation
- Reduced ticket activity from 5000 to 1500
- Reduced transfer activity from 1000 to 300

## Grant Final Permissions

After the script completes, grant permissions on all created objects:

```bash
sudo -u postgres psql -d dms_sample << EOF
GRANT ALL ON SCHEMA dms_sample TO etrapuser;
GRANT ALL ON ALL TABLES IN SCHEMA dms_sample TO etrapuser;
GRANT ALL ON ALL SEQUENCES IN SCHEMA dms_sample TO etrapuser;
EOF
```

## Verification

### Local connection test:
```bash
psql -h 127.0.0.1 -U etrapuser -d dms_sample
# Password: ducati996

# In psql:
SET search_path TO dms_sample, public;
\dt
SELECT COUNT(*) FROM person;  -- Should show 10,000
```

### Remote connection test:
```bash
psql -h 54.213.201.149 -U etrapuser -d dms_sample
# Password: ducati996
```

## Final Database Statistics

- **Database size**: 104 MB
- **Tables**: 16 tables in dms_sample schema
- **Records**:
  - person: 10,000
  - sporting_event: 348
  - sporting_event_ticket: 126,556
  - ticket_purchase_hist: 147,726

## Disk Usage Summary

- Before PostgreSQL: 2.9GB used (39%)
- After PostgreSQL installation: 3.1GB used (41%)
- After database creation: ~3.2GB used
- Free space remaining: ~4.4GB

## Notes

- The "Permission denied" warning when running commands as postgres user can be ignored
- Default postgres user has no password and uses peer authentication
- All tables are in the `dms_sample` schema, not public schema
- Remember to set search_path or use schema-qualified names

## Appendix: Manual PostgreSQL Configuration for CDC

If the database requires manual configuration before running the ETRAP setup script (as with the dms_sample database case), follow these steps:

### Step 1: Verify Current Configuration
Connect to the database and check the current settings:
```sql
SHOW wal_level;  -- If this shows 'replica', it needs to be changed to 'logical'
SHOW max_replication_slots;
SHOW max_wal_senders;
```

### Step 2: Update PostgreSQL Configuration Files
On the PostgreSQL server (requires SSH access):

1. **Edit postgresql.conf** (typically at `/etc/postgresql/14/main/postgresql.conf`):
   ```ini
   wal_level = logical
   max_replication_slots = 4
   max_wal_senders = 4
   ```

2. **Edit pg_hba.conf** (typically at `/etc/postgresql/14/main/pg_hba.conf`):
   Add these lines for the debezium user:
   ```
   host    dms_sample    debezium    0.0.0.0/0    md5
   host    replication   debezium    0.0.0.0/0    md5
   ```

### Step 3: Restart PostgreSQL
```bash
sudo systemctl restart postgresql
```

### Step 4: Verify Changes
Reconnect and verify the configuration is now correct:
```sql
SHOW wal_level;  -- Should now show 'logical'
```

### Step 5: Run Setup Script
Once the WAL level is set to logical, you can proceed with the setup script:
```bash
./setup-postgresql.sh \
  --database dms_sample \
  --debezium-user debezium \
  --debezium-password your_secure_password \
  --postgres-host 54.213.201.149 \
  --execute
```

**Note**: If the current database user doesn't have superuser privileges, you may need to run the generated SQL script directly on the server as the postgres user.
