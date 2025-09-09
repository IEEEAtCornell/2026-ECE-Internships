# GitHub Automation Setup Guide

This guide will help you set up automated job scraping and README generation using GitHub Actions.

## 🚀 Quick Setup

### 1. Enable GitHub Actions
- Go to your repository on GitHub
- Click on the "Actions" tab
- Click "I understand my workflows, go ahead and enable them"

### 2. Configure Repository Secrets (Optional)
Go to **Settings** → **Secrets and variables** → **Actions** and add these secrets if needed:

#### Optional for Job Scraping:
- `JOBSPY_API_KEY` (optional): API key for jobspy if you have one

### 3. Workflow Files
The automation includes one main workflow:

#### Daily Job Updates (`.github/workflows/update-jobs.yml`)
- **Schedule**: Runs daily at 9 AM UTC
- **Manual Trigger**: Available in Actions tab
- **What it does**:
  - Scrapes new job postings
  - Updates `jobs.csv` with new jobs
  - Generates updated `README.md`
  - Commits and pushes changes automatically

## ⚙️ Configuration Options

### Customizing Schedule
Edit the cron expression in the workflow file:

```yaml
schedule:
  - cron: '0 9 * * *'  # Daily at 9 AM UTC
```

### Timezone Conversion
- UTC 9 AM = 5 AM EST / 2 AM PST

### Manual Triggers
You can manually run the workflow:
1. Go to **Actions** tab
2. Select "Update Job Listings"
3. Click **Run workflow**
4. Choose branch and options

## 🔧 Troubleshooting

### Common Issues

1. **Workflow fails to run**
   - Check if Actions are enabled
   - Verify repository secrets are set
   - Check workflow syntax

2. **No new jobs found**
   - This is normal - jobspy may not find new postings daily
   - Use manual trigger with "Force update" option

3. **Permission denied errors**
   - Ensure `GITHUB_TOKEN` has write permissions
   - Check if repository allows Actions to modify files

### Debugging
- Check the **Actions** tab for detailed logs
- Look for error messages in the workflow steps
- Test scripts locally first

## 📊 Monitoring

### Workflow Status
- Green checkmark: Success
- Red X: Failed
- Yellow circle: In progress

## 🎯 Best Practices

1. **Test First**: Run workflows manually before relying on schedules
2. **Monitor Logs**: Check Actions tab regularly for issues
3. **Backup Data**: Keep `jobs.csv` in version control
4. **Update Dependencies**: Regularly update Python packages
5. **Review Changes**: Check auto-committed changes before merging

## 🔄 Customization

### Adding New Job Sources
Edit `scrape.py` to add more job sites or search terms.

### Changing Update Frequency
Modify cron expression in the workflow file.

## 📞 Support

If you encounter issues:
1. Check the GitHub Actions logs
2. Review this documentation
3. Test components individually
4. Open an issue in the repository

---

**Note**: This automation requires the repository to be public or have GitHub Actions enabled for private repositories.
