# domain-autopilot

A Claude Code skill that puts your idle domains on Cloudflare's free plan with a designed coming-soon page, checks that the page is really live over HTTPS, and tells you when each domain expires.

Your domains stay registered where they are. Nothing is transferred.

## What it does

1. **Classify** every domain you list by where its nameservers point: `cloudflare`, `vercel`, `shopify`, `live`, `ready`, `unknown`, `unresolved`. Only `ready` is ever acted on.
2. **Zone**: creates the Cloudflare zone and saves the old nameservers so you can roll back.
3. **Nameservers**: switches them at the registrar. GoDaddy through its API; every other registrar gets the exact two nameservers to paste by hand.
4. **Finish**: makes apex and www proxied, deploys a Cloudflare Worker that serves the page, adds the routes, and fetches both hosts until a unique marker in the page comes back over HTTPS.
5. **Expiry**: reads each expiry date over RDAP and prints reminder dates 60, 30 and 7 days before.

Everything is a dry run until you add `--apply`.

## Install (2 minutes)

Copy the `domain-autopilot` folder into your Claude Code skills folder:

- macOS / Linux: `~/.claude/skills/domain-autopilot/`
- Windows: `%USERPROFILE%\.claude\skills\domain-autopilot\`

Check it runs: `python3 ~/.claude/skills/domain-autopilot/domains.py demo` (use `python` on Windows). It prints `ok`.

Then, in Claude Code: "check my domains example.com example.net" or "put example.com on Cloudflare with a coming-soon page".

## What you need

- Python 3.9 or newer. No packages to install.
- A free Cloudflare account. An API token with Zone Edit, DNS Edit, Workers Routes Edit (all zones) and Workers Scripts Edit (account), set as `CF_API_TOKEN`, and your account id as `CF_ACCOUNT_ID`.
- Optional, for domains at GoDaddy: a GoDaddy Personal Access Token with domain write scope as `GODADDY_TOKEN`.

Keep the keys in your environment, never in the skill folder.

## The page

The coming-soon page follows the visual rules in `design.md`, taken from [elayadesign/ai-design-skills](https://github.com/elayadesign/ai-design-skills) (MIT). Per domain text, accent color and an optional button go in a `brands.json` next to the script; see `SKILL.md` for the format. Without it you get a clean neutral page with the domain name.

## What it does not do

- It does not buy or transfer domains.
- It does not copy anything from an old host. A domain with a live site is left alone unless you pass `--force` and confirm.
- It does not run on a schedule or send notifications. Wrap it in cron if you want that.
- It does not capture emails on the page.

## Read it before you run it

Open `SKILL.md` and `domains.py`, hand them to Claude and ask what they will change in your Cloudflare and registrar accounts. The answer should be: one zone per domain, two proxied DNS records, one Worker and two routes, and a nameserver change at the registrar, all only with `--apply`.

## License

`SKILL.md`, `domains.py`: MIT (`LICENSE`). `design.md`: MIT, by Elaya (`LICENSE-design.md`). See `DISCLAIMER.md` and `CREDITS.md`.
