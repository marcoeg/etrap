# ETRAP Docker Container
# Multi-stage build: Java for Debezium + Python for ETRAP CDC Agent

FROM openjdk:11-jre-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    python3 \
    python3-pip \
    python3-venv \
    unzip \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

# Create symbolic link for python
RUN ln -s /usr/bin/python3 /usr/bin/python

# Set working directory
WORKDIR /app

# Install Debezium Server
ARG DEBEZIUM_VERSION=2.4.2.Final
RUN wget -q https://repo1.maven.org/maven2/io/debezium/debezium-server-dist/${DEBEZIUM_VERSION}/debezium-server-dist-${DEBEZIUM_VERSION}.tar.gz \
    && tar -xzf debezium-server-dist-${DEBEZIUM_VERSION}.tar.gz \
    && mv debezium-server /opt/debezium-server \
    && rm debezium-server-dist-${DEBEZIUM_VERSION}.tar.gz

# Copy Python requirements and install dependencies
COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt

# Copy ETRAP CDC Agent
COPY etrap_cdc_agent.py .

# Copy configuration files
COPY config/ /app/config/

# Copy scripts
COPY scripts/ /app/scripts/
RUN chmod +x /app/scripts/*.sh

# Create necessary directories
RUN mkdir -p /app/data /app/logs /root/.near-credentials

# Set up NEAR credentials directory structure
RUN mkdir -p /root/.near-credentials/testnet /root/.near-credentials/mainnet

# Environment variables
ENV DEBEZIUM_HOME=/opt/debezium-server
ENV PATH="$DEBEZIUM_HOME/bin:$PATH"
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose ports (not used in docker-compose but for reference)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
    CMD /app/scripts/health-check.sh

# Use entrypoint script
ENTRYPOINT ["/app/scripts/entrypoint.sh"]