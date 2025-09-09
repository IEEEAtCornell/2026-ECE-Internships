import os
import json
import pandas as pd
import jobspy
from thefuzz import fuzz
from datetime import datetime

# --- Configuration ---
METADATA_FILE = "metadata.json"
CSV_FILE = "jobs.csv"
RESULTS_PER_SEARCH = 15  # Number of results to fetch for each keyword search
HOURS_OLD = 72  # Max age of job postings in hours

# --- Keyword Strategy for Targeted Searching ---
# Maps categories from metadata.json to specific search terms.
# This helps find more relevant ECE roles.
SEARCH_KEYWORD_MAP = {
    "AI": [
        "ai hardware intern",
        "machine learning intern electrical engineering",
        "deep learning hardware intern",
    ],
    "FPGA": [
        "fpga intern",
        "rtl design intern",
        "asic verification intern",
    ],
    "Semiconductors": [
        "semiconductor intern",
        "vlsi intern",
        "asic design intern",
        "analog ic design intern",
        "rfic intern",
    ],
    "Trading": [
        "quantitative trading intern hardware",
        "fpga developer intern trading",
        "low latency hardware intern",
    ],
    "Embedded Systems": [
        "embedded systems intern",
        "firmware engineer intern",
        "iot hardware intern",
    ],
}

def load_metadata(file_path):
    """Loads metadata from the specified JSON file."""
    print(f"📘 Loading metadata from {file_path}...")
    with open(file_path, "r") as f:
        return json.load(f)

def scrape_jobs_for_categories(keyword_map):
    """Scrapes jobs for each category using targeted keywords."""
    all_jobs = []
    print("🚀 Starting job scraping process...")
    for category, keywords in keyword_map.items():
        print(f"\n--- Searching for category: {category} ---")
        for keyword in keywords:
            print(f"🔍 Searching for term: '{keyword}'...")
            try:
                jobs = jobspy.scrape_jobs(
                    site_name=["linkedin", "indeed", "glassdoor"],
                    search_term=keyword,
                    results_wanted=RESULTS_PER_SEARCH,
                    hours_old=HOURS_OLD,
                    country_indeed="USA",
                    return_dict=True  # FIX: Ensures the output is a list of dictionaries
                )
                print(f"✅ Found {len(jobs)} jobs for '{keyword}'")
                for job in jobs:
                    job['Category'] = category  # Tag each job with its category
                all_jobs.extend(jobs)
            except Exception as e:
                print(f"❌ Error scraping for '{keyword}': {e}")
    return all_jobs

def get_existing_jobs(filename):
    """Loads existing jobs from the CSV file."""
    if os.path.exists(filename):
        print(f"📑 Loading existing jobs from {filename}.")
        return pd.read_csv(filename)
    return pd.DataFrame()

def is_fuzzy_duplicate(new_job, existing_jobs_df, threshold=85):
    """Checks if a new job is a fuzzy duplicate of an existing one."""
    for _, existing_job in existing_jobs_df.iterrows():
        title_score = fuzz.ratio(str(new_job["title"]).lower(), str(existing_job["Role"]).lower())
        company_score = fuzz.ratio(str(new_job["company"]).lower(), str(existing_job["Company"]).lower())
        
        # Only compare location if both are strings
        if isinstance(new_job.get("location"), str) and isinstance(existing_job.get("Location"), str):
            location_score = fuzz.ratio(new_job["location"].lower(), existing_job["Location"].lower())
        else:
            location_score = 100 # Assume match if location data is missing/not comparable

        if title_score > threshold and company_score > threshold and location_score > threshold:
            return True
    return False

def main():
    """Main function to run the job scraping and processing pipeline."""
    # Load metadata and existing jobs
    metadata = load_metadata(METADATA_FILE)
    existing_jobs_df = get_existing_jobs(CSV_FILE)

    # Scrape new jobs based on the keyword map
    scraped_jobs = scrape_jobs_for_categories(SEARCH_KEYWORD_MAP)
    if not scraped_jobs:
        print("\nNo jobs found in the scrape. Exiting.")
        return

    # Convert to DataFrame and remove duplicates from the scrape itself
    scraped_df = pd.DataFrame(scraped_jobs)
    scraped_df.drop_duplicates(subset=["title", "company", "location"], inplace=True)
    print(f"\n✨ Total unique jobs scraped: {len(scraped_df)}")

    # Identify jobs that are not already in the CSV
    new_jobs = []
    for _, job in scraped_df.iterrows():
        if not is_fuzzy_duplicate(job, existing_jobs_df):
            new_jobs.append(job)

    # Process and save new jobs
    if not new_jobs:
        print("✅ No new job postings found. The jobs list is up to date!")
        return

    print(f"\n📢 Found {len(new_jobs)} new jobs!")
    
    new_jobs_to_append = []
    for job in new_jobs:
        # Format date to YYYY-MM-DD
        date_posted = job.get('date_posted')
        formatted_date = date_posted.strftime("%Y-%m-%d") if isinstance(date_posted, datetime) else datetime.now().strftime("%Y-%m-%d")

        new_jobs_to_append.append({
            "Category": job.get("Category", "General"),
            "Company": job.get("company"),
            "Role": job.get("title"),
            "Location": job.get("location"),
            "Application Link": job.get("job_url"),
            "Date Posted": formatted_date,
            "Open": "TRUE"
        })
        print(f"  - 🆕 {job['company']} - {job['title']} ({job['Category']})")

    # Append new jobs to the CSV file
    new_jobs_df = pd.DataFrame(new_jobs_to_append)
    updated_df = pd.concat([existing_jobs_df, new_jobs_df], ignore_index=True)
    updated_df.to_csv(CSV_FILE, index=False)
    
    print(f"\n💾 Successfully added {len(new_jobs_df)} new jobs to {CSV_FILE}.")

if __name__ == "__main__":
    main()