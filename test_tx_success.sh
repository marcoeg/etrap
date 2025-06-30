#!/bin/bash

# Function to poll transaction until it completes
near_tx_success() {
  local tx_hash="$1"
  local account="$2"
  local max_retries=60
  local attempt=0

  while true; do
    output=$(near tx-status "$tx_hash" "$account" 2>/dev/null)

    if echo "$output" | grep -q 'status:'; then
      if echo "$output" | awk '/status:/,/}/' | grep -q 'SuccessValue'; then
        echo "✅ Transaction succeeded"
        return 0
      elif echo "$output" | awk '/status:/,/}/' | grep -q 'Failure\|Unknown'; then
        echo "❌ Transaction failed"
        return 1
      fi
    fi

    (( attempt++ ))
    if [ "$attempt" -ge "$max_retries" ]; then
      echo "⏱️ Timeout waiting for transaction confirmation"
      return 2
    fi

    sleep 1
  done
}

# Main logic: send 0 NEAR to self
account_id="vantage.testnet"

echo "🚀 Sending 0 NEAR from $account_id to itself..."
send_output=$(near send "$account_id" "$account_id" 0)
tx_hash=$(echo "$send_output" | awk '/Transaction Id/ {print $3}')

if [ -z "$tx_hash" ]; then
  echo "❌ Failed to extract transaction hash"
  exit 1
fi

echo "🔍 Waiting for transaction $tx_hash to complete..."
near_tx_success "$tx_hash" "$account_id"
