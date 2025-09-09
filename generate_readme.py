import csv
import json
import sys
from datetime import datetime

CSV_FILE = "jobs.csv"
JSON_FILE = "metadata.json"
OUTPUT_FILE = "README.md"
IEEE_URL = "https://sites.coecis.cornell.edu/ieee/"

# Colors for Shields.io badges
OPEN_COLOR = "2cb5e2"
CLOSED_COLOR = "e22c5a"  # Red for closed applications

# Apply Button Images
APPLY_IMAGE_OPEN = f"https://img.shields.io/badge/Apply-{OPEN_COLOR}?style=flat"
APPLY_IMAGE_CLOSED = f"https://img.shields.io/badge/Closed-{CLOSED_COLOR}?style=flat"

# IEEE at Cornell Badge
IEEE_BADGE = "https://img.shields.io/badge/IEEE%20at%20Cornell-98cbf6?style=flat&logo=ieee&logoColor=black&link"

error = False

# Function to count total job listings
def count_total_listings(csv_file):
    with open(csv_file, "r") as file:
        return sum(1 for _ in csv.DictReader(file))

# Generate Table of Contents
def generate_toc(categories):
    toc = ["## Categories\n"]
    for category in categories:
        anchor = category.lower().replace(" ", "-")  # Convert category to GitHub-style anchor
        toc.append(f"- [{category}](#{anchor})")
    return "\n".join(toc)

# Generate Markdown Header with Badges
def generate_header(total_jobs, categories):
    listings_badge = f"https://img.shields.io/badge/Total%20Listings-{total_jobs}-blue?style=flat"
    return f"""# Summer 2026 Electrical and Computer Engineering Internships by IEEE at Cornell

This list compiles internship opportunities in **Electrical and Computer Engineering**, categorized for easy navigation.
Each listing includes company details, role, location, application links, posting dates, and availability status.

This list is compiled and maintained by [IEEE at Cornell](https://sites.coecis.cornell.edu/ieee/). 

**For updates or corrections, please open a pull request!**

Current Cornell IEEE Maintenance Team:
- [Peter He](https://peterhe.dev/)
- [Dalton Luce](https://www.daltonluce.com/)

**Note:** The scraper is actively being tuned to be better at finding ECE jobs. It will improve with due time!

![Total Listings]({listings_badge})
[![IEEE at Cornell]({IEEE_BADGE})]({IEEE_URL})



{generate_toc(categories)}

---
"""

# gen timestamp
def generate_footer():
    current_date = datetime.today().strftime("%b %d, %Y")
    return f"""---
_Last updated on `{current_date}`. Please verify application deadlines and availability with company websites._
"""

# load metadata
def load_metadata(json_file):
    with open(json_file, "r") as file:
        return json.load(file)

def parse_csv(csv_file):
    jobs_by_category = {}
    with open(csv_file, "r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            category = row["Category"]
            if category not in jobs_by_category:
                jobs_by_category[category] = []
            row["Date Posted"] = format_date(row["Date Posted"])
            jobs_by_category[category].append(row)
    return jobs_by_category

def format_date(date_str):
    return datetime.strptime(date_str, "%Y-%m-%d").strftime("%b %d %Y")

def generate_markdown(jobs_by_category, metadata):

    global error

    markdown_output = [HEADER + "\n"]

    all_categories = list(jobs_by_category.keys())
    ordered_categories = sorted([cat for cat in all_categories if cat != "Software Engineering"])
    if "Software Engineering" in all_categories:
        ordered_categories.append("Software Engineering")

    for category in ordered_categories:
        jobs = jobs_by_category[category]
        if category not in metadata["categories"]:
            print(f"Warning: Category '{category}' not found in metadata. Skipping.")
            error = True
            continue

        markdown_output.append(f"## {category}\n\n")
        markdown_output.append("| Company | Role | Location | Application Link | Date Posted |\n")
        markdown_output.append("|---------|------|----------|------------------|-------------|\n")

        for job in jobs:
            company = job["Company"]
            role = job["Role"]
            location = job["Location"]
            app_link = job["Application Link"]
            date_posted = job["Date Posted"]

            if company in metadata["companies"]:
                company_link = metadata["companies"][company]
            else:
                company_link = "#"
                print(f"Warning: Company '{company}' not found in metadata. Please add it to metadata.json.")

                error = True

            apply_button = f"[![Apply]({APPLY_IMAGE_OPEN})]({app_link})" if job["Open"].lower() == "true" else f"[![Closed]({APPLY_IMAGE_CLOSED})]({app_link})"

            markdown_output.append(f"| [{company}]({company_link}) | {role} | {location} | {apply_button} | {date_posted} |\n")

        markdown_output.append("\n")

    markdown_output.append(generate_footer())

    return "".join(markdown_output)

def main():

    total_jobs = count_total_listings(CSV_FILE)

    metadata = load_metadata(JSON_FILE)
    jobs_by_category = parse_csv(CSV_FILE)

    all_categories = list(jobs_by_category.keys())
    categories = sorted([cat for cat in all_categories if cat != "Software Engineering"])
    if "Software Engineering" in all_categories:
        categories.append("Software Engineering")

    global HEADER
    HEADER = generate_header(total_jobs, categories)

    markdown_content = generate_markdown(jobs_by_category, metadata)

    with open(OUTPUT_FILE, "w") as file:
        file.write(markdown_content)

    if error:
        sys.exit(1)

    print(f"Markdown file '{OUTPUT_FILE}' generated successfully with {total_jobs} listings!")


if __name__ == "__main__":
    main()
