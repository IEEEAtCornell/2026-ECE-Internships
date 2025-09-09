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
                )
                print(f"✅ Found {len(jobs_df)} jobs for '{keyword}'")

                # FIX: Check if the DataFrame is not empty before processing
                if not jobs_df.empty:
                    jobs_df['Category'] = category  # Add category to the DataFrame
                    all_jobs_dfs.append(jobs_df)

            except Exception as e:
                print(f"❌ Error scraping for '{keyword}': {e}")

    if not all_jobs_dfs:
        return pd.DataFrame()  # Return an empty DataFrame if no jobs were found

    # Combine all individual DataFrames into one
    return pd.concat(all_jobs_dfs, ignore_index=True)

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
    """Main function to run the job scraping and processing pipeline."""
    metadata = load_metadata(METADATA_FILE)
    existing_jobs_df = get_existing_jobs(CSV_FILE)

    # Scraped jobs are now in a single DataFrame
    scraped_df = scrape_jobs_for_categories(SEARCH_KEYWORD_MAP)

    # FIX: Use the correct method to check if the DataFrame is empty
    if scraped_df.empty:
        print("\nNo jobs found in the scrape. Exiting.")
        return

    scraped_df.drop_duplicates(subset=["title", "company", "location"], inplace=True)
    print(f"\n✨ Total unique jobs scraped: {len(scraped_df)}")

    new_jobs = []
    for _, job in scraped_df.iterrows():
        if not is_fuzzy_duplicate(job, existing_jobs_df):
            new_jobs.append(job)

    if not new_jobs:
        print("✅ No new job postings found. The jobs list is up to date!")
        return

    print(f"\n📢 Found {len(new_jobs)} new jobs!")
    
    new_jobs_to_append = []
    for job in new_jobs:
        date_posted = job.get('date_posted')
        # Ensure date_posted is a datetime object before formatting
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
        print(f"  - 🆕 {job['company']} - {job['title']} ({job['Category']})")

    new_jobs_df = pd.DataFrame(new_jobs_to_append)
    updated_df = pd.concat([existing_jobs_df, new_jobs_df], ignore_index=True)
    updated_df.to_csv(CSV_FILE, index=False)
    
    print(f"\n💾 Successfully added {len(new_jobs_df)} new jobs to {CSV_FILE}.")

if __name__ == "__main__":
    main()