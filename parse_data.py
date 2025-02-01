import csv
import json
from datetime import datetime

CSV_FILE = "jobs.csv"
JSON_FILE = "metadata.json"
OUTPUT_FILE = "README.md"

HEADER = """# 2026 Electrical and Computer Engineering Internships by IEEE at Cornell

This list compiles internship opportunities in **Electrical and Computer Engineering**, categorized for easy navigation.
Each listing includes company details, role, location, application links, posting dates, and availability status.

This list is compiled and maintained by [IEEE at Cornell](https://sites.coecis.cornell.edu/ieee/). For updates or corrections, please open a pull request!

---

"""

def generate_footer():
    current_date = datetime.today().strftime("%b %d, %Y")
    return f"""
---
_Last updated on `{current_date}`. Please verify application deadlines and availability with company websites._
"""


# Load metadata from JSON file
def load_metadata(json_file):
    with open(json_file, "r") as file:
        return json.load(file)

# Parse CSV file
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

# Generate Markdown tables
def generate_markdown(jobs_by_category, metadata):
    markdown_output = [HEADER]

    for category, jobs in jobs_by_category.items():
        if category not in metadata["categories"]:
            print(f"Warning: Category '{category}' not found in metadata. Skipping.")
            continue

        markdown_output.append(f"## {category}\n\n")
        markdown_output.append("| Company | Role | Location | Application Link | Date Posted | Open |\n")
        markdown_output.append("|---------|------|----------|------------------|-------------|------|\n")

        for job in jobs:
            company = job["Company"]
            role = job["Role"]
            location = job["Location"]
            app_link = job["Application Link"]
            date_posted = job["Date Posted"]
            open_status = "✅" if job["Open"].lower() == "true" else "❌"

            # Verify company URL from metadata
            if company in metadata["companies"]:
                company_link = metadata["companies"][company]
            else:
                company_link = "#"
                print(f"Warning: Company '{company}' not found in metadata. Please add it to metadata.json.")
            markdown_output.append(f"| [{company}]({company_link}) | {role} | {location} | [Apply]({app_link}) | {date_posted} | {open_status} |\n")

        markdown_output.append("\n")

    markdown_output.append(generate_footer())

    return "".join(markdown_output)

# Main function
def main():


    metadata = load_metadata(JSON_FILE)
    jobs_by_category = parse_csv(CSV_FILE)
    markdown_content = generate_markdown(jobs_by_category, metadata)

    with open(OUTPUT_FILE, "w") as file:
        file.write(markdown_content)

    print(f"Markdown file '{OUTPUT_FILE}' generated successfully!")

if __name__ == "__main__":
    main()
