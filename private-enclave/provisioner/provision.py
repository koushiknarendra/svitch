"""
Svitch Enclave Provisioner

Provisions a bare GPU server (Lambda Labs, RunPod, or any Ubuntu 22.04 box)
into a fully configured Svitch Private Enclave in one command.

What it does:
  1. SSH into the server
  2. Install Docker, NVIDIA Container Toolkit, WireGuard
  3. Pull and start vLLM with the requested model
  4. Deploy the Svitch inference server (PII Shield + Audit Tracer)
  5. Configure WireGuard and return the customer's connection config

Usage:
    python provision.py \\
        --host 203.0.113.42 \\
        --customer razorbank \\
        --model llama-3.1-8b-instruct \\
        --ssh-key ~/.ssh/id_rsa

    # Or use environment variables
    SVITCH_HOST=203.0.113.42 \\
    SVITCH_CUSTOMER=razorbank \\
    python provision.py
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

# ── Models ────────────────────────────────────────────────────────────────────
SUPPORTED_MODELS = {
    "llama-3.1-8b-instruct":  "meta-llama/Llama-3.1-8B-Instruct",
    "llama-3.1-70b-instruct": "meta-llama/Llama-3.1-70B-Instruct",
    "mistral-7b-instruct":    "mistralai/Mistral-7B-Instruct-v0.3",
    "gemma-2-9b-instruct":    "google/gemma-2-9b-it",
    "phi-3-mini":             "microsoft/Phi-3-mini-4k-instruct",
}

# ── Remote commands ───────────────────────────────────────────────────────────
INSTALL_SCRIPT = r"""#!/bin/bash
set -e

echo "[svitch] Installing Docker..."
apt-get update -qq
apt-get install -y -qq curl git wireguard

if ! command -v docker &>/dev/null; then
    curl -fsSL https://get.docker.com | bash
fi

echo "[svitch] Installing NVIDIA Container Toolkit..."
if command -v nvidia-smi &>/dev/null; then
    distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
        gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
    curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
        sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
        tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
    apt-get update -qq
    apt-get install -y -qq nvidia-container-toolkit
    nvidia-ctk runtime configure --runtime=docker
    systemctl restart docker
    echo "[svitch] GPU detected and configured"
else
    echo "[svitch] No GPU detected — running in CPU mode (inference will be slow)"
fi

echo "[svitch] Docker ready: $(docker --version)"
"""

DOCKER_COMPOSE_TEMPLATE = """\
version: "3.9"

services:
  vllm:
    image: vllm/vllm-openai:latest
    runtime: {runtime}
    shm_size: "8g"
    volumes:
      - ~/.cache/huggingface:/root/.cache/huggingface
    environment:
      - HUGGING_FACE_HUB_TOKEN={hf_token}
    command: >
      --model {hf_model}
      --served-model-name {model_name}
      --max-model-len 8192
      --dtype auto
    ports:
      - "8000:8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 10
      start_period: 120s

  svitch-inference:
    image: python:3.12-slim
    working_dir: /app
    volumes:
      - ./svitch:/app
    environment:
      - VLLM_BASE_URL=http://vllm:8000
      - DEFAULT_MODEL={model_name}
      - ENCLAVE_ID={enclave_id}
      - PII_MODE=redact
      - TRACER_ENABLED=true
      - SVITCH_DB_PATH=/app/audit.db
    command: >
      sh -c "pip install -q fastapi uvicorn httpx &&
             uvicorn server:app --host 0.0.0.0 --port 8080"
    ports:
      - "8080:8080"
    depends_on:
      vllm:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 15s
      timeout: 5s
      retries: 5
"""

WIREGUARD_SERVER_TEMPLATE = """\
[Interface]
PrivateKey = {server_priv}
Address = 10.8.0.1/24
ListenPort = 51820

PostUp   = iptables -t nat -A PREROUTING -i wg0 -p tcp --dport 8080 -j DNAT --to-destination 127.0.0.1:8080
PostUp   = iptables -A FORWARD -i wg0 -j ACCEPT
PostDown = iptables -t nat -D PREROUTING -i wg0 -p tcp --dport 8080 -j DNAT --to-destination 127.0.0.1:8080
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT

[Peer]
PublicKey = {client_pub}
AllowedIPs = 10.8.0.2/32
"""

WIREGUARD_CLIENT_TEMPLATE = """\
# Svitch Enclave — {customer}
# wg-quick up svitch

[Interface]
PrivateKey = {client_priv}
Address = 10.8.0.2/32
DNS = 1.1.1.1

[Peer]
PublicKey = {server_pub}
Endpoint = {server_ip}:51820
AllowedIPs = 10.8.0.1/32
PersistentKeepalive = 25
"""


# ── SSH helpers ───────────────────────────────────────────────────────────────

def _ssh(host: str, cmd: str, key: str | None = None, user: str = "ubuntu") -> str:
    ssh_args = [
        "ssh",
        "-o", "StrictHostKeyChecking=no",
        "-o", "BatchMode=yes",
    ]
    if key:
        ssh_args += ["-i", key]
    ssh_args.append(f"{user}@{host}")
    ssh_args.append(cmd)
    result = subprocess.run(ssh_args, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(f"SSH command failed:\n{result.stderr}")
    return result.stdout.strip()


def _scp(host: str, local: str, remote: str, key: str | None = None, user: str = "ubuntu"):
    scp_args = ["scp", "-o", "StrictHostKeyChecking=no"]
    if key:
        scp_args += ["-i", key]
    scp_args += [local, f"{user}@{host}:{remote}"]
    subprocess.run(scp_args, check=True, timeout=60)


# ── Keypair generation (no wg binary needed on local machine) ─────────────────

def _gen_keypair_remote(host: str, key: str | None, user: str) -> tuple[str, str]:
    priv = _ssh(host, "wg genkey", key, user)
    pub  = _ssh(host, f"echo '{priv}' | wg pubkey", key, user)
    return priv, pub


# ── Main provision ────────────────────────────────────────────────────────────

def provision(
    host: str,
    customer: str,
    model: str = "llama-3.1-8b-instruct",
    ssh_key: str | None = None,
    ssh_user: str = "ubuntu",
    hf_token: str = "",
    output_dir: Path = Path("provisioned"),
):
    hf_model = SUPPORTED_MODELS.get(model)
    if not hf_model:
        raise ValueError(f"Unknown model '{model}'. Supported: {list(SUPPORTED_MODELS)}")

    enclave_id = f"svitch-{customer}"
    out = output_dir / customer
    out.mkdir(parents=True, exist_ok=True)

    print(f"\n{'═'*56}")
    print(f"  Svitch Enclave Provisioner")
    print(f"  Customer : {customer}")
    print(f"  Host     : {host}")
    print(f"  Model    : {model} ({hf_model})")
    print(f"{'═'*56}\n")

    # ── Step 1: Install dependencies ──────────────────────────────────────────
    print("[1/5] Installing Docker + WireGuard + NVIDIA toolkit...")
    _ssh(host, f"bash -s << 'EOF'\n{INSTALL_SCRIPT}\nEOF", ssh_key, ssh_user)
    print("      Done.")

    # ── Step 2: Detect GPU ────────────────────────────────────────────────────
    print("[2/5] Detecting GPU...")
    try:
        gpu_info = _ssh(host, "nvidia-smi --query-gpu=name --format=csv,noheader", ssh_key, ssh_user)
        runtime = "nvidia"
        print(f"      GPU: {gpu_info.splitlines()[0]}")
    except Exception:
        runtime = "runc"
        print("      No GPU — CPU mode (suitable for testing, not production)")

    # ── Step 3: Upload inference server ───────────────────────────────────────
    print("[3/5] Uploading Svitch inference stack...")
    _ssh(host, "mkdir -p ~/svitch/pii-shield/service/detectors ~/svitch/agent-tracer/svitch_tracer", ssh_key, ssh_user)

    repo_root = Path(__file__).parent.parent.parent
    for local, remote in [
        (repo_root / "private-enclave/inference/server.py",      "~/svitch/server.py"),
        (repo_root / "pii-shield/service/detectors",             "~/svitch/pii-shield/service/"),
        (repo_root / "pii-shield/service/requirements.txt",      "~/svitch/pii-shield/service/requirements.txt"),
        (repo_root / "agent-tracer/svitch_tracer",               "~/svitch/agent-tracer/"),
    ]:
        if Path(local).exists():
            _scp(host, str(local), remote, ssh_key, ssh_user)

    # Write docker-compose.yml
    dc = DOCKER_COMPOSE_TEMPLATE.format(
        runtime=runtime,
        hf_model=hf_model,
        model_name=model,
        hf_token=hf_token,
        enclave_id=enclave_id,
    )
    dc_path = out / "docker-compose.yml"
    dc_path.write_text(dc)
    _scp(host, str(dc_path), "~/docker-compose.yml", ssh_key, ssh_user)
    print("      Done.")

    # ── Step 4: Start services ────────────────────────────────────────────────
    print(f"[4/5] Starting vLLM ({model}) and Svitch inference server...")
    print("      (Model download may take 5–20 minutes the first time)")
    _ssh(host, "cd ~ && docker compose up -d", ssh_key, ssh_user)
    print("      Services started. Waiting for health checks...")

    for attempt in range(1, 25):
        time.sleep(15)
        try:
            result = _ssh(host, "curl -sf http://localhost:8080/health", ssh_key, ssh_user)
            if "ok" in result:
                print(f"      Svitch inference server healthy after {attempt * 15}s")
                break
        except Exception:
            print(f"      Still starting... ({attempt * 15}s)")
    else:
        print("      Warning: health check timed out. Check 'docker compose logs' on the server.")

    # ── Step 5: Configure WireGuard ───────────────────────────────────────────
    print("[5/5] Configuring WireGuard tunnel...")
    server_priv, server_pub = _gen_keypair_remote(host, ssh_key, ssh_user)

    # Generate client keypair locally using the server's wg binary via SSH
    client_priv, client_pub = _gen_keypair_remote(host, ssh_key, ssh_user)

    server_wg = WIREGUARD_SERVER_TEMPLATE.format(
        server_priv=server_priv,
        client_pub=client_pub,
    )
    client_wg = WIREGUARD_CLIENT_TEMPLATE.format(
        customer=customer,
        client_priv=client_priv,
        server_pub=server_pub,
        server_ip=host,
    )

    # Deploy server WireGuard config
    server_wg_path = out / "server-wg.conf"
    server_wg_path.write_text(server_wg)
    _scp(host, str(server_wg_path), "~/wg0.conf", ssh_key, ssh_user)
    _ssh(host, "cp ~/wg0.conf /etc/wireguard/wg0.conf && wg-quick up wg0 && systemctl enable wg-quick@wg0", ssh_key, ssh_user)

    # Save client config
    client_wg_path = out / "svitch.conf"
    client_wg_path.write_text(client_wg)

    print(f"\n{'═'*56}")
    print(f"  ENCLAVE READY")
    print(f"{'═'*56}")
    print(f"\n  Customer config: {client_wg_path}")
    print(f"  API endpoint   : http://10.8.0.1:8080/v1")
    print(f"\n  Connect:\n")
    print(f"    # 1. Install WireGuard and import {client_wg_path.name}")
    print(f"    wg-quick up svitch\n")
    print(f"    # 2. Point your OpenAI client at the enclave")
    print(f"    import openai")
    print(f"    client = openai.OpenAI(")
    print(f'        base_url="http://10.8.0.1:8080/v1",')
    print(f'        api_key="svitch-enclave",')
    print(f"    )")
    print(f"\n{'═'*56}\n")

    return client_wg_path


def main():
    parser = argparse.ArgumentParser(description="Provision a Svitch Private Enclave")
    parser.add_argument("--host",      default=os.environ.get("SVITCH_HOST"),     help="Server public IP")
    parser.add_argument("--customer",  default=os.environ.get("SVITCH_CUSTOMER"), help="Customer slug")
    parser.add_argument("--model",     default="llama-3.1-8b-instruct",           help="Model to serve")
    parser.add_argument("--ssh-key",   default=os.path.expanduser("~/.ssh/id_rsa"))
    parser.add_argument("--ssh-user",  default="ubuntu")
    parser.add_argument("--hf-token",  default=os.environ.get("HF_TOKEN", ""),    help="HuggingFace token (for gated models)")
    parser.add_argument("--out",       default="provisioned")
    args = parser.parse_args()

    if not args.host:
        print("Error: --host is required (or set SVITCH_HOST env var)")
        sys.exit(1)
    if not args.customer:
        print("Error: --customer is required (or set SVITCH_CUSTOMER env var)")
        sys.exit(1)

    provision(
        host=args.host,
        customer=args.customer,
        model=args.model,
        ssh_key=args.ssh_key,
        ssh_user=args.ssh_user,
        hf_token=args.hf_token,
        output_dir=Path(args.out),
    )


if __name__ == "__main__":
    main()
