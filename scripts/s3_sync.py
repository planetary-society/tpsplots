#!/usr/bin/env python3
"""
s3_sync.py - Utility script to sync the charts/ directory to an S3 bucket.

This can be used to manually upload charts to S3 for testing
before relying on the GitHub Action.

Prerequisites:
- AWS CLI installed and configured with appropriate credentials
- The boto3 Python package (pip install boto3)
"""

import os
import sys
import argparse
import boto3
from pathlib import Path
from botocore.exceptions import ClientError

def upload_file(s3_client, file_path, bucket, s3_key):
    """Upload a file to an S3 bucket."""
    try:
        s3_client.upload_file(
            file_path, 
            bucket, 
            s3_key,
            ExtraArgs={'ContentType': get_content_type(file_path)}
        )
        return True
    except ClientError as e:
        print(f"Error uploading {file_path}: {e}")
        return False

def get_content_type(file_path):
    """Determine the content type based on file extension."""
    extension = Path(file_path).suffix.lower()
    content_types = {
        '.svg': 'image/svg+xml',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        '.pdf': 'application/pdf',
        '.html': 'text/html',
        '.csv': 'text/csv'
    }
    return content_types.get(extension, 'application/octet-stream')

def sync_directory_to_s3(local_dir, bucket_name, s3_prefix, delete=False, dry_run=False):
    """Sync a local directory to an S3 bucket."""
    s3_client = boto3.client('s3')
    local_dir = Path(local_dir)
    
    if dry_run:
        print(f"DRY RUN: Would sync {local_dir} to s3://{bucket_name}/{s3_prefix}")
        
    # Check if the bucket exists (even in dry-run mode to validate credentials)
    try:
        if not dry_run:
            s3_client.head_bucket(Bucket=bucket_name)
        print(f"Using bucket: {bucket_name}")
    except ClientError as e:
        print(f"Error: The bucket {bucket_name} does not exist or you don't have access to it.")
        print(f"Error details: {e}")
        return False
    
    # Get list of existing files in the S3 prefix if we need to delete files
    existing_keys = set()
    if delete and not dry_run:
        try:
            paginator = s3_client.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=bucket_name, Prefix=s3_prefix):
                if 'Contents' in page:
                    existing_keys.update(item['Key'] for item in page['Contents'])
        except ClientError as e:
            print(f"Error listing objects in {s3_prefix}: {e}")
            return False
    
    # Track which keys we've uploaded or kept
    uploaded_keys = set()
    
    # Upload all files in the local directory
    ALLOWED_TYPES = ['.csv', '.png', '.svg', '.pptx']
    for file_path in local_dir.rglob('*'):
        if file_path.is_file() and file_path.suffix.lower() in ALLOWED_TYPES:
            # Get the relative path from the local_dir
            relative_path = file_path.relative_to(local_dir)
            s3_key = str(Path(s3_prefix) / relative_path)
            
            if dry_run:
                print(f"DRY RUN: Would upload {file_path} to s3://{bucket_name}/{s3_key}")
                uploaded_keys.add(s3_key)
            else:
                print(f"Uploading {file_path} to s3://{bucket_name}/{s3_key}")
                if upload_file(s3_client, str(file_path), bucket_name, s3_key):
                    uploaded_keys.add(s3_key)
    
    # Delete files that exist in the bucket but not locally
    if delete and not dry_run:
        keys_to_delete = existing_keys - uploaded_keys
        if keys_to_delete:
            print(f"Deleting {len(keys_to_delete)} files from S3")
            # Delete in batches of 1000 (S3 limit)
            for i in range(0, len(keys_to_delete), 1000):
                batch = list(keys_to_delete)[i:i+1000]
                try:
                    s3_client.delete_objects(
                        Bucket=bucket_name,
                        Delete={'Objects': [{'Key': key} for key in batch]}
                    )
                except ClientError as e:
                    print(f"Error deleting objects: {e}")
    elif delete and dry_run and existing_keys:
        print(f"DRY RUN: Would delete any files in s3://{bucket_name}/{s3_prefix} that don't exist locally")
    
    if dry_run:
        print(f"DRY RUN: Sync completed. Would upload {len(uploaded_keys)} files to s3://{bucket_name}/{s3_prefix}")
    else:
        print(f"Sync completed. {len(uploaded_keys)} files uploaded to s3://{bucket_name}/{s3_prefix}")
    return True

def main():
    parser = argparse.ArgumentParser(description="Sync a local directory to an S3 bucket")
    parser.add_argument("--local-dir", default="charts", help="Local directory to sync (default: charts)")
    parser.add_argument("--bucket", default="planetary", help="S3 bucket name (default: planetary)")
    parser.add_argument("--prefix", default="assets/charts/", help="S3 prefix (default: assets/charts/)")
    parser.add_argument("--delete", action="store_true", help="Delete files in the bucket that don't exist locally")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without uploading")
    
    args = parser.parse_args()
    
    local_dir = Path(args.local_dir)
    if not local_dir.exists() or not local_dir.is_dir():
        print(f"Error: {local_dir} does not exist or is not a directory")
        return 1
    
    success = sync_directory_to_s3(
        local_dir=args.local_dir,
        bucket_name=args.bucket,
        s3_prefix=args.prefix,
        delete=args.delete,
        dry_run=args.dry_run
    )
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())