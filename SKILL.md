---
name: domain-autopilot
description: Classify your domains by where they point, put idle ones on Cloudflare's free plan with a coming-soon page, verify HTTPS, and list expiry dates with 60/30/7-day reminders. Use when the user says "set up a domain on Cloudflare", "coming soon page", "which domains are idle", "domain expiry", or "check my domains".
---

# domain-autopilot

Script: `~/.claude/skills/domain-autopilot/domains.py` (Python 3.9+, stdlib only). Run it with its full path. `python3` on macOS/Linux, `python` on Windows (`$HOME\.claude\skills\domain-autopilot\domains.py`). **Dry-run by default; nothing changes without `--apply`.** `python3 ~/.claude/skills/domain-autopilot/domains.py demo` runs an offline self-check.

## Env (never print them)
- `CF_API_TOKEN`: Cloudflare API token with, for all zones in the account: **Zone: Edit**, **DNS: Edit**, **Workers Routes: Edit**, plus account-level **Workers Scripts: Edit**. `CF_ACCOUNT_ID`: the account id (Cloudflare dashboard, Overview page). Both are needed for `zone` and `finish`; `finish` reads the zone even in dry-run.
- GoDaddy, only for `ns` on GoDaddy domains: `GODADDY_TOKEN` (Personal Access Token with domain write scope, sent as Bearer). Legacy `GODADDY_KEY`/`GODADDY_SECRET` (sso-key, deprecated in 2026) still works as a fallback and prints a notice.

| Step | Command (prefix with `python3 ~/.claude/skills/domain-autopilot/domains.py`) |
|---|---|
| 1. Classify (read-only) | `classify a.com b.com` |
| 2. Create zone, show the 2 Cloudflare nameservers | `zone a.com [--apply]` (`--force` also accepts `live`, for domains whose only page is a registrar parking page) |
| 3. Switch nameservers at the registrar | `ns a.com [--apply]` (GoDaddy via API; other registrars print manual steps). Undo: `ns a.com --rollback --apply` |
| 4. Proxied DNS + Worker + routes + HTTPS marker check on apex and www | `finish a.com [--apply]` |
| Expiry + reminder dates | `expiry a.com b.com` |

Classes: `cloudflare` / `vercel` / `shopify` (never touch), `live` (something answers on 80/443; the status and page title are printed so the user can judge if it is a parking page), `ready` (registrar/parking nameservers, nothing answers), `unknown` (unrecognised nameservers, nothing answers), `unresolved` (NXDOMAIN or DNS error). Only `ready` is acted on; `live` needs `--force` and the user's confirmation.

Rules: registrar is detected via RDAP. `finish` makes apex and www proxied (adds `AAAA 100::` when no A/AAAA/CNAME exists, otherwise flips existing records to proxied), so the Worker route gets traffic; rerunning it is safe. `state.json` next to the script holds zone ids and the old nameservers used by `--rollback`; keep it. Buying domains is not automated. Domain arguments are validated (lowercase hostnames only).

## Page design
`finish` serves a designed page, not a bare placeholder. Rules live in `design.md` (MIT, from elayadesign/ai-design-skills: Part A copy/structure, Part B visual system). **Read `design.md` before changing `page()`.** Per domain copy and accent color go in optional `brands.json` next to the script: `{"a.com": {"name":"A","tagline":"...","blurb":"...","accent":"#RRGGBB","cta_text":"...","cta_url":"https://..."}}`. Values are HTML-escaped; `accent` must be a 6-digit hex and `cta_url` must be http(s), otherwise they fall back. Missing entries fall back to a neutral design. No email capture yet. To add more design guidance, append it to `design.md`.
