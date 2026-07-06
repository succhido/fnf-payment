# SoSalsa! F&F Day 2026 — showteam payments

Static payment page: pick your name, get your personal Tikkie.

- [index.html](index.html) — the site (GitHub Pages serves this)
- [participants.json](participants.json) — source of truth: who pays what
- [scripts/create_tikkies.py](scripts/create_tikkies.py) — one-time: creates the 31 Tikkie
  payment requests via the Tikkie API and injects the links into index.html
- [scripts/check_payments.py](scripts/check_payments.py) — daily: checks who paid and
  prints/writes a markdown report (posted to Slack #ff-payment-update)

`tikkie_links.json` (created by create_tikkies.py, holds the payment request tokens)
is intentionally **not** committed — it stays on the treasurer's machine.

Bank transfers (people without Tikkie/EU account) are matched by hand: when one
arrives, add the person's name to `manual_paid.json` (local, not committed), e.g.
`["Diego", "Amaia"]` — the daily check then counts them as paid and removes them
from the site dropdown.

Credentials via environment variables: `TIKKIE_API_KEY` (developer.abnamro.com) and
`TIKKIE_APP_TOKEN` (Tikkie Business Portal → Settings → API). Never commit these.

Pricing: €35 for one showteam, €50 for more than one. Deadline: 20 July 2026.
