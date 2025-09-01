# GitHub Actions Workflows

## Two-Step Chart Deployment Process

This repository uses a two-step process for chart deployment to provide a review window before charts go live.

## Step 1: Generate Charts

The `generate-and-sync-charts.yml` workflow generates charts and saves them as artifacts.

### Triggers
- **Manual**: Can be triggered manually anytime
- **Scheduled**: Runs quarterly (every 3 months) at 2 AM UTC

### What it does
1. Generates all charts using the latest data
2. Saves charts as GitHub artifacts (available for 7 days)
3. Provides generation statistics and summary

### Outputs
- **Artifacts**: `generated-charts` containing all chart files
- **Logs**: Error logs if generation fails
- **Summary**: File counts and generation statistics

## Step 2: Upload Charts to S3

The `upload-charts-to-s3.yml` workflow uploads previously generated charts to S3.

### Triggers
- **Manual**: Can be triggered manually with specific run ID
- **Scheduled**: Runs 1 day after chart generation (quarterly + 1 day)

### What it does
1. Downloads charts from artifacts of a previous generation run
2. Uploads charts to S3 bucket
3. Provides upload summary and statistics

### Required Secrets
- `AWS_ACCESS_KEY_ID`: AWS access key for S3 upload
- `AWS_SECRET_ACCESS_KEY`: AWS secret key for S3 upload

### Configuration
- **S3 Bucket**: `planetary`
- **S3 Prefix**: `assets/charts/`
- **AWS Region**: `us-east-1`

## Review Process

### Automatic (Quarterly)
1. **Day 1**: Charts are generated and saved as artifacts
2. **Day 2**: Charts are automatically uploaded to S3
3. **Review window**: 24 hours to inspect charts before they go live

### Manual Process
1. **Generate**: Run "Generate Charts" workflow
2. **Review**: Download and inspect artifacts
3. **Deploy**: Run "Upload Charts to S3" workflow when ready

### Manual Execution

**To generate charts:**
1. Go to Actions → "Generate Charts" → "Run workflow"

**To upload charts:**
1. Go to Actions → "Upload Charts to S3" → "Run workflow"
2. Optionally specify a run ID or use the latest
3. Enable dry-run mode to preview without uploading

### Caching

Both workflows use GitHub Actions caching for:
- Python dependencies (pip cache)
- Chart generation data (cachier cache)

This improves performance on subsequent runs.