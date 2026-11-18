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
                 action_handler, log_provider=None, audit_logger=None, search_handler=None):
        self.host, self.port = validate_tailscale_binding(host, port)
        self.username = username
        self.salt = salt
        self.verifier = verifier
        self.status_provider = status_provider
        self.action_handler = action_handler
        self.log_provider = log_provider or (lambda: [])
        self.audit_logger = audit_logger or (lambda _message: None)
        self.search_handler = search_handler or (lambda _query: [])
        self._searches = []
        self._sessions = {}
        self._failures = {}
        self._lock = threading.Lock()
        self._server = None
        self._thread = None

    def audit(self, event):
        """Write a credential-free security event to the Manager's normal log."""
        try:
            self.audit_logger(f"[REMOTE ACCESS] {event}")
        except (RuntimeError, TypeError):
            # An audit sink failure must never break authentication or controls.
            return

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
                    try:
                        status = owner.status_provider()
                        status["logs"] = [
                            redact_log_line(line) for line in owner.log_provider()
                        ]
                        status["searches"] = owner._searches[-10:]
                    except (RuntimeError, OSError, ValueError, TypeError) as error:
                        owner.audit(
                            f"Dashboard status request failed: {type(error).__name__}."
                        )
                        self._json(500, {"error": "Windows Manager could not prepare dashboard status."})
                        return
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
                    attempted_username = payload.get("username", "")
                    if not isinstance(attempted_username, str):
                        attempted_username = ""
                    attempted_username = "".join(
                        char for char in attempted_username[:64] if char.isprintable()
                    )
                    valid = (
                        attempted_username == owner.username
                        and isinstance(payload.get("password"), str)
                        and verify_password(payload["password"], owner.salt,
                                            owner.verifier)
                    )
                    if not valid or len(failures) >= 5:
                        if not valid:
                            with owner._lock:
                                owner._failures[address].append(now)
                            owner.audit(
                                f"Login failed for username '{attempted_username}' from {address}."
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
                if path == "/api/search":
                    query = payload.get("query") if isinstance(payload, dict) else None
                    if not isinstance(query, str):
                        self._json(400, {"error": "Enter a search term."})
                        return
                    query = query.strip()
                    if len(query) < 2 or len(query) > 120 or any(ord(c) < 32 for c in query):
                        self._json(400, {"error": "Search terms must be 2–120 characters."})
                        return
                    try:
                        results = owner.search_handler(query)
                        if not isinstance(results, list):
                            raise ValueError("Unexpected search response")
                    except (RuntimeError, OSError, ValueError, TypeError):
                        owner.audit(
                            f"Prowlarr search failed for user '{owner.username}' from {self.client_address[0]}."
                        )
                        self._json(502, {"error": "Prowlarr search failed. Check the Prowlarr connection and API key."})
                        return
                    entry = {
                        "query": query,
                        "count": len(results),
                        "results": results[:50],
                        "searched_at": time.strftime("%H:%M:%S"),
                    }
                    owner._searches.append(entry)
                    owner._searches = owner._searches[-10:]
                    owner.audit(
                        f"Prowlarr search completed for user '{owner.username}' from {self.client_address[0]} ({len(results)} results)."
                    )
                    self._json(200, entry)
                    return
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
overflow-wrap:anywhere;color:#b8c5d8;max-height:360px;overflow:auto}
input{box-sizing:border-box;width:100%;padding:13px;border-radius:7px;border:1px solid #35445b;background:#131a25;color:#fff}
.result{border-top:1px solid #2b3749;padding:12px 0}.result strong{display:block;overflow-wrap:anywhere}
.muted{color:#9aa7ba;font-size:13px}#search-message{color:#9aa7ba}</style>
<main><h1>BYPARR MANAGER</h1><p>Private remote dashboard</p><section class="panel">
<h2>Engine</h2><p id="updated" aria-live="polite">Waiting for live status…</p><p id="engine" aria-live="polite">Loading…</p><p id="api"></p><p id="browser"></p>
<p id="prowlarr"></p><p id="qbittorrent"></p>
<button onclick="act('start')">Start engine</button><button onclick="act('restart')">Restart</button>
<button onclick="act('stop')">Stop</button><button onclick="act('browser-health')">Browser Health</button>
<button onclick="act('check-integrations')">Check Prowlarr + qBittorrent</button></section>
<section class="panel"><h2>Prowlarr Search</h2>
<p class="muted">Search your configured Prowlarr indexers and view results here on your iPad.</p>
<form id="search-form"><input id="search-query" name="query" minlength="2" maxlength="120" placeholder="Enter a title or search term" required>
<button type="submit">Search Prowlarr</button></form><p id="search-message" aria-live="polite">Search results will appear here.</p>
<div id="search-results"></div><h3>Recent searches</h3><div id="search-history" class="muted">No searches yet.</div>
</section>
<section class="panel"><h2>Recent logs</h2>
<pre id="logs">Loading…</pre></section><button onclick="logout()">Sign out</button>
</main><script>let csrf='';async function refresh(){try{const r=await fetch('/api/status',{cache:'no-store',credentials:'same-origin'});
if(r.status===401){location.reload();return}const d=await r.json();if(!r.ok)throw new Error(d.error||('HTTP '+r.status));csrf=r.headers.get('X-CSRF-Token')||csrf;
document.querySelector('#engine').textContent=d.engine||'Unknown';
document.querySelector('#api').textContent=d.api||'';
document.querySelector('#browser').textContent='Browser health: '+(d.browser||'Not checked');
document.querySelector('#prowlarr').textContent='Prowlarr: '+(d.prowlarr||'Not checked');
document.querySelector('#qbittorrent').textContent='qBittorrent: '+(d.qbittorrent||'Not checked');
document.querySelector('#logs').textContent=(Array.isArray(d.logs)?d.logs:[]).join(String.fromCharCode(10));
renderSearchHistory(d.searches||[]);
document.querySelector('#updated').textContent='Live status updated: '+new Date().toLocaleTimeString();
}catch(error){const message='Dashboard data unavailable: '+(error&&error.message?error.message:'network or browser error');
document.querySelector('#updated').textContent='Status refresh failed';document.querySelector('#engine').textContent=message;document.querySelector('#api').textContent='Check that the Windows Manager is still running and remote access is enabled.';
document.querySelector('#logs').textContent=message;}}
function renderSearchResults(entry){const target=document.querySelector('#search-results');target.replaceChildren();
if(!entry||!Array.isArray(entry.results)||!entry.results.length){target.textContent='No results returned.';return;}
for(const item of entry.results){const card=document.createElement('div');card.className='result';
const title=document.createElement('strong');title.textContent=item.title||'Untitled release';card.appendChild(title);
const meta=document.createElement('div');meta.className='muted';
const parts=[item.indexer||'Unknown indexer',item.size_label||'Size unknown',
'Seeds: '+(item.seeders??'—'),'Peers: '+(item.leechers??'—'),item.protocol||''];
meta.textContent=parts.filter(Boolean).join(' · ');card.appendChild(meta);target.appendChild(card);}}
function renderSearchHistory(items){const target=document.querySelector('#search-history');target.replaceChildren();
if(!Array.isArray(items)||!items.length){target.textContent='No searches yet.';return;}
for(const item of [...items].reverse()){const b=document.createElement('button');b.type='button';b.textContent=item.query+' ('+item.count+')';
b.addEventListener('click',()=>{document.querySelector('#search-query').value=item.query;renderSearchResults(item);document.querySelector('#search-message').textContent='Previous results · '+item.searched_at;});target.appendChild(b);}}
document.querySelector('#search-form').addEventListener('submit',async event=>{event.preventDefault();
const query=document.querySelector('#search-query').value.trim();const message=document.querySelector('#search-message');
message.textContent='Searching Prowlarr…';try{const r=await fetch('/api/search',{method:'POST',credentials:'same-origin',
headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify({query})});
const data=await r.json();if(!r.ok)throw new Error(data.error||('HTTP '+r.status));
renderSearchResults(data);message.textContent='Found '+data.count+' results for “'+data.query+'”.';
}catch(error){message.textContent='Search failed: '+error.message;renderSearchResults(null);}});
async function act(action){try{const r=await fetch('/api/action',{method:'POST',credentials:'same-origin',headers:{
'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify({action})});if(!r.ok)throw new Error('HTTP '+r.status);setTimeout(refresh,700)}
catch(error){document.querySelector('#engine').textContent='Action failed: '+error.message;}}
async function logout(){await fetch('/logout',{method:'POST',credentials:'same-origin',headers:{'X-CSRF-Token':csrf}});location.reload()}refresh();setInterval(refresh,5000);</script></html>"""
