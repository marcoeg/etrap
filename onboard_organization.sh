#!/bin/bash

set -euo pipefail

# Required input
ORG_NAME="$1"
ORG_ID="$2"
MASTER_ACCOUNT="etrap.testnet"
TREASURY_ACCOUNT="etrap-treasury.testnet"
INITIAL_BALANCE="10"
CONTRACT_DIR="/home/marco/Development/mglabs/etrap/near/notary/out"

# Logging setup
LOG_DIR="./logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/onboard_${ORG_ID}_$(date '+%Y%m%d_%H%M%S').log"

log() {
  echo -e "$1" | tee -a "$LOG_FILE"
}

# Helper function to check transaction success
near_tx_success() {
  local tx_hash="$1"
  local account="$2"
  local max_retries=60
  local attempt=0

  while true; do
    output=$(near tx-status "$tx_hash" "$account" 2>&1)
    echo "$output" >> "$LOG_FILE"

    if echo "$output" | grep -q 'status:'; then
      if echo "$output" | awk '/status:/,/}/' | grep -q 'SuccessValue'; then
        log "✅ Transaction $tx_hash succeeded"
        return 0
      elif echo "$output" | awk '/status:/,/}/' | grep -q 'Failure\|Unknown'; then
        log "❌ Transaction $tx_hash failed"
        return 1
      fi
    fi

    (( attempt++ ))
    if [ "$attempt" -ge "$max_retries" ]; then
      log "⏱️ Timeout waiting for transaction $tx_hash confirmation"
      return 2
    fi

    sleep 1
  done
}

if [ -z "$ORG_NAME" ] || [ -z "$ORG_ID" ]; then
  echo "Usage: $0 <organization_name> <organization_id>"
  exit 1
fi

ACCOUNT_ID="${ORG_ID}.testnet"
log "🚀 Starting onboarding for: $ORG_NAME ($ACCOUNT_ID)"

# 1. Create NEAR account
log "🔧 Creating NEAR account $ACCOUNT_ID..."
create_output=$(near create-account "$ACCOUNT_ID" --masterAccount "$MASTER_ACCOUNT" --initialBalance "$INITIAL_BALANCE" 2>&1 || true)
echo "$create_output" >> "$LOG_FILE"

if echo "$create_output" | grep -q 'Transaction Id'; then
  tx_hash=$(echo "$create_output" | awk '/Transaction Id/ {print $3}')
  log "🔍 Waiting for account creation tx $tx_hash to complete..."
  near_tx_success "$tx_hash" "$MASTER_ACCOUNT"
else
  log "⚠️ Account may already exist or failed to create. Skipping account creation."
fi

# 2. Verify account
log "🔍 Verifying account $ACCOUNT_ID exists..."
if ! near state "$ACCOUNT_ID" >> "$LOG_FILE" 2>&1; then
  log "❌ Account $ACCOUNT_ID does not exist. Aborting."
  exit 1
fi

# 3. Deploy contract
log "📦 Deploying contract to $ACCOUNT_ID..."
deploy_output=$(near deploy "$ACCOUNT_ID" "$CONTRACT_DIR/etrap_contract.wasm" 2>&1)
echo "$deploy_output" >> "$LOG_FILE"

deploy_tx_hash=$(echo "$deploy_output" | awk '/Transaction Id/ {print $3}')
log "🔍 Waiting for deploy tx $deploy_tx_hash to complete..."
near_tx_success "$deploy_tx_hash" "$ACCOUNT_ID"

# 4. Initialize contract
log "⚙️ Initializing contract for $ORG_NAME..."
init_output=$(near call "$ACCOUNT_ID" new \
  "{\"organization_id\": \"$ACCOUNT_ID\", \"organization_name\": \"$ORG_NAME\", \"etrap_treasury\": \"$TREASURY_ACCOUNT\", \"etrap_fee_amount\": 0.05}" \
  --accountId "$ACCOUNT_ID" 2>&1)
echo "$init_output" >> "$LOG_FILE"

init_tx_hash=$(echo "$init_output" | awk '/Transaction Id/ {print $3}')
log "🔍 Waiting for init tx $init_tx_hash to complete..."
near_tx_success "$init_tx_hash" "$ACCOUNT_ID"

log "🎉 Onboarding completed for $ORG_NAME ($ACCOUNT_ID)"
log "📄 Full log written to $LOG_FILE"
