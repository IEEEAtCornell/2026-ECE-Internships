import json
import csv
import jobspy
import os
import pandas as pd
from thefuzz import fuzz
from datetime import datetime

# Load metadata
with open("metadata.json", "r") as f:
    metadata = json.load(f)

CATEGORIES = metadata["categories"]
COMPANIES = metadata["companies"]

# Scrape jobs using jobspy
try:
    jobs = jobspy.scrape_jobs(
        site_name=["indeed", "linkedin", "zip_recruiter", "glassdoor", "google"],
        search_term="electrical computer intern",
        google_search_term="electrical and computer engineering intern jobs",
        results_wanted=20,
        hours_old=72,
        country_indeed="USA",
    )
    print(f"✅ Successfully scraped {len(jobs)} jobs")
except Exception as e:
    print(f"❌ Error scraping jobs: {str(e)}")
    print("🔄 Continuing with existing job data...")
    jobs = []

print(f"Found {len(jobs)} jobs")

# Convert jobs to DataFrame
jobs_df = pd.DataFrame(jobs)
print(jobs_df.keys())


csv_filename = "jobs.csv"
if os.path.exists(csv_filename):
    existing_jobs_df = pd.read_csv(csv_filename)
else:
    existing_jobs_df = pd.DataFrame(columns=["title", "company", "location", "job_url", "date_posted"])

# Function to check if a job is a fuzzy match
def is_fuzzy_duplicate(new_job, existing_jobs, threshold=85):
    for _, row in existing_jobs.iterrows():
        title_score = fuzz.ratio(str(new_job["title"]).lower(), row["Role"].lower())
        company_score = fuzz.ratio(str(new_job["company"]).lower(), row["Company"].lower())
        location_score = fuzz.ratio(str(new_job["location"]).lower(), row["Location"].lower())

        # If all match above the threshold, consider it a duplicate
        if title_score > threshold and company_score > threshold and location_score > threshold:
            return True
    return False

# Identify new jobs using fuzzy matching
new_jobs = []
for _, job in jobs_df.iterrows():
    if not is_fuzzy_duplicate(job, existing_jobs_df):
        new_jobs.append(job)

# Convert new jobs to DataFrame
new_jobs_df = pd.DataFrame(new_jobs)

# Print new jobs
if not new_jobs_df.empty:
    print("\n📢 **New Jobs Found:**\n")
    for _, row in new_jobs_df.iterrows():
        print(f"🆕 {row['company']} - {row['title']} ({row['location']})\n🔗 {row['job_url']}\n📅 {row['date_posted']}\n")
else:
    print("✅ No new job postings today.")