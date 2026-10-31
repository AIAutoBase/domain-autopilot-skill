#!/usr/bin/env python3
"""domain-autopilot: classify / zone / ns / finish / expiry. Dry-run unless --apply."""
import json, os, re, sys, html, urllib.request, urllib.parse, urllib.error, datetime, pathlib, uuid

STATE = pathlib.Path(__file__).with_name("state.json")
CF = "https://api.cloudflare.com/client/v4"
UA = {"User-Agent": "domain-autopilot"}
DOMAIN_RE = re.compile(r"^(?=.{4,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z][a-z0-9-]{1,62}$")
HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
PARKED_NS = ("hostgator", "bluehost", "domaincontrol", "registrar-servers", "parkingcrew", "networksolutions", "worldnic")

def valid_domain(d): return bool(DOMAIN_RE.match(d))
def q(d): return urllib.parse.quote(d, safe="")

def env(name):
    v = os.environ.get(name)
    if not v: sys.exit(f"missing env {name}; see SKILL.md")
    return v

def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
        return json.load(r)

def dns(domain, rtype):
    d = get(f"https://dns.google/resolve?name={q(domain)}&type={rtype}")
    if d.get("Status") != 0: return None  # NXDOMAIN/SERVFAIL: nothing is safe to assume
    return [a["data"] for a in d.get("Answer", []) if a["type"] == {"NS": 2, "A": 1}[rtype]]

def ns_of(domain):
    ns = dns(domain, "NS")
    return None if ns is None else sorted(x.rstrip(".").lower() for x in ns)

def a_of(domain): return dns(domain, "A") or []

def probe(domain):
    """'' when nothing answers on 443/80, else 'status title' so the user can judge parking pages."""
    for u in (f"https://{domain}", f"http://{domain}"):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=8) as r:
                m = re.search(r"<title[^>]*>(.*?)</title>", r.read(8192).decode("utf-8", "replace"), re.I | re.S)
                return f"{r.status} {html.unescape(m.group(1)).strip()[:50]!r}" if m else str(r.status)
        except urllib.error.HTTPError as e: return str(e.code)
        except Exception: pass
    return ""

def classify(ns, ips, live=""):
    if ns is None: return "unresolved"
    n = " ".join(ns)
    if "cloudflare.com" in n: return "cloudflare"
    if "vercel-dns" in n: return "vercel"
    if "shopify" in n or any(ip.startswith("23.227.38.") for ip in ips): return "shopify"
    if live: return "live"
    if ns and any(k in n for k in PARKED_NS): return "ready"  # ponytail: NS-name allowlist; extend PARKED_NS as registrars show up
    return "unknown"

def inspect(d):
    ns = ns_of(d); live = probe(d) if ns else ""
    return ns, classify(ns, a_of(d) if ns else [], live), live

def cf(method, path, body=None, raw=None, ctype="application/json"):
    data = raw if raw is not None else (json.dumps(body).encode() if body else None)
    req = urllib.request.Request(CF + path, data=data, method=method, headers={
        "Authorization": "Bearer " + env("CF_API_TOKEN"), "Content-Type": ctype})
    try:
        with urllib.request.urlopen(req, timeout=30) as r: return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"Cloudflare {e.code} on {method} {path}: {e.read()[:300].decode()}")

def load(): return json.loads(STATE.read_text()) if STATE.exists() else {}
def save(s): STATE.write_text(json.dumps(s, indent=2))

def cmd_classify(domains, apply, force=False):
    for d in domains:
        ns, kind, live = inspect(d)
        print(f"{d:32} {kind:11} {', '.join(ns or [])}{'  http: ' + live if live else ''}")

def cmd_zone(domains, apply, force=False):
    st = load()
    for d in domains:
        if d in st: print(f"SKIP {d}: zone already in state.json (id {st[d]['zone']})"); continue
        ns, kind, live = inspect(d)
        if kind == "live" and force: kind = "ready"
        if kind != "ready": print(f"SKIP {d}: {kind}{' (http: ' + live + '); add --force if that is only a parking page' if kind == 'live' else ''}"); continue
        print(f"{d}: would create zone; old NS saved: {ns}")
        if not apply: continue
        r = cf("POST", "/zones", {"name": d, "account": {"id": env("CF_ACCOUNT_ID")}, "type": "full"})["result"]
        st[d] = {"zone": r["id"], "old_ns": ns, "new_ns": r["name_servers"], "started": datetime.datetime.now(datetime.timezone.utc).isoformat()}
        save(st); print(f"  -> set nameservers at your registrar to: {r['name_servers']}")

def brand(d):
    f = pathlib.Path(__file__).with_name("brands.json")
    b = {k: str(v) for k, v in (json.loads(f.read_text()).get(d, {}) if f.exists() else {}).items()}
    b = {"name": d, "tagline": "Something new is on the way", "blurb": "We are putting the finishing touches on this site. Check back soon.",
         "accent": "#FFFFFF", "cta_text": "", "cta_url": "", **b}
    if not HEX_RE.match(b["accent"]): b["accent"] = "#FFFFFF"
    if not re.match(r"^https?://", b["cta_url"], re.I): b["cta_url"] = ""
    return b

def page(d, marker):
    # Follows design.md Part B: Geist, flat #131209 bg, gradient text only on H1, 680px max width, spacing tokens, no italics, no hyphens in copy.
    b = brand(d); esc = lambda t: html.escape(t, quote=True)
    cta = f'<a class=btn href="{esc(b["cta_url"])}">{esc(b["cta_text"])}</a>' if b["cta_url"] and b["cta_text"] else ""
    return f"""<!doctype html><html lang=en><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>{esc(b['name'])}</title><meta name=description content="{esc(b['tagline'])}">
<meta property=og:title content="{esc(b['name'])}"><meta property=og:description content="{esc(b['tagline'])}">
<link rel=preconnect href=https://fonts.googleapis.com><link rel=stylesheet href="https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600&display=swap">
<style>*{{box-sizing:border-box;margin:0}}body{{background:#131209;color:#9B9B9B;font:400 16px/24px Geist,system-ui,sans-serif;min-height:100vh;display:grid;place-items:center;padding:24px}}
main{{max-width:680px;display:grid;gap:24px;justify-items:start}}
.tag{{font:500 14px/20px Geist,system-ui;color:{b['accent']};border:1px solid #313131;background:#1F1F1F;border-radius:8px;padding:4px 12px}}
h1{{font:600 60px/60px Geist,system-ui;background:linear-gradient(90deg,#FFF,#9B9B9B);-webkit-background-clip:text;background-clip:text;color:transparent;text-wrap:balance;opacity:0;animation:in .8s cubic-bezier(.16,1,.3,1) forwards}}
p{{text-wrap:pretty;opacity:0;animation:in .8s .15s cubic-bezier(.16,1,.3,1) forwards}}
.btn{{font:600 16px/24px Geist,system-ui;background:{b['accent']};color:#000;text-decoration:none;border-radius:8px;padding:8px 12px}}
footer{{font:400 12px/16px Geist,system-ui;color:#313131}}
@keyframes in{{from{{opacity:0;transform:translateY(12px)}}to{{opacity:1;transform:none}}}}
@media(max-width:640px){{h1{{font-size:36px;line-height:40px}}}}@media(prefers-reduced-motion:reduce){{h1,p{{animation:none;opacity:1}}}}</style>
<main><span class=tag>Coming soon</span><h1>{esc(b['tagline'])}</h1><p>{esc(b['blurb'])}</p>{cta}<footer>{esc(d)}</footer></main><!-- {marker} -->"""

def ensure_proxied(zone, names):
    """Worker routes only see traffic for proxied hostnames: add AAAA 100:: or flip existing records to proxied."""
    recs = cf("GET", f"/zones/{zone}/dns_records?per_page=500")["result"]
    for name in names:
        mine = [r for r in recs if r["name"] == name and r["type"] in ("A", "AAAA", "CNAME")]
        if not mine: cf("POST", f"/zones/{zone}/dns_records", {"type": "AAAA", "name": name, "content": "100::", "proxied": True})
        for r in mine:
            if not r.get("proxied"): cf("PATCH", f"/zones/{zone}/dns_records/{r['id']}", {"proxied": True})

def cmd_finish(domains, apply, force=False):
    st = load()
    for d in domains:
        s = st.get(d)
        if not s: print(f"SKIP {d}: run `zone` first"); continue
        zone = cf("GET", f"/zones/{s['zone']}")["result"]
        if zone["status"] != "active": print(f"{d}: zone {zone['status']}, nameservers not switched yet"); continue
        marker = s.setdefault("marker", "dap-" + uuid.uuid4().hex[:10])
        hosts = (d, "www." + d)
        print(f"{d}: would ensure proxied DNS for {hosts}, deploy worker + routes, then check marker {marker}")
        if not apply: continue
        acct = env("CF_ACCOUNT_ID")
        name = "coming-soon-" + d.replace(".", "-")
        js = f"export default {{ fetch() {{ return new Response({json.dumps(page(d, marker))}, {{headers: {{'content-type':'text/html;charset=utf-8'}}}}) }} }}"
        b = "----dap"
        raw = (f'--{b}\r\nContent-Disposition: form-data; name="metadata"\r\n\r\n{{"main_module":"w.js"}}\r\n'
               f'--{b}\r\nContent-Disposition: form-data; name="w.js"; filename="w.js"\r\nContent-Type: application/javascript+module\r\n\r\n{js}\r\n--{b}--\r\n').encode()
        cf("PUT", f"/accounts/{acct}/workers/scripts/{name}", raw=raw, ctype=f"multipart/form-data; boundary={b}")
        ensure_proxied(s["zone"], hosts)
        have = {r["pattern"] for r in cf("GET", f"/zones/{s['zone']}/workers/routes")["result"]}
        for pat in (f"{h}/*" for h in hosts):
            if pat not in have: cf("POST", f"/zones/{s['zone']}/workers/routes", {"pattern": pat, "script": name})
        save(st)
        for h in hosts:
            try: ok = marker in urllib.request.urlopen(urllib.request.Request(f"https://{h}", headers=UA), timeout=20).read().decode("utf-8", "replace")
            except Exception as e: ok = False; print(f"  {h}: HTTPS not ready yet ({e}); rerun finish later")
            print(f"  {h}: live={ok}")
        # ponytail: no notify or cron here; wrap in cron + notify when wanted

def cmd_expiry(domains, apply, force=False):
    today = datetime.date.today()
    for d in domains:
        try:
            ev = get(f"https://rdap.org/domain/{q(d)}")["events"]
            exp = datetime.date.fromisoformat(next(e["eventDate"] for e in ev if e["eventAction"] == "expiration")[:10])
        except Exception as e: print(f"{d:32} expiry unknown ({e})"); continue
        rem = ", ".join(str(exp - datetime.timedelta(days=n)) for n in (60, 30, 7) if exp - datetime.timedelta(days=n) >= today)
        print(f"{d:32} expires {exp} ({(exp - today).days}d)  remind: {rem or 'none left'}")

def registrar_of(d):
    try:
        r = get(f"https://rdap.org/domain/{q(d)}")
        reg = next(e for e in r["entities"] if "registrar" in e.get("roles", []))
        return next(x[3] for x in reg["vcardArray"][1] if x[0] == "fn")
    except Exception: return "unknown"

def godaddy_auth():
    if os.environ.get("GODADDY_TOKEN"): return "Bearer " + os.environ["GODADDY_TOKEN"]
    print("  note: GODADDY_KEY/GODADDY_SECRET is the legacy sso-key scheme (deprecated 2026); prefer GODADDY_TOKEN")
    return f"sso-key {env('GODADDY_KEY')}:{env('GODADDY_SECRET')}"

def godaddy_set_ns(d, ns):
    req = urllib.request.Request(f"https://api.godaddy.com/v1/domains/{q(d)}", method="PATCH",
        data=json.dumps({"nameServers": ns}).encode(), headers={"Content-Type": "application/json", "Authorization": godaddy_auth()})
    try: urllib.request.urlopen(req, timeout=30)
    except urllib.error.HTTPError as e: sys.exit(f"GoDaddy {e.code}: {e.read()[:300].decode()}")

def cmd_ns(domains, apply, force=False, rollback=False):
    st = load()
    for d in domains:
        s = st.get(d)
        if not s: print(f"SKIP {d}: run `zone` first"); continue
        want = s["old_ns"] if rollback else s["new_ns"]
        reg = registrar_of(d)
        print(f"{d}: registrar {reg}; nameservers -> {want}")
        if "godaddy" not in reg.lower():
            print(f"  no API for {reg}: change them by hand in its dashboard"); continue  # ponytail: GoDaddy only; add Namecheap/others as needed
        if not apply: continue
        godaddy_set_ns(d, want)
        print(f"  set. Propagation can take minutes to hours; verify: domains.py classify {d}")

def demo():
    assert classify(["a.ns.cloudflare.com"], []) == "cloudflare"
    assert classify(["ns1.vercel-dns.com"], []) == "vercel"
    assert classify(["ns1.hostgator.com"], ["23.227.38.65"]) == "shopify"
    assert classify(["ns1.hostgator.com"], []) == "ready"
    assert classify(["ns1.hostgator.com"], [], live="200 'Parked'") == "live"
    assert classify(["ns.example.org"], []) == "unknown"
    assert classify([], []) == "unknown"
    assert classify(None, []) == "unresolved"
    assert all(valid_domain(d) for d in ("a.com", "sub.a-b.co.uk", "xn--bcher-kva.de"))
    assert not any(valid_domain(d) for d in ("A.com", "-a.com", "a", "a..com", "a.com/x", "a.com?x", "a b.com", "a.1"))
    assert q("a.com/../x") == "a.com%2F..%2Fx"
    assert html.escape('"><script>', quote=True) == "&quot;&gt;&lt;script&gt;"
    assert HEX_RE.match("#1A2b3C") and not HEX_RE.match("#fff") and not HEX_RE.match("red;}body{x:url(")
    assert not re.match(r"^https?://", "javascript:alert(1)", re.I) and re.match(r"^https?://", "HTTPS://x.com", re.I)
    assert "dap-x" in page("example.com", "dap-x") and "class=btn" not in page("example.com", "dap-x")
    print("ok")

CMDS = {"classify": cmd_classify, "zone": cmd_zone, "finish": cmd_finish, "expiry": cmd_expiry, "ns": cmd_ns}
if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] == "demo": demo(); sys.exit()
    if a[0] not in CMDS: sys.exit(f"usage: domains.py {'|'.join(CMDS)} domain... [--apply] [--force] [--rollback]")
    flags = {x for x in a[1:] if x.startswith("--")}
    domains = [x.lower().rstrip(".") for x in a[1:] if not x.startswith("--")]
    bad = [d for d in domains if not valid_domain(d)]
    if bad or not domains: sys.exit(f"bad domain(s): {bad or 'none given'}")
    kw = {"force": "--force" in flags}
    if "--rollback" in flags: CMDS["ns"](domains, "--apply" in flags, rollback=True)
    else: CMDS[a[0]](domains, "--apply" in flags, **kw)
