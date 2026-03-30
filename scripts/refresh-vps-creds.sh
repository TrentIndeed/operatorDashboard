#!/usr/bin/env bash
# Refresh Claude CLI credentials on the VPS from your local machine
# Run this when you get an auth expired alert

VPS_IP="${1:-5.161.100.230}"

echo "Copying Claude credentials to VPS ($VPS_IP)..."
scp ~/.claude/.credentials.json root@$VPS_IP:/root/.claude/.credentials.json
scp ~/.claude.json root@$VPS_IP:/root/.claude.json

echo "Restarting backend..."
ssh root@$VPS_IP "cd /opt/operatorDashboard && docker compose restart backend"

echo "Testing..."
sleep 5
RESULT=$(ssh root@$VPS_IP "docker exec operatordashboard-backend-1 claude -p 'say ok' --max-turns 1 2>&1 | head -1")
if echo "$RESULT" | grep -qi 'ok\|hello\|hi'; then
    echo "Claude auth refreshed successfully."
else
    echo "WARNING: Auth may still be broken. Result: $RESULT"
fi
