"""Private Tailscale-bound remote dashboard for Byparr Manager.

The service deliberately binds to one explicitly configured Tailscale address;
it never binds to 0.0.0.0. Tailscale encrypts traffic between tailnet devices.
Application login and CSRF protection remain mandatory in addition to tailnet ACLs.
"""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import re
import socket
import secrets
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse


DEFAULT_REMOTE_PORT = 8765
PASSWORD_ITERATIONS = 600_000
SESSION_SECONDS = 30 * 60


def validate_tailscale_binding(host: str, port: str | int) -> tuple[str, int]:
    """Accept only an address in Tailscale's CGNAT IPv4 or ULA IPv6 ranges."""
    try:
        address = ipaddress.ip_address(host.strip())
        number = int(port)
    except (ValueError, TypeError) as error:
        raise ValueError("Enter a valid Tailscale IP address and port.") from error

    allowed = (
        address.version == 4 and address in ipaddress.ip_network("100.64.0.0/10")
    ) or (
        address.version == 6
        and address in ipaddress.ip_network("fd7a:115c:a1e0::/48")
    )
    if not allowed:
        raise ValueError(
            "For safety, the remote dashboard must bind to this device's Tailscale IP."
        )
    if not 1 <= number <= 65535:
        raise ValueError("Port must be between 1 and 65535.")
    return str(address), number


def password_verifier(password: str, salt: bytes | None = None) -> tuple[str, str]:
    """Create a salted PBKDF2-HMAC-SHA256 verifier; never persist the password."""
    if len(password) < 14:
        raise ValueError("Choose a password with at least 14 characters.")
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS
    )
    return salt.hex(), digest.hex()


def verify_password(password: str, salt_hex: str, verifier_hex: str) -> bool:
    try:
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(verifier_hex)
    except ValueError:
        return False
    actual = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS
    )
    return hmac.compare_digest(actual, expected)


class RemoteDashboardServer:
    """Small authenticated HTTP dashboard, restricted to a configured Tailscale IP."""

    def __init__(self, host, port, username, salt, verifier, status_provider,
                 action_handler, log_provider=None, audit_logger=None):
        self.host, self.port = validate_tailscale_binding(host, port)
        self.username = username
        self.salt = salt
        self.verifier = verifier
        self.status_provider = status_provider
        self.action_handler = action_handler
        self.log_provider = log_provider or (lambda: [])
        self.audit_logger = audit_logger or (lambda _message: None)
        self._sessions = {}
        self._failures = {}
        self._lock = threading.Lock()

    def audit(self, event):
        """Write a credential-free security event to the Manager's normal log."""
        try:
            self.audit_logger(f"[REMOTE ACCESS] {event}")
        except Exception:
            # An audit sink failure must never break authentication or controls.
            pass
        self._server = None
        self._thread = None

    @property
    def running(self):
        return self._server is not None

    def start(self):
        if self.running:
            return
        owner = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "ByparrManagerRemote"
            sys_version = ""

            def log_message(self, _format, *_args):
                return

            def _send(self, status, body, content_type="application/json",
                      headers=None):
                data = body.encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", content_type + "; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("X-Frame-Options", "DENY")
                self.send_header("Referrer-Policy", "no-referrer")
                self.send_header("Content-Security-Policy",
                                 "default-src 'self'; script-src 'self' 'unsafe-inline'; "
                                 "style-src 'self' 'unsafe-inline'; frame-ancestors 'none'")
                self.send_header("Cache-Control", "no-store")
                for key, value in (headers or {}).items():
                    self.send_header(key, value)
                self.end_headers()
                self.wfile.write(data)

            def _json(self, status, payload, headers=None):
                self._send(status, json.dumps(payload), headers=headers)

            def _body(self):
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if length > 8192:
                        return None
                    return json.loads(self.rfile.read(length) or b"{}")
                except (ValueError, json.JSONDecodeError):
                    return None

            def _session(self):
                cookie = self.headers.get("Cookie", "")
                token = next((part.split("=", 1)[1] for part in cookie.split("; ")
                              if part.startswith("byparr_session=")), "")
                with owner._lock:
                    session = owner._sessions.get(token)
                    if session and session["expires"] > time.time():
                        session["expires"] = time.time() + SESSION_SECONDS
                        return token, session
                    expired = owner._sessions.pop(token, None)
                    if expired:
                        owner.audit(f"Session expired for user '{owner.username}'.")
                return None, None

            def do_GET(self):
                path = urlparse(self.path).path
                if path == "/":
                    _, session = self._session()
                    self._send(200, DASHBOARD if session else LOGIN_PAGE,
                               "text/html")
                    return
                if path == "/api/status":
                    _, session = self._session()
                    if not session:
                        self._json(HTTPStatus.UNAUTHORIZED, {"error": "Sign in required"})
                        return
                    status = owner.status_provider()
                    status["logs"] = [
                        redact_log_line(line) for line in owner.log_provider()
                    ]
                    self._json(200, status, {"X-CSRF-Token": session["csrf"]})
                    return
                self._json(HTTPStatus.NOT_FOUND, {"error": "Not found"})

            def do_POST(self):
                path = urlparse(self.path).path
                if path == "/login":
                    payload = self._body()
                    if not isinstance(payload, dict):
                        self._json(400, {"error": "Invalid request"})
                        return
                    address = self.client_address[0]
                    now = time.time()
                    with owner._lock:
                        failures = [stamp for stamp in owner._failures.get(address, [])
                                    if now - stamp < 300]
                        owner._failures[address] = failures
                    valid = (
                        payload.get("username") == owner.username
                        and isinstance(payload.get("password"), str)
                        and verify_password(payload["password"], owner.salt,
                                            owner.verifier)
                    )
                    if not valid or len(failures) >= 5:
                        if not valid:
                            with owner._lock:
                                owner._failures[address].append(now)
                            owner.audit(
                                f"Login failed for username '{owner.username}' from {address}."
                            )
                        else:
                            owner.audit(f"Login rate limit blocked {address}.")
                        self._json(401, {"error": "Sign-in failed. Check your details or wait."})
                        return
                    token = secrets.token_urlsafe(32)
                    csrf = secrets.token_urlsafe(24)
                    with owner._lock:
                        owner._sessions[token] = {
                            "csrf": csrf, "expires": now + SESSION_SECONDS
                        }
                        owner._failures.pop(address, None)
                    owner.audit(f"Login successful for user '{owner.username}' from {address}.")
                    self._json(200, {"ok": True}, {
                        "Set-Cookie": f"byparr_session={token}; HttpOnly; SameSite=Strict; "
                                      "Path=/; Max-Age=1800"
                    })
                    return

                token, session = self._session()
                if not session:
                    self._json(401, {"error": "Sign in required"})
                    return
                if not hmac.compare_digest(
                    self.headers.get("X-CSRF-Token", ""), session["csrf"]
                ):
                    self._json(403, {"error": "Request verification failed"})
                    return
                payload = self._body()
                if path == "/logout":
                    with owner._lock:
                        owner._sessions.pop(token, None)
                    owner.audit(
                        f"Logout for user '{owner.username}' from {self.client_address[0]}."
                    )
                    self._json(200, {"ok": True}, {
                        "Set-Cookie": "byparr_session=; HttpOnly; SameSite=Strict; "
                                      "Path=/; Max-Age=0"
                    })
                    return
                if path == "/api/action" and isinstance(payload, dict):
                    action = payload.get("action")
                    if action not in {"start", "stop", "restart", "browser-health", "check-integrations"}:
                        self._json(400, {"error": "Unsupported action"})
                        return
                    owner.audit(
                        f"User '{owner.username}' from {self.client_address[0]} requested '{action}'."
                    )
                    owner.action_handler(action)
                    self._json(202, {"ok": True})
                    return
                self._json(HTTPStatus.NOT_FOUND, {"error": "Not found"})

        server_type = ThreadingHTTPServer
        if ":" in self.host:
            class IPv6ThreadingHTTPServer(ThreadingHTTPServer):
                address_family = socket.AF_INET6
            server_type = IPv6ThreadingHTTPServer
        self._server = server_type((self.host, self.port), Handler)
        self._server.daemon_threads = True
        self._thread = threading.Thread(target=self._server.serve_forever,
                                        name="ByparrRemoteDashboard", daemon=True)
        self._thread.start()

    def stop(self):
        server, self._server = self._server, None
        if server:
            server.shutdown()
            server.server_close()
        with self._lock:
            self._sessions.clear()
        self.audit("Remote dashboard stopped; active sessions cleared.")


def redact_log_line(value):
    """Mask common credential fields before logs leave the Windows desktop."""
    line = str(value)
    line = re.sub(
        r"(?i)(api[_-]?key|password|token|cookie|authorization)(\s*[:=]\s*)[^\s,;]+",
        r"\1\2[REDACTED]",
        line,
    )
    return line[:2000]


LOGIN_PAGE = """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Byparr Manager — Sign in</title><style>
body{margin:0;background:#10141c;color:#edf2fb;font:16px Arial;display:grid;
min-height:100vh;place-items:center}.card{background:#1a2230;padding:32px;border-radius:14px;
width:min(360px,calc(100% - 64px));border:1px solid #2b3749}h1{color:#8daaff}
input,button{box-sizing:border-box;width:100%;padding:12px;margin:8px 0;border-radius:7px;
border:1px solid #35445b;background:#131a25;color:#fff}button{background:#4169e1;
cursor:pointer;font-weight:bold}#error{color:#ff9292}</style>
<div class="card"><h1>BYPARR</h1><h2>Remote Manager</h2>
<p>Sign in to your private Byparr Manager dashboard.</p>
<form id="login"><input name="username" autocomplete="username" placeholder="Username" required>
<input name="password" type="password" autocomplete="current-password" placeholder="Password" required>
<button>Sign in</button></form><p id="error" role="alert"></p></div>
<script>document.querySelector('#login').onsubmit=async e=>{e.preventDefault();
const f=new FormData(e.target);const r=await fetch('/login',{method:'POST',
headers:{'Content-Type':'application/json'},body:JSON.stringify({username:f.get('username'),
password:f.get('password')})});if(r.ok)location.href='/';else document.querySelector('#error').textContent=
(await r.json()).error;};</script></html>"""


DASHBOARD = """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Byparr Manager — Remote Dashboard</title><style>
body{margin:0;background:#10141c;color:#edf2fb;font:15px Arial;padding:24px}
main{max-width:900px;margin:auto}h1{color:#8daaff}.panel{background:#1a2230;border:1px solid #2b3749;
border-radius:12px;padding:20px;margin:16px 0}button{background:#4169e1;color:white;border:0;
padding:11px 16px;border-radius:7px;margin:4px;cursor:pointer}pre{white-space:pre-wrap;
overflow-wrap:anywhere;color:#b8c5d8;max-height:360px;overflow:auto}</style>
<main><h1>BYPARR MANAGER</h1><p>Private remote dashboard</p><section class="panel">
<h2>Engine</h2><p id="engine">Loading…</p><p id="api"></p><p id="browser"></p>
<p id="prowlarr"></p><p id="qbittorrent"></p>
<button onclick="act('start')">Start engine</button><button onclick="act('restart')">Restart</button>
<button onclick="act('stop')">Stop</button><button onclick="act('browser-health')">Browser Health</button>
<button onclick="act('check-integrations')">Check Prowlarr + qBittorrent</button></section>
<section class="panel"><h2>Recent logs</h2>
<pre id="logs">Loading…</pre></section><button onclick="logout()">Sign out</button>
</main><script>let csrf='';async function refresh(){const r=await fetch('/api/status');
if(r.status===401){location.reload();return}const d=await r.json();csrf=r.headers.get('X-CSRF-Token')||csrf;
document.querySelector('#engine').textContent=d.engine||'Unknown';
document.querySelector('#api').textContent=d.api||'';
document.querySelector('#browser').textContent='Browser health: '+(d.browser||'Not checked');
document.querySelector('#prowlarr').textContent='Prowlarr: '+(d.prowlarr||'Not checked');
document.querySelector('#qbittorrent').textContent='qBittorrent: '+(d.qbittorrent||'Not checked');
document.querySelector('#logs').textContent=(d.logs||[]).join('\n');}
async function act(action){await fetch('/api/action',{method:'POST',headers:{
'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify({action})});
setTimeout(refresh,700)}async function logout(){await fetch('/logout',{method:'POST',
headers:{'X-CSRF-Token':csrf}});location.reload()}refresh();setInterval(refresh,5000);</script></html>"""
