"""Marks stale or dead listings as closed in jobs.csv.

Two signals flip a listing's "Open" column to FALSE:
  1. Age: the listing has been on the list longer than MAX_AGE_DAYS.
  2. Dead link: the application link returns HTTP 404/410.

Job boards aggressively block bots (LinkedIn returns 999, Indeed 403), so
anything other than a definitive 404/410 — including errors and timeouts —
is treated as still open. To keep runs short, at most MAX_LINK_CHECKS links
are checked per run, rotating through the list so every link is eventually
visited.
"""

import csv
from datetime import datetime, timedelta

import requests

CSV_FILE = "jobs.csv"
MAX_AGE_DAYS = 120
MAX_LINK_CHECKS = 300
REQUEST_TIMEOUT = 10
USER_AGENT = "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0"


def parse_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except (ValueError, TypeError):
        return None


def link_is_dead(url, session):
    try:
        response = session.head(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        if response.status_code == 405:  # some servers reject HEAD
            response = session.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True, stream=True)
            response.close()
        return response.status_code in (404, 410)
    except requests.RequestException:
        return False  # unreachable is not proof the job is gone


def main():
    with open(CSV_FILE, "r", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    if not rows:
        print("No listings to check.")
        return

    today = datetime.now()
    cutoff = today - timedelta(days=MAX_AGE_DAYS)
    closed_by_age = 0
    closed_by_link = 0

    open_rows = [r for r in rows if r.get("Open", "").strip().lower() == "true"]

    for row in open_rows:
        listed = parse_date(row.get("Date Added") or "") or parse_date(row.get("Date Posted") or "")
        if listed and listed < cutoff:
            row["Open"] = "FALSE"
            closed_by_age += 1

    # Rotate the HTTP checks through the still-open rows across daily runs.
    check_candidates = [
        r for r in open_rows
        if r["Open"].strip().lower() == "true" and (r.get("Application Link") or "").startswith("http")
    ]
    if check_candidates:
        offset = today.timetuple().tm_yday * MAX_LINK_CHECKS % len(check_candidates)
        rotated = check_candidates[offset:] + check_candidates[:offset]
        to_check = rotated[:MAX_LINK_CHECKS]

        session = requests.Session()
        session.headers["User-Agent"] = USER_AGENT
        print(f"Checking {len(to_check)} of {len(check_candidates)} open links...")
        for row in to_check:
            if link_is_dead(row["Application Link"], session):
                row["Open"] = "FALSE"
                closed_by_link += 1
                print(f"  ✗ Dead link: {row['Company']} - {row['Role']}")

    if closed_by_age or closed_by_link:
        with open(CSV_FILE, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    print(f"Closed {closed_by_age} listings older than {MAX_AGE_DAYS} days "
          f"and {closed_by_link} with dead links.")


if __name__ == "__main__":
    main()
