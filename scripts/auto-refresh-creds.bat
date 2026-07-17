@echo off
scp -i %USERPROFILE%\.ssh\id_ed25519 %USERPROFILE%\.claude\.credentials.json root@YOUR_VPS_IP:/root/.claude/.credentials.json
scp -i %USERPROFILE%\.ssh\id_ed25519 %USERPROFILE%\.claude.json root@YOUR_VPS_IP:/root/.claude.json
ssh -i %USERPROFILE%\.ssh\id_ed25519 root@YOUR_VPS_IP "cd /opt/operatorDashboard && docker compose restart backend"
