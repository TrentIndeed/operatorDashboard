"""
Hetzner Cloud VPS provisioning — reusable across any SaaS app.

Creates, monitors, and destroys cloud servers for paying users.
Each user gets their own VPS with Docker and the app deployed.

Setup:
  1. Create a Hetzner Cloud API token at https://console.hetzner.cloud/
  2. Set HETZNER_API_TOKEN in .env
"""
import os
import httpx
import asyncio
from typing import Optional

HETZNER_API = "https://api.hetzner.cloud/v1"
HETZNER_TOKEN = os.getenv("HETZNER_API_TOKEN", "")

# Default server config
DEFAULT_SERVER_TYPE = "cx22"  # 2 vCPU, 4GB RAM, 40GB — $4.35/mo
DEFAULT_LOCATION = "ash"  # Ashburn, VA
DEFAULT_IMAGE = "ubuntu-24.04"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {HETZNER_TOKEN}",
        "Content-Type": "application/json",
    }


async def create_server(
    name: str,
    ssh_key_name: Optional[str] = None,
    server_type: str = DEFAULT_SERVER_TYPE,
    location: str = DEFAULT_LOCATION,
    user_data: str = "",
) -> dict:
    """
    Create a new Hetzner Cloud server.

    Args:
        name: Server name (e.g., "op-user-123")
        ssh_key_name: Name of SSH key registered in Hetzner
        user_data: Cloud-init script to run on first boot

    Returns:
        {"server_id": str, "ip": str, "status": str}
    """
    body = {
        "name": name,
        "server_type": server_type,
        "location": location,
        "image": DEFAULT_IMAGE,
        "start_after_create": True,
        "user_data": user_data or _default_cloud_init(),
    }

    if ssh_key_name:
        body["ssh_keys"] = [ssh_key_name]

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{HETZNER_API}/servers",
            headers=_headers(),
            json=body,
        )
        resp.raise_for_status()
        data = resp.json()

    server = data["server"]
    return {
        "server_id": str(server["id"]),
        "ip": server["public_net"]["ipv4"]["ip"],
        "status": server["status"],
    }


async def get_server(server_id: str) -> dict:
    """Get server status and details."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{HETZNER_API}/servers/{server_id}",
            headers=_headers(),
        )
        resp.raise_for_status()
        server = resp.json()["server"]

    return {
        "server_id": str(server["id"]),
        "ip": server["public_net"]["ipv4"]["ip"],
        "status": server["status"],
        "server_type": server["server_type"]["name"],
    }


async def destroy_server(server_id: str) -> bool:
    """Delete a server permanently."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.delete(
            f"{HETZNER_API}/servers/{server_id}",
            headers=_headers(),
        )
        return resp.status_code in (200, 204)


async def wait_for_running(server_id: str, timeout: int = 120) -> bool:
    """Poll until server is running or timeout."""
    for _ in range(timeout // 5):
        info = await get_server(server_id)
        if info["status"] == "running":
            return True
        await asyncio.sleep(5)
    return False


def _default_cloud_init() -> str:
    """Cloud-init script that installs Docker and prepares the server."""
    return """#!/bin/bash
set -e

# Install Docker
curl -fsSL https://get.docker.com | sh

# Install Docker Compose plugin
apt-get install -y docker-compose-plugin git

# Install Node.js + Claude CLI
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs
npm install -g @anthropic-ai/claude-code

# Install Caddy for HTTPS
apt-get install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
apt-get update && apt-get install -y caddy

echo "PROVISIONING_COMPLETE" > /root/.provisioning_status
"""
