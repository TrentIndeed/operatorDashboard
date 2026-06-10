@echo off
REM DISABLED: VPS now uses a 1-year setup-token. This script would overwrite it
REM with a short-lived local OAuth token. Only re-enable if the VPS token is revoked.
echo VPS uses a 1-year token. This script is no longer needed.
echo If you need to push fresh creds, run: scripts\auto-refresh-creds.bat
pause
