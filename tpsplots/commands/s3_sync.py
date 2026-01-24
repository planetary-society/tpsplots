"""S3 sync command for uploading charts to S3."""

from pathlib import Path
from typing import Annotated

import typer


def get_content_type(file_path: str | Path) -> str:
    """Determine the content type based on file extension."""
    extension = Path(file_path).suffix.lower()
    content_types = {
        ".svg": "image/svg+xml",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".pdf": "application/pdf",
        ".html": "text/html",
        ".csv": "text/csv",
    }
    return content_types.get(extension, "application/octet-stream")


def upload_file(s3_client, file_path: str, bucket: str, s3_key: str) -> bool:
    """Upload a file to an S3 bucket."""
    from botocore.exceptions import ClientError

    try:
        s3_client.upload_file(
            file_path, bucket, s3_key, ExtraArgs={"ContentType": get_content_type(file_path)}
        )
        return True
    except ClientError as e:
        print(f"Error uploading {file_path}: {e}")
        return False


def upload_directory(
    local_dir: Path, bucket_name: str, s3_prefix: str, dry_run: bool = False
) -> bool:
    """Upload files from a local directory to an S3 bucket."""
    import boto3

    s3_client = boto3.client("s3")

    if dry_run:
        print(f"DRY RUN: Would upload files from {local_dir} to s3://{bucket_name}/{s3_prefix}")

    # Track successful uploads
    uploaded_count = 0

    # Upload all files in the local directory
    ALLOWED_TYPES = [".csv", ".png", ".svg", ".pptx"]
    for file_path in local_dir.rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in ALLOWED_TYPES:
            # Get the relative path from the local_dir
            relative_path = file_path.relative_to(local_dir)
            s3_key = str(Path(s3_prefix) / relative_path)

            if dry_run:
                print(f"DRY RUN: Would upload {file_path} to s3://{bucket_name}/{s3_key}")
                uploaded_count += 1
            else:
                print(f"Uploading {file_path} to s3://{bucket_name}/{s3_key}")
                if upload_file(s3_client, str(file_path), bucket_name, s3_key):
                    uploaded_count += 1

    # Report results
    if dry_run:
        print(f"DRY RUN: Would upload {uploaded_count} files to s3://{bucket_name}/{s3_prefix}")
    else:
        print(
            f"Upload completed. {uploaded_count} files uploaded to s3://{bucket_name}/{s3_prefix}"
        )
    return True


def s3_sync(
    local_dir: Annotated[
        Path,
        typer.Option("--local-dir", "-d", help="Local directory to upload (required)"),
    ],
    bucket: Annotated[
        str,
        typer.Option("--bucket", "-b", help="S3 bucket name (required)"),
    ],
    prefix: Annotated[
        str,
        typer.Option("--prefix", "-p", help="S3 prefix/path within bucket (required)"),
    ],
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", "-n", help="Preview changes without uploading"),
    ] = False,
) -> None:
    """Upload charts directory to S3 bucket.

    This command uploads chart files (.csv, .png, .svg, .pptx) from a local
    directory to an S3 bucket. AWS credentials must be configured via AWS CLI
    or environment variables.

    Examples:

        tpsplots s3-sync -d charts -b mybucket -p assets/charts/ --dry-run

        tpsplots s3-sync --local-dir charts --bucket mybucket --prefix charts/
    """
    if not local_dir.exists() or not local_dir.is_dir():
        print(f"Error: {local_dir} does not exist or is not a directory")
        raise typer.Exit(code=1)

    success = upload_directory(
        local_dir=local_dir,
        bucket_name=bucket,
        s3_prefix=prefix,
        dry_run=dry_run,
    )

    if not success:
        raise typer.Exit(code=1)
