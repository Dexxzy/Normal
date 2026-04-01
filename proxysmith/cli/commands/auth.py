"""proxysmith auth — scaffolding for authentication setup."""

from __future__ import annotations

import base64
import hashlib
import os
import secrets
import string
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from proxysmith.core.errors import ConfigError, ValidationError
from proxysmith.core.parser import load_config

console = Console()

app = typer.Typer(
    name="auth",
    help="Authentication scaffolding — generate htpasswd entries, forward-auth snippets.",
    no_args_is_help=True,
)

_DEFAULT_CONFIG = Path("proxysmith.toml")


# --------------------------------------------------------------------------- #
# auth list                                                                    #
# --------------------------------------------------------------------------- #


@app.command("list")
def auth_list(
    config: Path = typer.Option(_DEFAULT_CONFIG, "--config", "-c", help="proxysmith.toml path"),
) -> None:
    """Show auth mode for every service defined in proxysmith.toml."""
    try:
        cfg = load_config(config)
    except (ConfigError, ValidationError) as exc:
        console.print(f"[bold red]✗[/bold red] {exc}")
        raise typer.Exit(1)

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("service", style="cyan")
    table.add_column("subdomain")
    table.add_column("auth mode")
    table.add_column("notes", style="dim")

    for svc in cfg.services:
        auth = svc.auth.value
        if auth == "none":
            color, note = "dim", "publicly accessible"
        elif auth == "basic":
            color, note = "yellow", "requires htpasswd file"
        else:
            color, note = "green", "requires forward-auth middleware"

        table.add_row(
            svc.name,
            f"{svc.subdomain}.{cfg.global_.domain}",
            f"[{color}]{auth}[/{color}]",
            note,
        )

    console.print(table)


# --------------------------------------------------------------------------- #
# auth generate                                                                #
# --------------------------------------------------------------------------- #


@app.command("generate")
def auth_generate(
    username: str = typer.Argument(..., help="Username to add"),
    password: str = typer.Option(
        None,
        "--password",
        "-p",
        help="Password (omit to auto-generate a strong one)",
    ),
    output: Path = typer.Option(
        None,
        "--out",
        "-o",
        help="Write htpasswd entry to this file (appends). Prints to stdout if omitted.",
    ),
) -> None:
    """Generate an htpasswd entry for HTTP Basic Auth.

    The entry uses APR1-MD5 format, compatible with Nginx and Apache.

    Example:
        proxysmith auth generate admin --out /etc/nginx/htpasswd/ollama
    """
    if not password:
        password = _random_password(20)
        console.print(
            f"[bold]Generated password:[/bold] [cyan]{password}[/cyan]  "
            "[dim](save this — it cannot be recovered)[/dim]\n"
        )

    entry = _apr1_md5(username, password)

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        # Append (htpasswd files can have multiple users)
        with output.open("a", encoding="utf-8") as fh:
            fh.write(entry + "\n")
        console.print(f"[green]✓[/green] Appended entry for [bold]{username}[/bold] → {output}")
    else:
        console.print(Panel(entry, title=f"htpasswd entry — {username}", expand=False))
        console.print(
            "\n[dim]Paste into your htpasswd file or use with:[/dim]\n"
            "  Nginx:  auth_basic_user_file /etc/nginx/htpasswd/<service>\n"
            "  Caddy:  basicauth * { ... }\n"
            "  Traefik: traefik.http.middlewares.<name>.basicauth.users\n"
        )


# --------------------------------------------------------------------------- #
# auth forward                                                                 #
# --------------------------------------------------------------------------- #


@app.command("forward")
def auth_forward(
    provider: str = typer.Argument(
        "authelia",
        help="Forward-auth provider: authelia or authentik",
    ),
    config: Path = typer.Option(_DEFAULT_CONFIG, "--config", "-c"),
    target: str = typer.Option(
        "nginx",
        "--target",
        "-t",
        help="Proxy backend to show snippets for: nginx, caddy, or traefik",
    ),
) -> None:
    """Show forward-auth configuration snippets for Authelia or Authentik.

    Reads your proxysmith.toml to use the correct domain.
    """
    provider = provider.lower()
    if provider not in ("authelia", "authentik"):
        console.print("[bold red]✗[/bold red] provider must be 'authelia' or 'authentik'")
        raise typer.Exit(1)

    try:
        cfg = load_config(config)
    except (ConfigError, ValidationError) as exc:
        console.print(f"[bold red]✗[/bold red] {exc}")
        raise typer.Exit(1)

    domain = cfg.global_.domain

    if provider == "authelia":
        _show_authelia_snippets(domain, target)
    else:
        _show_authentik_snippets(domain, target)


# --------------------------------------------------------------------------- #
# Internal helpers                                                             #
# --------------------------------------------------------------------------- #


def _random_password(length: int = 20) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _apr1_md5(username: str, password: str) -> str:
    """Compute an Apache APR1-MD5 password hash for htpasswd files.

    This is a pure-Python implementation of the APR1 algorithm so that
    ProxySmith has no dependency on the ``passlib`` library.
    """
    salt = _random_password(8)[:8]  # APR1 uses 8-char salt
    magic = b"$apr1$"
    salt_b = salt.encode()
    pw_b = password.encode()

    # Step 1 — "A" digest
    a = hashlib.md5(pw_b + magic + salt_b)

    # Step 2 — "B" digest
    b = hashlib.md5(pw_b + salt_b + pw_b).digest()

    # Step 3 — mix B into A
    pw_len = len(pw_b)
    for i in range(pw_len // 16):
        a.update(b)
    a.update(b[: pw_len % 16])

    # Step 4 — bit-mixing loop
    n = pw_len
    while n:
        if n & 1:
            a.update(b"\x00")
        else:
            a.update(pw_b[:1])
        n >>= 1

    a_digest = a.digest()

    # Step 5 — 1000 rounds
    for i in range(1000):
        c = hashlib.md5()
        if i & 1:
            c.update(pw_b)
        else:
            c.update(a_digest)
        if i % 3:
            c.update(salt_b)
        if i % 7:
            c.update(pw_b)
        if i & 1:
            c.update(a_digest)
        else:
            c.update(pw_b)
        a_digest = c.digest()

    # Step 6 — custom base64 encoding (APR1 byte order)
    order = [
        (0, 6, 12), (1, 7, 13), (2, 8, 14), (3, 9, 15), (4, 10, 5)
    ]
    b64_chars = "./0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

    result = []
    for i0, i1, i2 in order:
        v = (a_digest[i0] << 16) | (a_digest[i1] << 8) | a_digest[i2]
        for _ in range(4):
            result.append(b64_chars[v & 0x3F])
            v >>= 6

    # Last byte (11) encodes into 2 chars
    v = a_digest[11]
    result.append(b64_chars[v & 0x3F])
    result.append(b64_chars[(v >> 6) & 0x3F])

    hash_str = "".join(result)
    return f"{username}:$apr1${salt}${hash_str}"


def _show_authelia_snippets(domain: str, target: str) -> None:
    console.print("\n[bold cyan]Authelia Forward Auth Setup[/bold cyan]\n")

    if target == "nginx":
        snippet = f"""\
# 1. Add to your main nginx.conf (http block):
#    upstream authelia {{ server authelia:9091; }}

# 2. Create /etc/nginx/snippets/authelia-auth.conf:
auth_request        /authelia;
auth_request_set    $user   $upstream_http_remote_user;
auth_request_set    $groups $upstream_http_remote_groups;
proxy_set_header    Remote-User   $user;
proxy_set_header    Remote-Groups $groups;

location /authelia {{
    internal;
    proxy_pass              http://authelia/api/verify;
    proxy_set_header        Host                $host;
    proxy_set_header        X-Original-URL      $scheme://$http_host$request_uri;
    proxy_set_header        X-Forwarded-For     $remote_addr;
    proxy_pass_request_body off;
    proxy_set_header        Content-Length      "";
}}

# 3. In each protected server block:
#    include snippets/authelia-auth.conf;
"""
    elif target == "caddy":
        snippet = f"""\
# In each protected Caddyfile site block:
forward_auth authelia:9091 {{
    uri /api/verify?rd=https://auth.{domain}
    copy_headers Remote-User Remote-Groups Remote-Name Remote-Email
}}
"""
    else:  # traefik
        snippet = f"""\
# In your Traefik static config (traefik.yml):
entryPoints:
  web:
    address: ":80"
  websecure:
    address: ":443"

# In your Docker Compose (authelia service):
authelia:
  image: authelia/authelia
  labels:
    - "traefik.enable=true"
    - "traefik.http.routers.authelia.rule=Host(`auth.{domain}`)"
    - "traefik.http.routers.authelia.entrypoints=websecure"
    - "traefik.http.routers.authelia.tls.certresolver=letsencrypt"

# Middleware definition (file provider or labels):
http:
  middlewares:
    authelia:
      forwardAuth:
        address: "http://authelia:9091/api/verify?rd=https://auth.{domain}"
        trustForwardHeader: true
        authResponseHeaders:
          - Remote-User
          - Remote-Groups
          - Remote-Name
          - Remote-Email

# Add to any router that needs auth:
#   middlewares:
#     - authelia
#     - your-other-middlewares
"""

    console.print(Syntax(snippet, "nginx" if target == "nginx" else "yaml", theme="ansi_dark"))
    console.print(
        f"\n[dim]Authelia docs: https://www.authelia.com/integration/proxies/{target}/[/dim]\n"
    )


def _show_authentik_snippets(domain: str, target: str) -> None:
    console.print("\n[bold cyan]Authentik Forward Auth Setup[/bold cyan]\n")

    if target == "nginx":
        snippet = f"""\
# Authentik outpost URL — replace <outpost-id> with your outpost UUID
# found in Authentik UI → Applications → Outposts

location /outpost.goauthentik.io {{
    proxy_pass http://authentik:9000/outpost.goauthentik.io;
    proxy_set_header Host $host;
    proxy_set_header X-Original-URL $scheme://$http_host$request_uri;
    add_header Set-Cookie $auth_cookie;
    auth_request_set $auth_cookie $upstream_http_set_cookie;
    proxy_pass_request_body off;
    proxy_set_header Content-Length "";
}}

# In each protected location block:
auth_request     /outpost.goauthentik.io/auth/nginx;
error_page 401 = @goauthentik_proxy_signin;
auth_request_set $auth_cookie $upstream_http_set_cookie;
add_header       Set-Cookie $auth_cookie;

location @goauthentik_proxy_signin {{
    internal;
    add_header Set-Cookie $auth_cookie;
    return 302 /outpost.goauthentik.io/start?rd=$request_uri;
}}
"""
    elif target == "caddy":
        snippet = f"""\
# Per-site forward auth to Authentik embedded outpost:
forward_auth authentik:9000 {{
    uri /outpost.goauthentik.io/auth/caddy
    copy_headers X-Authentik-Username X-Authentik-Groups X-Authentik-Email
    header_up X-Original-URL {{scheme}}://{{host}}{{uri}}
}}
"""
    else:  # traefik
        snippet = f"""\
# Authentik forwardAuth middleware (file provider):
http:
  middlewares:
    authentik:
      forwardAuth:
        address: "http://authentik:9000/outpost.goauthentik.io/auth/traefik"
        trustForwardHeader: true
        authResponseHeaders:
          - X-authentik-username
          - X-authentik-groups
          - X-authentik-email
          - X-authentik-uid

# Add to routers that need auth:
#   middlewares:
#     - authentik
"""

    console.print(Syntax(snippet, "nginx" if target == "nginx" else "yaml", theme="ansi_dark"))
    console.print(
        "\n[dim]Authentik docs: https://docs.goauthentik.io/docs/add-secure-apps/providers/proxy/[/dim]\n"
    )
