#!/usr/bin/env bash
# Mandate — Soroban Policy Contract Deployment Script
#
# Prerequisites:
#   - Rust toolchain: curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
#   - Soroban CLI: cargo install --locked soroban-cli
#   - wasm32 target: rustup target add wasm32-unknown-unknown
#
# Usage:
#   ./deploy.sh testnet    # Deploy to Stellar testnet
#   ./deploy.sh mainnet    # Deploy to Stellar mainnet (requires funded account)
#
# Environment variables:
#   MANDATE_STELLAR_SIGNING_KEY - Secret key for deployment (starts with S...)
#   MANDATE_STELLAR_NETWORK - "testnet" or "public"
#
set -euo pipefail

NETWORK="${1:-testnet}"
CONTRACT_DIR="$(cd "$(dirname "$0")/soroban-policy" && pwd)"
WASM_PATH="$CONTRACT_DIR/target/wasm32-unknown-unknown/release/mandate_policy.wasm"

echo "=== Mandate Policy Contract Deployment ==="
echo "Network: $NETWORK"
echo ""

# --- Step 1: Build ---
echo "[1/5] Building contract..."
cd "$CONTRACT_DIR"
cargo build --target wasm32-unknown-unknown --release
echo "  ✓ Built: $WASM_PATH"
echo "  Size: $(wc -c < "$WASM_PATH") bytes"

# --- Step 2: Optimize (optional, reduces size) ---
echo "[2/5] Optimizing WASM..."
if command -v soroban &> /dev/null; then
    soroban contract optimize --wasm "$WASM_PATH"
    echo "  ✓ Optimized"
else
    echo "  ⚠ soroban CLI not found, skipping optimization"
fi

# --- Step 3: Configure network ---
echo "[3/5] Configuring network..."
if [ "$NETWORK" = "testnet" ]; then
    NETWORK_PASSPHRASE="Test SDF Network ; September 2015"
    RPC_URL="https://soroban-testnet.stellar.org"
    HORIZON_URL="https://horizon-testnet.stellar.org"
    FRIENDBOT="https://friendbot.stellar.org"
elif [ "$NETWORK" = "mainnet" ] || [ "$NETWORK" = "public" ]; then
    NETWORK_PASSPHRASE="Public Global Stellar Network ; September 2015"
    RPC_URL="https://soroban-rpc.mainnet.stellar.gateway.fm"
    HORIZON_URL="https://horizon.stellar.org"
    FRIENDBOT=""
else
    echo "ERROR: Unknown network '$NETWORK'. Use 'testnet' or 'mainnet'."
    exit 1
fi

echo "  RPC: $RPC_URL"
echo "  Horizon: $HORIZON_URL"

# --- Step 4: Generate or use deployer account ---
echo "[4/5] Setting up deployer account..."
if [ -n "${MANDATE_STELLAR_SIGNING_KEY:-}" ]; then
    echo "  Using provided signing key"
    DEPLOYER_SECRET="$MANDATE_STELLAR_SIGNING_KEY"
else
    if [ "$NETWORK" = "testnet" ]; then
        echo "  Generating new testnet account..."
        KEYPAIR=$(soroban keys generate mandate-deployer --network testnet 2>&1 || true)
        DEPLOYER_SECRET=$(soroban keys show mandate-deployer 2>/dev/null || echo "")
        if [ -z "$DEPLOYER_SECRET" ]; then
            echo "  ERROR: Could not generate keys. Install soroban CLI first."
            exit 1
        fi
        # Fund via friendbot
        DEPLOYER_PUBLIC=$(soroban keys address mandate-deployer)
        echo "  Funding via friendbot: $DEPLOYER_PUBLIC"
        curl -s "$FRIENDBOT?addr=$DEPLOYER_PUBLIC" > /dev/null
        echo "  ✓ Account funded"
    else
        echo "  ERROR: MANDATE_STELLAR_SIGNING_KEY required for mainnet deployment"
        exit 1
    fi
fi

# --- Step 5: Deploy contract ---
echo "[5/5] Deploying contract..."
CONTRACT_ID=$(soroban contract deploy \
    --wasm "$WASM_PATH" \
    --source "$DEPLOYER_SECRET" \
    --rpc-url "$RPC_URL" \
    --network-passphrase "$NETWORK_PASSPHRASE" 2>&1)

echo ""
echo "=== Deployment Complete ==="
echo "Contract ID: $CONTRACT_ID"
echo "Network: $NETWORK"
echo "RPC: $RPC_URL"
echo ""
echo "Next steps:"
echo "  1. Initialize the contract:"
echo "     soroban contract invoke \\"
echo "       --id $CONTRACT_ID \\"
echo "       --source \$MANDATE_STELLAR_SIGNING_KEY \\"
echo "       --rpc-url $RPC_URL \\"
echo "       --network-passphrase \"$NETWORK_PASSPHRASE\" \\"
echo "       -- initialize \\"
echo "       --admin <ADMIN_ADDRESS> \\"
echo "       --single_limit 25000000000 \\"
echo "       --daily_limit 100000000000 \\"
echo "       --timelock_threshold 100000000000"
echo ""
echo "  2. Set in environment:"
echo "     export MANDATE_SOROBAN_CONTRACT_ID=$CONTRACT_ID"
echo ""
echo "  3. Add allowed addresses:"
echo "     soroban contract invoke --id $CONTRACT_ID ... -- add_to_allowlist --admin <ADMIN> --address <RECIPIENT>"
echo ""

# Save contract ID for the backend
echo "$CONTRACT_ID" > "$CONTRACT_DIR/../.soroban-contract-id-$NETWORK"
echo "Contract ID saved to: $CONTRACT_DIR/../.soroban-contract-id-$NETWORK"
