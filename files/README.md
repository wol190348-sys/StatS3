# Files Directory

This directory is **not used** by the GitHub Actions workflow.

The workflow downloads files directly from **Google Drive** and uploads them to AWS S3.

You don't need to commit any files to this repository - everything is transferred automatically from your Google Drive folder.

## How it works:

1. You share a Google Drive folder with the service account
2. The workflow downloads files from that folder
3. Files are uploaded directly to AWS S3
4. Temporary files are automatically cleaned up

See the main [README.md](../README.md) for complete setup instructions.

