@echo off
scp -i %USERPROFILE%\.ssh\id_ed25519 %USERPROFILE%\.claude\.credentials.json root@5.161.100.230:/root/.claude/.credentials.json
scp -i %USERPROFILE%\.ssh\id_ed25519 %USERPROFILE%\.claude.json root@5.161.100.230:/root/.claude.json
ssh -i %USERPROFILE%\.ssh\id_ed25519 root@5.161.100.230 "cd /opt/operatorDashboard && docker compose restart backend"
