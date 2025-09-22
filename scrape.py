import os
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
RESULTS_PER_SEARCH = 15
HOURS_OLD = 72

# this needs to be improved - peter
SEARCH_KEYWORD_MAP = {
    "AI": ["ai hardware intern", "machine learning intern electrical engineering", "deep learning hardware intern"],
    "FPGA": ["fpga intern", "rtl design intern", "asic verification intern"],
    "Semiconductors": ["semiconductor intern", "vlsi intern", "asic design intern", "analog ic design intern", "rfic intern"],
    "Software Engineering": ["software engineering intern", "software engineer intern", "it engineer intern", "software development intern"],
    "Trading": ["quantitative trading intern hardware", "fpga developer intern trading", "low latency hardware intern"],
    "Embedded Systems": ["embedded systems intern", "firmware engineer intern", "iot hardware intern"],
}

def find_company_url(company_name):
    """Searches for a company's career page and returns the most likely URL."""
    try:
        query = f"{company_name} careers"
        for url in search(query, num_results=1):
            return url
        # This is a fallback if the search yields no results
        return f"https://www.google.com/search?q={company_name.replace(' ', '+')}"
    except Exception as e:
        print(f"⚠️  Could not automatically find URL for '{company_name}': {e}")
        # Return a backup Google search link if the search fails.
        return f"https://www.google.com/search?q={company_name.replace(' ', '+')}"

def update_metadata_if_needed(scraped_df, metadata_file):
    """Checks for new companies and updates the metadata file with their URLs."""
    if scraped_df.empty:
        return
    
    print("\nChecking for new companies to add to metadata...")
    with open(metadata_file, 'r') as f:
        metadata = json.load(f)

    known_companies = set(company.lower() for company in metadata['companies'].keys())
    
    found_companies = {str(name) for name in scraped_df['company'].unique() if name}

    new_companies = {comp for comp in found_companies if comp.lower() not in known_companies}

    if not new_companies:
        print("All found companies are already in metadata.json.")
        return

    print(f"🆕 Found {len(new_companies)} new companies. Attempting to find URLs...")
    updated = False
    for company in sorted(list(new_companies)):
        print(f"   - Searching for: {company}")
        url = find_company_url(company) 
        metadata['companies'][company] = url
        updated = True
        time.sleep(1.5) 

    if updated:
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
                    results_wanted=RESULTS_PER_SEARCH,
                    hours_old=HOURS_OLD,
                    country_indeed="USA",
                    headers = {
                        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
                    }
                    
                )
                print(f"Found {len(jobs_df)} jobs for '{keyword}'")
                if not jobs_df.empty:
                    jobs_df['Category'] = category
                    all_jobs_dfs.append(jobs_df)
            except Exception as e:
                print(f"Error scraping for '{keyword}': {e}") # noqa: F841

    if not all_jobs_dfs:
        return pd.DataFrame()
    return pd.concat(all_jobs_dfs, ignore_index=True)

def get_existing_jobs(filename):
    """Loads existing jobs from the CSV file."""
    if os.path.exists(filename):
        print(f"Loading existing jobs from {filename}.")
        return pd.read_csv(filename)
    return pd.DataFrame()

def is_fuzzy_duplicate(new_job, existing_jobs_df, threshold=85):
    """Checks if a new job is a fuzzy duplicate of an existing one."""
    for _, existing_job in existing_jobs_df.iterrows():
        title_score = fuzz.ratio(str(new_job["title"]).lower(), str(existing_job["Role"]).lower())
        company_score = fuzz.ratio(str(new_job["company"]).lower(), str(existing_job["Company"]).lower())
        
        location = new_job.get("location")
        existing_location = existing_job.get("Location")
        if isinstance(location, str) and isinstance(existing_location, str):
            location_score = fuzz.ratio(location.lower(), existing_location.lower())
        else:
            location_score = 100

        if title_score > threshold and company_score > threshold and location_score > threshold:
            return True
    return False

def main():
    existing_jobs_df = get_existing_jobs(CSV_FILE)
    scraped_df = scrape_jobs_for_categories(SEARCH_KEYWORD_MAP)

    if scraped_df.empty:
        print("\nNo new jobs scraped. Exiting.")
        return

    update_metadata_if_needed(scraped_df, METADATA_FILE)

    scraped_df.drop_duplicates(subset=["title", "company", "location"], inplace=True)
    print(f"\nTotal unique jobs scraped: {len(scraped_df)}")

    new_jobs = []
    for _, job in scraped_df.iterrows():
        if not is_fuzzy_duplicate(job, existing_jobs_df):
            new_jobs.append(job)

    if not new_jobs:
        print("No new job postings found. The jobs list is up to date!")
        return

    print(f"\nFound {len(new_jobs)} new jobs!")
    
    new_jobs_to_append = []
    for job in new_jobs:
        date_posted = job.get('date_posted')
        formatted_date = pd.to_datetime(date_posted).strftime('%Y-%m-%d') if pd.notna(date_posted) else datetime.now().strftime('%Y-%m-%d')
        
        new_jobs_to_append.append({
            "Category": job.get("Category", "General"),
            "Company": job.get("company"),
            "Role": job.get("title"),
            "Location": job.get("location"),
            "Application Link": job.get("job_url"),
            "Date Posted": formatted_date,
            "Open": "TRUE"
        })
        print(f"  - {job['company']} - {job['title']} ({job['Category']})")

    new_jobs_df = pd.DataFrame(new_jobs_to_append)
    updated_df = pd.concat([existing_jobs_df, new_jobs_df], ignore_index=True)
    updated_df.to_csv(CSV_FILE, index=False)
    
    print(f"\nSuccessfully added {len(new_jobs_df)} new jobs to {CSV_FILE}.")

if __name__ == "__main__":
    main()