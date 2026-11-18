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
    if not isinstance(password, str) or len(password) < 14:
        raise ValueError("Choose a password with at least 14 characters.")
    if len(password) > 1024:
        raise ValueError("Remote dashboard passwords cannot exceed 1024 characters.")
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS
    )
    return salt.hex(), digest.hex()


def verify_password(password: str, salt_hex: str, verifier_hex: str) -> bool:
    if not isinstance(password, str) or len(password) > 1024:
        return False
    try:
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(verifier_hex)
    except (TypeError, ValueError):
        return False
    if len(salt) != 16 or len(expected) != 32:
        return False
    try:
        encoded = password.encode("utf-8")
    except UnicodeEncodeError:
        return False
    actual = hashlib.pbkdf2_hmac(
        "sha256", encoded, salt, PASSWORD_ITERATIONS
    )
    return hmac.compare_digest(actual, expected)


def validate_request_host(host_header: str, host: str, port: int) -> bool:
    """Reject unexpected Host headers to reduce DNS-rebinding exposure."""
    address = f"[{host}]" if ":" in host else host
    return isinstance(host_header, str) and hmac.compare_digest(
        host_header.strip().lower(), f"{address}:{port}".lower()
    )


def validate_request_origin(origin: str, host_header: str) -> bool:
    """Allow only browser POSTs whose Origin exactly matches the request Host."""
    if not isinstance(origin, str) or not isinstance(host_header, str):
        return False
    try:
        parsed = urlparse(origin)
        return (
            parsed.scheme == "http"
            and parsed.netloc.lower() == host_header.strip().lower()
            and parsed.path == ""
            and not parsed.params
            and not parsed.query
            and not parsed.fragment
        )
    except ValueError:
        return False


class RemoteDashboardServer:
    """Small authenticated HTTP dashboard, restricted to a configured Tailscale IP."""

    def __init__(self, host, port, username, salt, verifier, status_provider,
                 action_handler, log_provider=None, audit_logger=None, search_handler=None, grab_handler=None):
        self.host, self.port = validate_tailscale_binding(host, port)
        if not isinstance(username, str) or not re.fullmatch(r"[A-Za-z0-9_.@-]{1,64}", username):
            raise ValueError("Remote dashboard username must be 1–64 safe characters.")
        self.username = username
        self.salt = salt
        self.verifier = verifier
        self.status_provider = status_provider
        self.action_handler = action_handler
        self.log_provider = log_provider or (lambda: [])
        self.audit_logger = audit_logger or (lambda _message: None)
        self.search_handler = search_handler or (lambda _query, _category: [])
        self.grab_handler = grab_handler
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

            def setup(self):
                super().setup()
                self.connection.settimeout(10)

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
                self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
                if not (headers and "Content-Security-Policy" in headers):
                    self.send_header("Content-Security-Policy",
                                     "default-src 'self'; script-src 'self'; "
                                     "style-src 'self' 'unsafe-inline'; frame-ancestors 'none'; "
                                     "base-uri 'none'; object-src 'none'; form-action 'self'")
                self.send_header("Cache-Control", "no-store")
                for key, value in (headers or {}).items():
                    self.send_header(key, value)
                self.end_headers()
                self.wfile.write(data)

            def _json(self, status, payload, headers=None):
                self._send(status, json.dumps(payload), headers=headers)

            def _body(self):
                raw_length = self.headers.get("Content-Length")
                if self.headers.get("Transfer-Encoding") is not None:
                    return None
                if raw_length is None or not raw_length.isdigit():
                    return None
                length = int(raw_length)
                if length < 0 or length > 8192:
                    return None
                if length == 0:
                    return {}
                if self.headers.get_content_type() != "application/json":
                    return None
                try:
                    raw = self.rfile.read(length)
                    if len(raw) != length:
                        return None
                    return json.loads(raw)
                except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                    return None

            def _trusted_request(self, require_origin=False):
                host_header = self.headers.get("Host", "")
                if not validate_request_host(host_header, owner.host, owner.port):
                    return False
                return not require_origin or validate_request_origin(
                    self.headers.get("Origin", ""), host_header
                )

            def _session(self):
                cookie = self.headers.get("Cookie", "")
                token = next((part.strip().split("=", 1)[1]
                              for part in cookie.split(";")
                              if part.strip().startswith("byparr_session=")), "")
                with owner._lock:
                    now = time.time()
                    owner._sessions = {
                        key: value for key, value in owner._sessions.items()
                        if value["expires"] > now
                    }
                    session = owner._sessions.get(token)
                    if session and session.get("client") == self.client_address[0]:
                        session["expires"] = now + SESSION_SECONDS
                        return token, session
                    invalidated = owner._sessions.pop(token, None)
                    if invalidated:
                        reason = "client address changed" if invalidated.get("client") != self.client_address[0] else "session expired"
                        owner.audit(
                            f"Session invalidated ({reason}) for user '{owner.username}' "
                            f"from {self.client_address[0]}."
                        )
                return None, None

            def do_GET(self):
                if not self._trusted_request():
                    self._json(HTTPStatus.BAD_REQUEST, {"error": "Invalid request host"})
                    return
                path = urlparse(self.path).path
                if path == "/":
                    _, session = self._session()
                    nonce = secrets.token_urlsafe(18)
                    page = DASHBOARD if session else LOGIN_PAGE
                    page = page.replace("__CSP_NONCE__", nonce)
                    self._send(
                        200, page, "text/html",
                        {"Content-Security-Policy":
                         f"default-src 'self'; script-src 'self' 'nonce-{nonce}'; "
                         "style-src 'self' 'unsafe-inline'; frame-ancestors 'none'; "
                         "base-uri 'none'; object-src 'none'; form-action 'self'"},
                    )
                    return
                if path == "/api/status":
                    token, session = self._session()
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
                    self._json(200, status, {
                        "X-CSRF-Token": session["csrf"],
                        "Set-Cookie": f"byparr_session={token}; HttpOnly; SameSite=Strict; "
                                      f"Path=/; Max-Age={SESSION_SECONDS}",
                    })
                    return
                self._json(HTTPStatus.NOT_FOUND, {"error": "Not found"})

            def do_POST(self):
                if not self._trusted_request(require_origin=True):
                    self._json(HTTPStatus.FORBIDDEN, {"error": "Request origin rejected"})
                    return
                path = urlparse(self.path).path
                if path == "/login":
                    payload = self._body()
                    if not isinstance(payload, dict):
                        self._json(400, {"error": "Invalid request"})
                        return
                    address = self.client_address[0]
                    now = time.time()
                    with owner._lock:
                        # Count attempts before PBKDF2 so parallel requests cannot
                        # bypass the per-address limit and consume CPU indefinitely.
                        failures = [
                            stamp for stamp in owner._failures.get(address, [])
                            if now - stamp < 300
                        ]
                        if len(failures) >= 5:
                            owner._failures[address] = failures
                            blocked = True
                        else:
                            failures.append(now)
                            owner._failures[address] = failures
                            blocked = False
                        if len(owner._failures) > 1024:
                            owner._failures = {
                                key: stamps for key, stamps in owner._failures.items()
                                if stamps and now - stamps[-1] < 300
                            }
                    if blocked:
                        owner.audit(f"Login rate limit blocked {address}.")
                        self._json(HTTPStatus.TOO_MANY_REQUESTS,
                                   {"error": "Too many sign-in attempts. Wait five minutes and try again."})
                        return
                    attempted_username = payload.get("username", "")
                    if not isinstance(attempted_username, str):
                        attempted_username = ""
                    attempted_username = re.sub(
                        r"[^A-Za-z0-9_.@-]", "?", attempted_username[:64]
                    )
                    attempted_password = payload.get("password", "")
                    if not isinstance(attempted_password, str):
                        attempted_password = ""
                    password_ok = verify_password(
                        attempted_password, owner.salt, owner.verifier
                    )
                    valid = attempted_username == owner.username and password_ok
                    if not valid:
                        owner.audit(
                            f"Login failed for username '{attempted_username}' from {address}."
                        )
                        self._json(401, {"error": "Sign-in failed. Check your details or wait."})
                        return
                    token = secrets.token_urlsafe(32)
                    csrf = secrets.token_urlsafe(24)
                    with owner._lock:
                        owner._sessions = {
                            key: value for key, value in owner._sessions.items()
                            if value["expires"] > now
                        }
                        if len(owner._sessions) >= 32:
                            owner.audit("Login blocked because the active session limit was reached.")
                            self._json(HTTPStatus.TOO_MANY_REQUESTS,
                                       {"error": "Too many active sessions. Sign out elsewhere first."})
                            return
                        owner._sessions[token] = {
                            "csrf": csrf, "expires": now + SESSION_SECONDS,
                            "client": address,
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
                    category = payload.get("category", "all")
                    category_labels = {
                        "all": "All", "movies": "Movies", "tv": "TV Shows",
                        "audio": "Audio / Music", "books": "Books",
                        "pc": "PC", "console": "Console",
                    }
                    if not isinstance(category, str) or category not in category_labels:
                        self._json(400, {"error": "Choose a valid search category."})
                        return
                    try:
                        results = owner.search_handler(query, category)
                        if not isinstance(results, list):
                            raise TypeError("Unexpected search response")
                    except (RuntimeError, OSError, ValueError, TypeError):
                        owner.audit(
                            f"Prowlarr search failed for user '{owner.username}' from {self.client_address[0]}."
                        )
                        self._json(502, {"error": "Prowlarr search failed. Check the Prowlarr connection and API key."})
                        return
                    entry = {
                        "query": query,
                        "category": category,
                        "category_label": category_labels[category],
                        "count": len(results),
                        "results": results[:50],
                        "searched_at": time.strftime("%H:%M:%S"),
                    }
                    owner._searches.append(entry)
                    owner._searches = owner._searches[-10:]
                    owner.audit(
                        f"Prowlarr {category_labels[category]} search completed for user '{owner.username}' from {self.client_address[0]} ({len(results)} results)."
                    )
                    self._json(200, entry)
                    return
                if path == "/api/grab":
                    grab_id = payload.get("grab_id") if isinstance(payload, dict) else None
                    if not isinstance(grab_id, str) or not 20 <= len(grab_id) <= 100:
                        self._json(400, {"error": "Choose a valid search result."})
                        return
                    if owner.grab_handler is None:
                        self._json(503, {"error": "Release grabbing is not configured."})
                        return
                    try:
                        owner.grab_handler(grab_id)
                    except (RuntimeError, OSError, ValueError, TypeError):
                        owner.audit(
                            f"Release grab failed for user '{owner.username}' from {self.client_address[0]}."
                        )
                        self._json(502, {"error": "Prowlarr could not send this release to its configured download client."})
                        return
                    owner.audit(
                        f"Release grab accepted for user '{owner.username}' from {self.client_address[0]}."
                    )
                    self._json(200, {"ok": True, "message": "Prowlarr accepted the release grab."})
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
                    try:
                        owner.action_handler(action)
                    except (RuntimeError, OSError, ValueError, TypeError) as error:
                        owner.audit(
                            f"Remote action '{action}' failed: {type(error).__name__}."
                        )
                        self._json(HTTPStatus.INTERNAL_SERVER_ERROR,
                                   {"error": "The requested Manager action could not be started."})
                        return
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
        r"(?i)(authorization\s*[:=]\s*)(?:bearer\s+)?[^\s,;]+",
        r"\1[REDACTED]",
        line,
    )
    line = re.sub(
        r"(?i)(api[_-]?key|password|token|cookie|secret|client_secret)(\s*[:=]\s*)"
        r"(?:(?:bearer)\s+)?[\"']?[^\s,;\\\"']+",
        r"\1\2[REDACTED]",
        line,
    )
    line = re.sub(
        r"(?i)([?&](?:apikey|api_key|token|password|passkey|auth|key)=)[^&#\s]+",
        r"\1[REDACTED]",
        line,
    )
    line = re.sub(
        r"(?i)(https?://[^:/\s]+:)[^@/\s]+(@)",
        r"\1[REDACTED]\2",
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
<script nonce="__CSP_NONCE__">document.querySelector('#login').onsubmit=async e=>{e.preventDefault();
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
input,select{box-sizing:border-box;width:100%;padding:13px;border-radius:7px;border:1px solid #35445b;background:#131a25;color:#fff;margin:6px 0 12px}
label{display:block;color:#b8c5d8;margin-top:8px}
.result{border-top:1px solid #2b3749;padding:12px 0}.result strong{display:block;overflow-wrap:anywhere}
.muted{color:#9aa7ba;font-size:13px}#search-message{color:#9aa7ba;min-height:20px}
button:disabled{opacity:.55;cursor:wait}.search-status{display:flex;align-items:center;gap:10px}
.spinner{width:17px;height:17px;border:3px solid #52617a;border-top-color:#8daaff;border-radius:50%;
box-sizing:border-box;animation:spin .8s linear infinite;flex:none}.spinner[hidden]{display:none}
@keyframes spin{to{transform:rotate(360deg)}}
@media(prefers-reduced-motion:reduce){.spinner{animation:none;border-top-color:#8daaff}}</style>
<main><h1>BYPARR MANAGER</h1><p>Private remote dashboard</p><section class="panel">
<h2>Engine</h2><p id="updated" aria-live="polite">Waiting for live status…</p><p id="engine" aria-live="polite">Loading…</p><p id="api"></p><p id="browser"></p>
<p id="prowlarr"></p><p id="qbittorrent"></p>
<button id="start-engine">Start engine</button><button id="restart-engine">Restart</button>
<button id="stop-engine">Stop</button><button id="browser-health">Browser Health</button>
<button id="check-integrations">Check Prowlarr + qBittorrent</button></section>
<section class="panel"><h2>Prowlarr Search</h2>
<p class="muted">Search your configured Prowlarr indexers and view results here on your iPad.</p>
<form id="search-form"><label for="search-category">Search category</label>
<select id="search-category" name="category">
<option value="all">All</option><option value="movies">Movies</option>
<option value="tv">TV Shows</option><option value="audio">Audio / Music</option>
<option value="books">Books</option><option value="pc">PC</option>
<option value="console">Console</option></select>
<label for="search-query">Search term</label>
<input id="search-query" name="query" minlength="2" maxlength="120" placeholder="Enter a title or search term" required>
<button id="search-button" type="submit">Search Prowlarr</button>
<button id="clear-search" type="button">Clear Search</button></form>
<div class="search-status"><span id="search-spinner" class="spinner" hidden aria-hidden="true"></span>
<p id="search-message" role="status" aria-live="polite" aria-atomic="true">Search results will appear here.</p></div>
<div id="search-results"></div><h3>Recent searches</h3><div id="search-history" class="muted">No searches yet.</div>
</section>
<section class="panel"><h2>Recent logs</h2>
<pre id="logs">Loading…</pre></section><button id="logout">Sign out</button>
</main><script nonce="__CSP_NONCE__">let csrf='';async function refresh(){try{const r=await fetch('/api/status',{cache:'no-store',credentials:'same-origin'});
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
meta.textContent=parts.filter(Boolean).join(' · ');card.appendChild(meta);
if(item.grab_id){const grab=document.createElement('button');grab.type='button';grab.textContent='Send to qBittorrent';
grab.addEventListener('click',()=>grabRelease(item.grab_id,item.title,grab));card.appendChild(grab);}
target.appendChild(card);}}
function renderSearchHistory(items){const target=document.querySelector('#search-history');target.replaceChildren();
if(!Array.isArray(items)||!items.length){target.textContent='No searches yet.';return;}
for(const item of [...items].reverse()){const b=document.createElement('button');b.type='button';b.textContent=(item.category_label||'All')+': '+item.query+' ('+item.count+')';
b.addEventListener('click',()=>{document.querySelector('#search-query').value=item.query;document.querySelector('#search-category').value=item.category||'all';renderSearchResults(item);document.querySelector('#search-message').textContent='Previous results · '+item.searched_at;});target.appendChild(b);}}
let grabInFlight=false;
async function grabRelease(grabId,title,button){if(grabInFlight)return;
if(!window.confirm('Send this release to qBittorrent via Prowlarr?\\n\\n'+title))return;
if(!csrf){setSearchMessage('Dashboard session is not ready. Refresh and try again.');return;}
grabInFlight=true;const oldText=button.textContent;button.disabled=true;button.textContent='Sending…';
setSearchMessage('Sending selected release to Prowlarr…');
try{const r=await fetch('/api/grab',{method:'POST',credentials:'same-origin',
headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify({grab_id:grabId})});
const data=await r.json();if(!r.ok)throw new Error(data.error||('HTTP '+r.status));
button.textContent='Sent to qBittorrent';setSearchMessage(data.message||'Prowlarr accepted the release grab.');}
catch(error){button.disabled=false;button.textContent=oldText;setSearchMessage('Could not send release: '+error.message);}
finally{grabInFlight=false;}}
let searchInFlight=false;let searchTimer=null;let searchStartedAt=0;
function elapsedSearchSeconds(){return Math.max(0,Math.floor((Date.now()-searchStartedAt)/1000));}
function setSearchMessage(text){document.querySelector('#search-message').textContent=text;}
document.querySelector('#clear-search').addEventListener('click',()=>{
if(searchInFlight)return;
document.querySelector('#search-query').value='';
document.querySelector('#search-category').value='all';
document.querySelector('#search-results').replaceChildren();
document.querySelector('#search-results').removeAttribute('aria-busy');
document.querySelector('#search-spinner').hidden=true;
setSearchMessage('Search cleared. Enter a new search when ready.');
document.querySelector('#search-query').focus();
});
document.querySelector('#search-form').addEventListener('submit',async event=>{event.preventDefault();
if(searchInFlight)return;
const query=document.querySelector('#search-query').value.trim();
const category=document.querySelector('#search-category').value;
if(query.length<2){setSearchMessage('Enter at least 2 characters.');return;}
if(!csrf){setSearchMessage('Connecting to the dashboard… please try again in a moment.');return;}
searchInFlight=true;searchStartedAt=Date.now();
const button=document.querySelector('#search-button');const clearButton=document.querySelector('#clear-search');const spinner=document.querySelector('#search-spinner');
button.disabled=true;clearButton.disabled=true;button.textContent='Searching…';spinner.hidden=false;
document.querySelector('#search-results').setAttribute('aria-busy','true');
setSearchMessage('Searching Prowlarr… 0s elapsed. Some indexers take longer while Byparr handles challenges.');
searchTimer=setInterval(()=>{const seconds=elapsedSearchSeconds();
setSearchMessage(seconds<15?'Searching Prowlarr… '+seconds+'s elapsed.':'Still searching… '+seconds+'s elapsed. Some indexers take longer while Byparr handles challenges. Keep this page open.');},1000);
try{const r=await fetch('/api/search',{method:'POST',credentials:'same-origin',
headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify({query,category})});
const data=await r.json();if(!r.ok)throw new Error(data.error||('HTTP '+r.status));
renderSearchResults(data);setSearchMessage('Found '+data.count+' '+(data.category_label||'All')+' results for “'+data.query+'” in '+elapsedSearchSeconds()+'s.');
}catch(error){setSearchMessage('Search failed after '+elapsedSearchSeconds()+'s: '+error.message+' You can try again.');}
finally{if(searchTimer!==null){clearInterval(searchTimer);searchTimer=null;}
searchInFlight=false;button.disabled=false;clearButton.disabled=false;button.textContent='Search Prowlarr';spinner.hidden=true;
document.querySelector('#search-results').removeAttribute('aria-busy');}});
async function act(action){try{const r=await fetch('/api/action',{method:'POST',credentials:'same-origin',headers:{
'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify({action})});if(!r.ok)throw new Error('HTTP '+r.status);setTimeout(refresh,700)}
catch(error){document.querySelector('#engine').textContent='Action failed: '+error.message;}}
for(const [id,action] of Object.entries({"start-engine":"start","restart-engine":"restart","stop-engine":"stop","browser-health":"browser-health","check-integrations":"check-integrations"})){document.getElementById(id).addEventListener("click",()=>act(action));}
document.getElementById("logout").addEventListener("click",logout);
async function logout(){await fetch('/logout',{method:'POST',credentials:'same-origin',headers:{'X-CSRF-Token':csrf}});location.reload()}refresh();setInterval(refresh,5000);</script></html>"""
