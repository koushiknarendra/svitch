"""
Svitch WireGuard Config Generator

Generates a WireGuard server + client keypair configuration for a new
customer enclave. Each customer gets an isolated VPN tunnel.

Usage:
    python gen_config.py --customer acme-fintech --server-ip 10.8.0.1 --client-ip 10.8.0.2
    python gen_config.py --customer razorbank   --server-ip 10.9.0.1 --client-ip 10.9.0.2

Outputs:
    configs/acme-fintech/server.conf   → deploy to the GPU server
    configs/acme-fintech/client.conf   → hand to the customer (one file, connect instantly)
"""

import argparse
import base64
import os
import subprocess
import sys
from pathlib import Path


def _gen_keypair() -> tuple[str, str]:
    """Generate a WireGuard private/public keypair using the wg CLI."""
    try:
        private = subprocess.check_output(["wg", "genkey"]).decode().strip()
        public = subprocess.check_output(["wg", "pubkey"], input=private.encode()).decode().strip()
        return private, public
    except FileNotFoundError:
        # wg not installed — generate keys using Python for portability
        # In production, always use the wg CLI on the actual server.
        import secrets
        import hashlib

        private_bytes = bytearray(secrets.token_bytes(32))
        private_bytes[0] &= 248
        private_bytes[31] &= 127
        private_bytes[31] |= 64
        private_key = base64.b64encode(bytes(private_bytes)).decode()

        # Curve25519 scalar multiplication — simplified for key generation only
        # Real deployments must use wg genkey / wg pubkey
        pub_bytes = _curve25519_base(bytes(private_bytes))
        public_key = base64.b64encode(pub_bytes).decode()
        return private_key, public_key


def _curve25519_base(private: bytes) -> bytes:
    """Minimal Curve25519 base-point scalar multiply. For key preview only."""
    p = (2**255) - 19
    a24 = 121665

    def clamp(k):
        k = bytearray(k)
        k[0] &= 248
        k[31] &= 127
        k[31] |= 64
        return bytes(k)

    def decode_u_coord(u):
        u_list = list(bytearray(u))
        u_list[-1] &= 127
        return int.from_bytes(u_list, "little")

    def encode_u_coord(u):
        return (u % p).to_bytes(32, "little")

    def x25519(k_bytes, u):
        k = int.from_bytes(clamp(k_bytes), "little")
        x_1 = u
        x_2, z_2, x_3, z_3 = 1, 0, u, 1
        swap = 0
        for t in range(254, -1, -1):
            k_t = (k >> t) & 1
            swap ^= k_t
            if swap:
                x_2, x_3 = x_3, x_2
                z_2, z_3 = z_3, z_2
            swap = k_t
            A = (x_2 + z_2) % p
            AA = (A * A) % p
            B = (x_2 - z_2) % p
            BB = (B * B) % p
            E = (AA - BB) % p
            C = (x_3 + z_3) % p
            D = (x_3 - z_3) % p
            DA = (D * A) % p
            CB = (C * B) % p
            x_3 = pow(DA + CB, 2, p)
            z_3 = (x_1 * pow(DA - CB, 2, p)) % p
            x_2 = (AA * BB) % p
            z_2 = (E * (AA + a24 * E)) % p
        if swap:
            x_2, x_3 = x_3, x_2
            z_2, z_3 = z_3, z_2
        return (x_2 * pow(z_2, p - 2, p)) % p

    base_point = 9
    result = x25519(private, base_point)
    return encode_u_coord(result)


def generate(
    customer: str,
    server_public_ip: str,
    server_vpn_ip: str,
    client_vpn_ip: str,
    port: int = 51820,
    enclave_port: int = 8080,
    output_dir: Path = Path("configs"),
) -> tuple[Path, Path]:
    """
    Generate WireGuard server and client configs for a customer enclave.

    Returns (server_conf_path, client_conf_path).
    """
    out = output_dir / customer
    out.mkdir(parents=True, exist_ok=True)

    server_priv, server_pub = _gen_keypair()
    client_priv, client_pub = _gen_keypair()

    # ── Server config ─────────────────────────────────────────────────────────
    server_conf = f"""\
# Svitch Enclave — WireGuard Server
# Customer: {customer}
# Deploy to: /etc/wireguard/wg0.conf on the GPU server

[Interface]
PrivateKey = {server_priv}
Address = {server_vpn_ip}/24
ListenPort = {port}

# Forward traffic from VPN to local Svitch inference server
PostUp   = iptables -t nat -A PREROUTING -i wg0 -p tcp --dport {enclave_port} -j DNAT --to-destination 127.0.0.1:{enclave_port}
PostUp   = iptables -A FORWARD -i wg0 -j ACCEPT
PostDown = iptables -t nat -D PREROUTING -i wg0 -p tcp --dport {enclave_port} -j DNAT --to-destination 127.0.0.1:{enclave_port}
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT

[Peer]
# Customer client
PublicKey = {client_pub}
AllowedIPs = {client_vpn_ip}/32
"""

    # ── Client config ─────────────────────────────────────────────────────────
    client_conf = f"""\
# Svitch Enclave — WireGuard Client
# Customer: {customer}
# Save to /etc/wireguard/svitch.conf and run: wg-quick up svitch
# Or import into WireGuard app on macOS / Windows / iOS / Android

[Interface]
PrivateKey = {client_priv}
Address = {client_vpn_ip}/32
DNS = 1.1.1.1

[Peer]
# Svitch Enclave server
PublicKey = {server_pub}
Endpoint = {server_public_ip}:{port}
AllowedIPs = {server_vpn_ip}/32

# Keeps the tunnel alive through NAT
PersistentKeepalive = 25
"""

    server_path = out / "server.conf"
    client_path = out / "client.conf"
    meta_path   = out / "info.txt"

    server_path.write_text(server_conf)
    client_path.write_text(client_conf)
    meta_path.write_text(f"""\
Svitch Enclave — {customer}
─────────────────────────────────
Server VPN IP : {server_vpn_ip}
Client VPN IP : {client_vpn_ip}
WireGuard port: {port}
Enclave API   : http://{server_vpn_ip}:{enclave_port}/v1
OpenAI endpoint: http://{server_vpn_ip}:{enclave_port}/v1

Connect your app:
    import openai
    client = openai.OpenAI(
        base_url="http://{server_vpn_ip}:{enclave_port}/v1",
        api_key="svitch-enclave",
    )
""")

    print(f"  Server config → {server_path}")
    print(f"  Client config → {client_path}")
    print(f"  Info          → {meta_path}")
    print(f"\n  Customer connects to: http://{server_vpn_ip}:{enclave_port}/v1")

    return server_path, client_path


def main():
    parser = argparse.ArgumentParser(description="Generate Svitch WireGuard configs")
    parser.add_argument("--customer",   required=True, help="Customer slug (e.g. acme-fintech)")
    parser.add_argument("--server-ip",  required=True, help="Public IP of the GPU server")
    parser.add_argument("--server-vpn", default="10.8.0.1", help="Server VPN IP (default 10.8.0.1)")
    parser.add_argument("--client-vpn", default="10.8.0.2", help="Client VPN IP (default 10.8.0.2)")
    parser.add_argument("--port",       default=51820, type=int, help="WireGuard UDP port")
    parser.add_argument("--enclave-port", default=8080, type=int, help="Svitch inference server port")
    parser.add_argument("--out",        default="configs", help="Output directory")
    args = parser.parse_args()

    print(f"\nGenerating WireGuard configs for: {args.customer}\n")
    generate(
        customer=args.customer,
        server_public_ip=args.server_ip,
        server_vpn_ip=args.server_vpn,
        client_vpn_ip=args.client_vpn,
        port=args.port,
        enclave_port=args.enclave_port,
        output_dir=Path(args.out),
    )
    print("\nDone.")


if __name__ == "__main__":
    main()
