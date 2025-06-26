# ETRAP Docker Deployment for Lunaris Corp

## Quick Start

1. Navigate to the deployment directory:
   ```bash
   cd /home/marco/Development/mglabs/etrap/near/etrap/docker/etrap-lunaris
   ```

2. Build and start the containers:
   ```bash
   docker-compose up -d
   ```

3. Check the status:
   ```bash
   docker-compose ps
   docker-compose logs -f
   ```

## Configuration

- **Organization**: Lunaris Corp (lunaris)
- **NEAR Network**: testnet
- **NEAR Account**: lunaris.testnet
- **PostgreSQL**: 52.13.35.62:5432/etrapdb
- **S3 Bucket**: etrap-lunaris
- **AWS Region**: us-west-2

## Services

- **redis**: Redis server for message streaming
- **debezium**: Debezium server for PostgreSQL CDC
- **etrap-agent**: ETRAP CDC Agent for blockchain integration

## Management Commands

```bash
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
```

## Troubleshooting

1. Check PostgreSQL connectivity:
   ```bash
   docker-compose exec debezium /app/scripts/health-check.sh debezium
   ```

2. Verify NEAR credentials:
   ```bash
   docker-compose exec etrap-agent cat /root/.near-credentials/testnet/lunaris.testnet.json
   ```

3. Monitor Redis streams:
   ```bash
   docker-compose exec redis redis-cli XINFO GROUPS etrap.public.*
   ```
