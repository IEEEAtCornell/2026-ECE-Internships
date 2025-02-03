# Contributing Guidelines

Thank you for your interest in contributing to this project! Please follow the guidelines below to ensure a smooth contribution process.

## How to Contribute

1. **Submit Job Listings**  
   - Add new internship or job listings by modifying the [`jobs.csv`](./jobs.csv) file.
   - Ensure that each entry follows the correct format:

        ```csv
        Category,Company,Role,Location,Application Link,Date Posted,Open
        ```

   - Use ISO 8601 format (`YYYY-MM-DD`) for dates.

2. **Update Metadata**  
   - If a new category or company needs to be added, update `metadata.json`.  
   - Ensure company names match those in `jobs.csv` to link them correctly.

3. **Do Not Edit `README.md` Directly**  
   - The `README.md` file is **auto-generated** by a script.
   - To make changes, update `jobs.csv` or `metadata.json` and run the generation script.

4. **Run the Markdown Generator (Optional)**  
   - If you have Python installed, you can test your changes before committing:

     ```sh
     python generate_markdown.py
     ```

   - This will generate `jobs.md` with the latest updates.

5. **Submit a Pull Request (PR)**  
   - Open a PR with a clear description of the changes.
   - Ensure that your updates follow the formatting guidelines.

## Notes

- **Formatting Issues:** If the table doesn't render properly, check for missing or extra commas in `jobs.csv`.
- **Invalid Links:** Verify that company URLs and application links are correct.
- **Job Status:** Ensure the `Open` field is either `true` (✅) or `false` (❌).

## Tips

Add the following [Git pre-commit hook](https://git-scm.com/book/ms/v2/Customizing-Git-Git-Hooks) to automate generating the README.

```sh
#!/bin/sh
python3 generate_readme.py
git add README.md
```

Happy contributing! 🚀
