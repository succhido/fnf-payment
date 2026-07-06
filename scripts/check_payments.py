#!/usr/bin/env python3
"""Check payment status of all F&F Day tikkies and print a markdown report.

Usage:
    set TIKKIE_API_KEY=...
    set TIKKIE_APP_TOKEN=...
    set TIKKIE_SANDBOX=1   (optional)
    python scripts/check_payments.py

Prints the report to stdout and writes payment_report.md next to it.
Exit code 0 always (report generation should never break the daily job).
"""
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import date

# The report contains emoji (❌ 🎉 ⚠️) and €; force UTF-8 so printing never
# crashes on a legacy Windows console (cp1252).
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001 - older Python / non-reconfigurable stream
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINKS_FILE = os.path.join(ROOT, "tikkie_links.json")
MANUAL_FILE = os.path.join(ROOT, "manual_paid.json")  # names paid by bank transfer
REPORT_FILE = os.path.join(ROOT, "payment_report.md")
INDEX_FILE = os.path.join(ROOT, "index.html")

DEADLINE = date(2026, 7, 20)
PAID_START = "// PAID-DATA-START"
PAID_END = "// PAID-DATA-END"


def base_url():
    if os.environ.get("TIKKIE_SANDBOX"):
        return "https://api-sandbox.abnamro.com/v2/tikkie"
    return "https://api.abnamro.com/v2/tikkie"


def get(path):
    req = urllib.request.Request(base_url() + path)
    req.add_header("API-Key", os.environ["TIKKIE_API_KEY"])
    req.add_header("X-App-Token", os.environ["TIKKIE_APP_TOKEN"])
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def euros(cents):
    return f"€{cents / 100:.2f}".replace(".00", "")


def main():
    if not os.environ.get("TIKKIE_API_KEY") or not os.environ.get("TIKKIE_APP_TOKEN"):
        print("ERROR: set TIKKIE_API_KEY and TIKKIE_APP_TOKEN.")
        return
    with open(LINKS_FILE, encoding="utf-8") as f:
        entries = json.load(f)

    manual = set()
    if os.path.exists(MANUAL_FILE):
        with open(MANUAL_FILE, encoding="utf-8") as f:
            manual = set(json.load(f))

    paid, unpaid, errors = [], [], []
    for e in entries:
        if e["fullName"] in manual:
            e["receivedCents"] = e["amountCents"]
            e["viaBank"] = True
            paid.append(e)
            continue
        try:
            pr = get(f"/paymentrequests/{e['token']}")
            received = pr.get("totalAmountPaidInCents", 0)
        except Exception as exc:  # noqa: BLE001 - report and continue
            errors.append((e, str(exc)))
            continue
        e["receivedCents"] = received
        (paid if received >= e["amountCents"] else unpaid).append(e)

    total_due = sum(e["amountCents"] for e in entries)
    total_in = sum(e.get("receivedCents", 0) for e in entries)
    days_left = (DEADLINE - date.today()).days

    lines = ["*F&F Day 2026 — payment status*", ""]
    lines.append(
        f"{euros(total_in)} / {euros(total_due)} collected · "
        f"{len(paid)}/{len(entries)} paid · "
        + (f"{days_left} days until the deadline (20 July)" if days_left >= 0
           else f"deadline was {-days_left} day(s) ago")
    )
    lines.append("")
    if unpaid:
        lines.append(f"*Still owes ({len(unpaid)}):*")
        for e in unpaid:
            partial = f" (paid {euros(e['receivedCents'])} so far)" if e.get("receivedCents") else ""
            lines.append(f"❌ {e['fullName']} — {euros(e['amountCents'])}{partial}")
    elif errors:
        # Some reads failed — do NOT claim everyone paid (could be an outage).
        lines.append("⚠️ Could not confirm payment status for everyone this run — see below.")
    else:
        lines.append("\U0001f389 Everyone has paid!")
    if paid:
        lines.append("")
        lines.append(f"*Paid ({len(paid)}):* " + ", ".join(
            e["fullName"] + (" (bank transfer)" if e.get("viaBank") else "") for e in paid))
    if errors:
        lines.append("")
        lines.append(f"⚠️ Could not check {len(errors)}: "
                     + ", ".join(e["fullName"] for e, _ in errors))

    report = "\n".join(lines)
    print(report)
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(report + "\n")

    update_paid_in_index([e["id"] for e in paid])


def update_paid_in_index(paid_ids):
    """Inject the fully-paid people's opaque ids into index.html so they vanish
    from the dropdown. Ids (not names) are used so nothing personal is published.

    Only grows the list (an id never reappears once marked paid) and only
    rewrites the file when something changed, so a git diff means a real update.
    """
    with open(INDEX_FILE, encoding="utf-8") as f:
        html = f.read()
    start = html.index(PAID_START)
    end = html.index(PAID_END) + len(PAID_END)
    current_block = html[start:end]
    existing = set(json.loads(
        current_block[current_block.index("["):current_block.rindex("]") + 1]
    ))
    merged = sorted(existing | set(paid_ids))
    block = (
        PAID_START + " (auto-updated daily by scripts/check_payments.py — do not edit by hand)\n"
        + "const PAID = " + json.dumps(merged, ensure_ascii=False) + ";\n"
        + PAID_END
    )
    if html[start:end] == block:
        print("\nindex.html paid list unchanged.")
        return
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        f.write(html[:start] + block + html[end:])
    print(f"\nindex.html paid list updated ({len(merged)} paid) — commit and push to deploy.")


if __name__ == "__main__":
    main()
