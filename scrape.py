import os
import re
import json
import pandas as pd
import jobspy
from thefuzz import fuzz
from datetime import datetime
import time
from googlesearch import search

# --- Configuration ---
METADATA_FILE = "metadata.json"
CSV_FILE = "jobs.csv"
RESULTS_PER_SEARCH = 25
HOURS_OLD = 72
TARGET_YEAR = 2027  # titles that name a year must include this one
FUZZ_THRESHOLD = 85

SEARCH_KEYWORD_MAP = {
    "AI": ["ai hardware intern", "machine learning intern electrical engineering", "deep learning hardware intern"],
    "FPGA": ["fpga intern", "rtl design intern", "asic verification intern"],
    "Semiconductors": ["semiconductor intern", "vlsi intern", "asic design intern", "analog ic design intern", "rfic intern"],
    "Software Engineering": ["software engineering intern", "software engineer intern", "it engineer intern", "software development intern"],
    "Trading": ["quantitative trading intern hardware", "fpga developer intern trading", "low latency hardware intern"],
    "Embedded Systems": ["embedded systems intern", "firmware engineer intern", "iot hardware intern"],
}

# Title must look like an internship/co-op. Word boundaries keep
# "international"/"internal" from matching. Seniority words (senior, staff,
# principal...) never co-occur with "intern" except as false positives
# ("Staff Engineering Intern", "Intern Sr" = senior student), so requiring
# this pattern is the whole full-time filter — except "Intern Conversion"
# requisitions, which are full-time roles for former interns.
INTERN_RE = re.compile(r"\bintern(ship)?s?\b|\bco[\s-]?op\b", re.IGNORECASE)
CONVERSION_RE = re.compile(r"\bintern(ship)?\s+conversion\b", re.IGNORECASE)
YEAR_RE = re.compile(r"\b(20\d{2})\b")

# Aggregators / repost mills that pollute listings. Matched on the normalized
# company name exactly, not as a substring.
COMPANY_BLOCKLIST = {
    "lensa",
    "jobs via dice",
    "dice",
    "jobgether",
    "jobright ai",
    "talentify io",
    "adzuna",
}

# Categories are assigned from the job title, first matching rule wins.
# Falls back to the category of the search keyword that found the job.
CATEGORY_RULES = [
    ("Trading", re.compile(r"\b(quant(itative)?|trading|trader|hedge fund|low[\s-]?latency)\b", re.I)),
    ("FPGA", re.compile(r"\b(fpga|rtl|asic|verilog|vhdl|digital design|design verification|logic design)\b", re.I)),
    ("Semiconductors", re.compile(
        r"\b(semiconductor|vlsi|analog|rfic|mixed[\s-]?signal|ic design|silicon|photonics|physical design|"
        r"layout|process integration|packaging|foundry|wafer|lithography)\b", re.I)),
    ("Embedded Systems", re.compile(r"\b(embedded|firmware|iot|microcontroller|rtos|bare[\s-]?metal)\b", re.I)),
    ("AI", re.compile(
        r"\b(ai|machine learning|ml|deep learning|computer vision|nlp|llm|robotics|autonomous|autonomy|"
        r"perception|data science|data scientist|neural)\b", re.I)),
    ("Software Engineering", re.compile(
        r"\b(software|swe|full[\s-]?stack|backend|back[\s-]?end|front[\s-]?end|web|cloud|devops|"
        r"information technology|it|developer|data engineer)\b", re.I)),
]


def norm_key(text):
    """Normalizes a string for dedup keys: lowercase, alphanumeric words only."""
    return re.sub(r"[^a-z0-9]+", " ", str(text).lower()).strip()


def normalize_location(location):
    """Cleans whitespace and strips a trailing ', US'/', USA'/', United States'."""
    if not isinstance(location, str):
        return ""
    location = re.sub(r"\s+", " ", location).strip()
    location = re.sub(r",\s*(US|USA|United States)$", "", location, flags=re.IGNORECASE)
    return location


def classify_job(title, fallback):
    for category, pattern in CATEGORY_RULES:
        if pattern.search(title):
            return category
    return fallback


def filter_reason(title, company):
    """Returns None if the job should be kept, otherwise the rejection reason."""
    if norm_key(company) in COMPANY_BLOCKLIST:
        return "blocklisted company"
    if not INTERN_RE.search(title):
        return "not an internship"
    if CONVERSION_RE.search(title):
        return "intern-conversion (full-time) role"
    years = YEAR_RE.findall(title)
    if years and str(TARGET_YEAR) not in years:
        return "wrong season/year"
    return None


def find_company_url(company_name, scraped_url=None):
    """Returns the best-known URL for a company's page.

    Prefers the URL the job board reported for the company, then falls back to
    a Google search (which is rate limited and can fail in CI)."""
    if isinstance(scraped_url, str) and scraped_url.startswith("http"):
        return scraped_url
    try:
        query = f"{company_name} careers"
        for url in search(query, num_results=1):
            return url
        return f"https://www.google.com/search?q={company_name.replace(' ', '+')}"
    except Exception as e:
        print(f"⚠️  Could not automatically find URL for '{company_name}': {e}")
        return f"https://www.google.com/search?q={company_name.replace(' ', '+')}"


def update_metadata_if_needed(scraped_df, metadata_file):
    """Checks for new companies and updates the metadata file with their URLs."""
    if scraped_df.empty:
        return

    print("\nChecking for new companies to add to metadata...")
    with open(metadata_file, 'r') as f:
        metadata = json.load(f)

    known_companies = set(company.lower() for company in metadata['companies'].keys())

    # Best URL per company as reported by the job boards themselves.
    scraped_urls = {}
    for _, job in scraped_df.iterrows():
        company = job.get("company")
        if not isinstance(company, str) or company.lower() in scraped_urls:
            continue
        url = job.get("company_url_direct")
        if not (isinstance(url, str) and url.startswith("http")):
            url = job.get("company_url")
        if isinstance(url, str) and url.startswith("http"):
            scraped_urls[company.lower()] = url

    found_companies = {str(name) for name in scraped_df['company'].unique() if name}
    new_companies = {comp for comp in found_companies if comp.lower() not in known_companies}

    if not new_companies:
        print("All found companies are already in metadata.json.")
        return

    print(f"🆕 Found {len(new_companies)} new companies. Attempting to find URLs...")
    for company in sorted(new_companies):
        scraped_url = scraped_urls.get(company.lower())
        print(f"   - Resolving URL for: {company}" + (" (from job board)" if scraped_url else " (via search)"))
        metadata['companies'][company] = find_company_url(company, scraped_url)
        if not scraped_url:
            time.sleep(1.5)  # only Google lookups need rate limiting

    metadata['companies'] = dict(sorted(metadata['companies'].items(), key=lambda item: item[0].lower()))
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"Successfully updated {metadata_file} with {len(new_companies)} new company URLs.")


def scrape_jobs_for_categories(keyword_map):
    """Scrapes jobs and returns a single DataFrame with a 'Category' column."""
    all_jobs_dfs = []
    print("🚀 Starting job scraping process...")
    for category, keywords in keyword_map.items():
        print(f"\n--- Searching for category: {category} ---")
        for keyword in keywords:
            print(f"🔍 Searching for term: '{keyword}'...")
            try:
                jobs_df = jobspy.scrape_jobs(
                    site_name=["linkedin", "indeed", "glassdoor"],
                    search_term=keyword,
                    # Native internship filter. LinkedIn/Glassdoor apply it
                    # directly; Indeed ignores it when hours_old is set, so the
                    # title filter below is the backstop there.
                    job_type="internship",
                    results_wanted=RESULTS_PER_SEARCH,
                    hours_old=HOURS_OLD,
                    country_indeed="USA",
                )
                print(f"Found {len(jobs_df)} jobs for '{keyword}'")
                if not jobs_df.empty:
                    jobs_df['SearchCategory'] = category
                    all_jobs_dfs.append(jobs_df)
            except Exception as e:
                print(f"Error scraping for '{keyword}': {e}")

    if not all_jobs_dfs:
        return pd.DataFrame()
    return pd.concat(all_jobs_dfs, ignore_index=True)


def get_existing_jobs(filename):
    """Loads existing jobs from the CSV file, migrating older schemas."""
    if os.path.exists(filename):
        print(f"Loading existing jobs from {filename}.")
        # dtype=str keeps "TRUE"/dates exactly as written instead of parsing
        # them into bools/floats that would round-trip differently.
        df = pd.read_csv(filename, dtype=str)
        if "Date Added" not in df.columns:
            df["Date Added"] = df.get("Date Posted", "")
        return df
    return pd.DataFrame()


def build_existing_index(existing_jobs_df):
    """Groups existing jobs by normalized company name for fast fuzzy dedup."""
    index = {}
    if existing_jobs_df.empty:
        return index
    for _, row in existing_jobs_df.iterrows():
        key = norm_key(row["Company"])
        role = str(row["Role"]).lower()
        location = row.get("Location")
        location = location.lower() if isinstance(location, str) else ""
        index.setdefault(key, []).append((role, location))
    return index


def is_fuzzy_duplicate(job, existing_index, company_match_cache):
    """Checks a new job against existing jobs, only comparing roles within
    companies whose names fuzzy-match (instead of every row in the CSV)."""
    company = norm_key(job.get("company"))
    candidates = company_match_cache.get(company)
    if candidates is None:
        candidates = [
            key for key in existing_index
            if key == company or fuzz.ratio(company, key) > FUZZ_THRESHOLD
        ]
        company_match_cache[company] = candidates

    title = str(job.get("title")).lower()
    location = normalize_location(job.get("location")).lower()
    for key in candidates:
        for existing_role, existing_location in existing_index[key]:
            if fuzz.ratio(title, existing_role) > FUZZ_THRESHOLD:
                # Missing locations count as a match, same as before.
                if not location or not existing_location or \
                        fuzz.ratio(location, existing_location) > FUZZ_THRESHOLD:
                    return True
    return False


def write_summary(stats):
    lines = [
        "## Scraper run summary",
        f"- Scraped (raw): {stats['scraped']}",
        f"- Rejected — not an internship: {stats['not an internship']}",
        f"- Rejected — intern-conversion (full-time) role: {stats['intern-conversion (full-time) role']}",
        f"- Rejected — wrong season/year: {stats['wrong season/year']}",
        f"- Rejected — blocklisted company: {stats['blocklisted company']}",
        f"- Duplicates (within batch): {stats['dup_batch']}",
        f"- Duplicates (already listed): {stats['dup_existing']}",
        f"- **Added: {stats['added']}**",
    ]
    print("\n" + "\n".join(lines))
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a") as f:
            f.write("\n".join(lines) + "\n")


def main():
    existing_jobs_df = get_existing_jobs(CSV_FILE)
    scraped_df = scrape_jobs_for_categories(SEARCH_KEYWORD_MAP)

    stats = {
        "scraped": len(scraped_df), "not an internship": 0, "intern-conversion (full-time) role": 0,
        "wrong season/year": 0, "blocklisted company": 0, "dup_batch": 0,
        "dup_existing": 0, "added": 0,
    }

    if scraped_df.empty:
        print("\nNo new jobs scraped. Exiting.")
        return

    # --- Filter out non-internships, wrong seasons, and aggregator spam ---
    keep_mask = []
    for _, job in scraped_df.iterrows():
        reason = filter_reason(str(job.get("title") or ""), str(job.get("company") or ""))
        if reason:
            stats[reason] += 1
        keep_mask.append(reason is None)
    scraped_df = scraped_df[keep_mask].copy()
    print(f"\n{len(scraped_df)} jobs remain after internship/season/company filters.")

    if scraped_df.empty:
        write_summary(stats)
        return

    scraped_df["location"] = scraped_df["location"].map(normalize_location)

    # --- Dedup within the batch on normalized company/title/location, so the
    # same posting found on two boards (or by two keywords) only counts once ---
    before = len(scraped_df)
    scraped_df["_dedup_key"] = (
        scraped_df["company"].map(norm_key) + "|"
        + scraped_df["title"].map(norm_key) + "|"
        + scraped_df["location"].map(norm_key)
    )
    scraped_df.drop_duplicates(subset=["_dedup_key"], inplace=True)
    stats["dup_batch"] = before - len(scraped_df)
    print(f"Total unique jobs scraped: {len(scraped_df)}")

    update_metadata_if_needed(scraped_df, METADATA_FILE)

    # --- Dedup against jobs already in the CSV ---
    existing_urls = set()
    if not existing_jobs_df.empty and "Application Link" in existing_jobs_df.columns:
        existing_urls = set(existing_jobs_df["Application Link"].dropna())
    existing_index = build_existing_index(existing_jobs_df)
    company_match_cache = {}

    new_jobs = []
    for _, job in scraped_df.iterrows():
        if job.get("job_url") in existing_urls or \
                is_fuzzy_duplicate(job, existing_index, company_match_cache):
            stats["dup_existing"] += 1
        else:
            new_jobs.append(job)

    if not new_jobs:
        print("No new job postings found. The jobs list is up to date!")
        write_summary(stats)
        return

    print(f"\nFound {len(new_jobs)} new jobs!")

    today = datetime.now().strftime('%Y-%m-%d')
    new_jobs_to_append = []
    for job in new_jobs:
        date_posted = job.get('date_posted')
        # Keep the real posting date if the board reported one; otherwise leave
        # it blank instead of faking today's date (Date Added covers recency).
        formatted_date = pd.to_datetime(date_posted).strftime('%Y-%m-%d') if pd.notna(date_posted) else ""

        title = str(job.get("title"))
        category = classify_job(title, job.get("SearchCategory", "Software Engineering"))
        new_jobs_to_append.append({
            "Category": category,
            "Company": job.get("company"),
            "Role": title,
            "Location": job.get("location"),
            "Application Link": job.get("job_url"),
            "Date Posted": formatted_date,
            "Date Added": today,
            "Open": "TRUE"
        })
        print(f"  - {job['company']} - {title} ({category})")

    stats["added"] = len(new_jobs_to_append)
    new_jobs_df = pd.DataFrame(new_jobs_to_append)
    updated_df = pd.concat([existing_jobs_df, new_jobs_df], ignore_index=True)
    columns = ["Category", "Company", "Role", "Location", "Application Link", "Date Posted", "Date Added", "Open"]
    updated_df = updated_df.reindex(columns=columns)
    updated_df.to_csv(CSV_FILE, index=False)

    print(f"\nSuccessfully added {len(new_jobs_df)} new jobs to {CSV_FILE}.")
    write_summary(stats)


if __name__ == "__main__":
    main()
