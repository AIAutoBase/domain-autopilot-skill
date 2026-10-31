# Credits

Built by Hector Diaz for the AI Auto Base community, with Claude Code. Reviewed by Codex (API calls checked against the Cloudflare, GoDaddy, Google Public DNS and RDAP docs) and by a second Claude model, which fixed the findings.

The idea comes from a public post describing an agent wired to Namecheap and Cloudflare that sets up domains and coming-soon pages on its own. This version is registrar neutral and keeps every change behind a dry run.

`design.md` is the landing-page-design skill from [elayadesign/ai-design-skills](https://github.com/elayadesign/ai-design-skills), MIT, copyright Elaya.

## What was verified

On Windows 11 with Python 3.14:

- The offline self-check (`domains.py demo`): classification, hostname validation, HTML escaping, color and URL checks.
- Read-only commands against live public data: `classify` (Google Public DNS), `expiry` (rdap.org), `zone` in dry run.
- The generated page contains its verification marker.

## What was not verified

- `zone`, `ns` and `finish` with `--apply` against a real Cloudflare or GoDaddy account. The calls were checked against the official docs, not run end to end.
- Installing the skill on a clean machine and asking Claude for it in plain words.

If you run it, post in the community what happened.
