"""
Deploy pipeline — deploys the dashboard to a user's provisioned VPS.

Reusable: swap DEPLOY_REPO and DEPLOY_COMPOSE for any Docker-based SaaS.

Flow:
  1. SSH into the user's VPS
  2. Clone the repo
  3. Write .env with user's config
  4. docker compose up -d --build
  5. Configure Caddy for HTTPS (if domain provided)
"""
import os
import asyncio
import subprocess

DEPLOY_REPO = os.getenv("DEPLOY_REPO", "https://github.com/TrentIndeed/operatorDashboard.git")
DEPLOY_BRANCH = os.getenv("DEPLOY_BRANCH", "main")
SSH_KEY_PATH = os.getenv("SSH_KEY_PATH", os.path.expanduser("~/.ssh/id_ed25519"))


async def deploy_to_server(
    ip: str,
    env_vars: dict,
    domain: str = "",
    repo: str = "",
) -> dict:
    """
    Deploy the dashboard to a remote VPS via SSH.

    Args:
        ip: Server IP address
        env_vars: Dict of environment variables for .env
        domain: Optional domain for HTTPS (e.g., "user123.yourdomain.com")
        repo: Git repo URL (defaults to DEPLOY_REPO)

    Returns:
        {"status": "ok" | "error", "message": str}
    """
    repo = repo or DEPLOY_REPO

    # Build .env content
    env_content = "\n".join(f"{k}={v}" for k, v in env_vars.items())

    # Build deploy script
    caddy_config = ""
    if domain:
        caddy_config = f"""
# Configure Caddy HTTPS
cat > /etc/caddy/Caddyfile << 'CADDY'
{domain} {{
    reverse_proxy localhost:3000
}}

api.{domain} {{
    reverse_proxy localhost:8000
}}
CADDY
systemctl reload caddy
"""

    deploy_script = f"""#!/bin/bash
set -e

# Clone or pull
if [ -d /opt/operatorDashboard ]; then
    cd /opt/operatorDashboard && git pull
else
    cd /opt && git clone {repo} operatorDashboard
fi

cd /opt/operatorDashboard

# Write .env
cat > .env << 'ENVEOF'
{env_content}
ENVEOF

# Write frontend env
mkdir -p frontend
cat > frontend/.env.local << 'FEOF'
NEXT_PUBLIC_API_URL={"https://api." + domain if domain else "http://localhost:8000"}
NEXT_PUBLIC_DISPLAY_NAME=Operator
NEXT_PUBLIC_TAGLINE=solo founder mode
NEXT_PUBLIC_INITIALS=OP
FEOF

# Build and deploy
docker compose up -d --build

{caddy_config}

echo "DEPLOY_COMPLETE"
"""

    try:
        result = await _ssh_exec(ip, deploy_script)
        if "DEPLOY_COMPLETE" in result:
            return {"status": "ok", "message": "Deployment successful"}
        return {"status": "error", "message": f"Deploy may have failed: {result[-500:]}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def check_health(ip: str, domain: str = "") -> bool:
    """Check if the deployed dashboard is responding."""
    import httpx
    url = f"https://api.{domain}/health" if domain else f"http://{ip}:8000/health"
    try:
        async with httpx.AsyncClient(timeout=10, verify=False) as client:
            resp = await client.get(url)
            return resp.status_code == 200
    except Exception:
        return False


async def teardown_server(ip: str) -> dict:
    """Remove the deployment from a server (but don't destroy the VPS)."""
    try:
        result = await _ssh_exec(ip, "cd /opt/operatorDashboard && docker compose down -v 2>&1 || true")
        return {"status": "ok", "message": "Torn down"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def _ssh_exec(ip: str, script: str) -> str:
    """Execute a script on a remote server via SSH."""
    proc = await asyncio.create_subprocess_exec(
        "ssh",
        "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=30",
        "-i", SSH_KEY_PATH,
        f"root@{ip}",
        "bash", "-s",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(
        proc.communicate(script.encode()),
        timeout=600,  # 10 min max for builds
    )
    output = stdout.decode() + stderr.decode()
    if proc.returncode != 0:
        raise RuntimeError(f"SSH command failed (exit {proc.returncode}): {output[-500:]}")
    return output
