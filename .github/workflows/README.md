# GitHub Actions Workflows

## Generate and Sync Charts

The `generate-and-sync-charts.yml` workflow automatically generates charts and syncs them to S3.

### Triggers

- **Manual**: Can be triggered manually with optional dry-run mode
- **Scheduled**: Runs daily at 2 AM UTC
- **Push**: Runs on pushes to main branch that affect chart generation

### Required Secrets

The workflow requires the following GitHub Secrets to be configured:

- `AWS_ACCESS_KEY_ID`: AWS access key for S3 upload
- `AWS_SECRET_ACCESS_KEY`: AWS secret key for S3 upload

### Configuration

The workflow uses these default settings:
- **S3 Bucket**: `planetary`
- **S3 Prefix**: `assets/charts/`
- **AWS Region**: `us-east-1`

These can be modified in the workflow file if needed.

### Manual Execution

To run the workflow manually:

1. Go to the **Actions** tab in your repository
2. Select **Generate and Sync Charts**
3. Click **Run workflow**
4. Optionally enable **dry-run mode** to test without uploading to S3

### Outputs

- Generated charts are uploaded as workflow artifacts
- Error logs are uploaded on failure
- Workflow summary shows generation statistics

### Caching

The workflow uses GitHub Actions caching for:
- Python dependencies (pip cache)
- Chart generation data (cachier cache)

This improves performance on subsequent runs.