@echo off
:loop
echo [%date% %time%] Refreshing Claude credentials to VPS...
scp -i %USERPROFILE%\.ssh\id_ed25519 -o StrictHostKeyChecking=no -o ConnectTimeout=10 %USERPROFILE%\.claude\.credentials.json root@5.161.100.230:/root/.claude/.credentials.json 2>nul
scp -i %USERPROFILE%\.ssh\id_ed25519 -o StrictHostKeyChecking=no -o ConnectTimeout=10 %USERPROFILE%\.claude.json root@5.161.100.230:/root/.claude.json 2>nul
ssh -i %USERPROFILE%\.ssh\id_ed25519 -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@5.161.100.230 "cd /opt/operatorDashboard && docker compose restart backend" 2>nul
echo [%date% %time%] Done. Sleeping 4 hours...
timeout /t 14400 /nobreak >nul
goto loop
