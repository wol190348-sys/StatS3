import os
import sys
import json
import boto3
from botocore.exceptions import ClientError
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
from datetime import datetime
import time

def log_step(message):
    """Print log message with timestamp."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")

def format_size(bytes):
    """Format bytes to human readable size."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024.0:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.2f} TB"

def get_google_drive_service():
    """
    Initialize and return Google Drive service using service account credentials.
    """
    try:
        log_step("🔐 Step 1/4: Authenticating with Google Drive...")
        
        # Get service account JSON from environment variable
        service_account_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
        if not service_account_json:
            print("Error: GOOGLE_SERVICE_ACCOUNT_JSON environment variable is required")
            sys.exit(1)
        
        log_step("   Parsing service account credentials...")
        # Parse the JSON
        service_account_info = json.loads(service_account_json)
        
        log_step("   Creating credentials...")
        # Create credentials
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=['https://www.googleapis.com/auth/drive.readonly']
        )
        
        log_step("   Building Google Drive service...")
        # Build the service
        service = build('drive', 'v3', credentials=credentials)
        log_step("✓ Successfully connected to Google Drive")
        return service
        
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in service account credentials: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error initializing Google Drive service: {e}")
        sys.exit(1)

def download_file_from_drive(service, file_id, file_name, local_path, file_num, total_files):
    """
    Download a single file from Google Drive.
    """
    try:
        log_step(f"   📥 [{file_num}/{total_files}] Downloading: {file_name}")
        
        request = service.files().get_media(fileId=file_id)
        file_path = Path(local_path) / file_name
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        
        done = False
        last_progress = 0
        while not done:
            status, done = downloader.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                # Only print every 10% to reduce log spam
                if progress >= last_progress + 10 or done:
                    print(f"      Progress: {progress}%")
                    last_progress = progress
        
        # Write to file
        with open(file_path, 'wb') as f:
            f.write(fh.getvalue())
        
        file_size = len(fh.getvalue())
        log_step(f"      ✓ Downloaded: {file_name} ({format_size(file_size)})")
        return file_path
        
    except Exception as e:
        print(f"  ✗ Error downloading {file_name}: {e}")
        return None

def list_files_in_folder(service, folder_id, path='', depth=0):
    """
    Recursively list all files in a Google Drive folder.
    Returns list of tuples: (file_id, file_name, relative_path)
    """
    files_list = []
    indent = "   " * depth
    
    try:
        if depth == 0:
            log_step("📂 Step 2/4: Scanning Google Drive folder...")
        else:
            log_step(f"{indent}📁 Scanning subfolder: {path}")
        
        query = f"'{folder_id}' in parents and trashed=false"
        results = service.files().list(
            q=query,
            fields="files(id, name, mimeType)",
            pageSize=1000
        ).execute()
        
        items = results.get('files', [])
        log_step(f"{indent}   Found {len(items)} item(s) in this folder")
        
        folder_count = 0
        file_count = 0
        
        for item in items:
            file_name = item['name']
            file_id = item['id']
            mime_type = item['mimeType']
            current_path = os.path.join(path, file_name) if path else file_name
            
            if mime_type == 'application/vnd.google-apps.folder':
                folder_count += 1
                # Recursively process subfolder
                files_list.extend(list_files_in_folder(service, file_id, current_path, depth + 1))
            else:
                # Skip Google Workspace files (Docs, Sheets, etc.) - they need export
                if not mime_type.startswith('application/vnd.google-apps'):
                    file_count += 1
                    files_list.append((file_id, file_name, path))
                else:
                    log_step(f"{indent}   ⚠ Skipping Google Workspace file: {file_name}")
        
        if depth == 0:
            log_step(f"   Total: {file_count} file(s) and {folder_count} subfolder(s)")
        
        return files_list
        
    except Exception as e:
        print(f"Error listing files in folder {folder_id}: {e}")
        return []

def download_from_google_drive(folder_id, local_directory):
    """
    Download all files from a Google Drive folder to local directory.
    """
    start_time = time.time()
    
    service = get_google_drive_service()
    local_path = Path(local_directory)
    local_path.mkdir(parents=True, exist_ok=True)
    
    # Get list of all files
    files_list = list_files_in_folder(service, folder_id)
    
    if not files_list:
        log_step("❌ No files found in the specified Google Drive folder")
        sys.exit(1)
    
    log_step(f"✓ Found {len(files_list)} file(s) to download")
    log_step("")
    log_step("📥 Step 3/4: Downloading files from Google Drive...")
    
    downloaded_files = []
    failed_files = []
    
    for idx, (file_id, file_name, relative_path) in enumerate(files_list, 1):
        download_path = local_path / relative_path if relative_path else local_path
        result = download_file_from_drive(service, file_id, file_name, download_path, idx, len(files_list))
        if result:
            downloaded_files.append(result)
        else:
            failed_files.append(file_name)
    
    elapsed = time.time() - start_time
    log_step("")
    log_step(f"✓ Download complete! ({elapsed:.1f} seconds)")
    log_step(f"   Successfully downloaded: {len(downloaded_files)} file(s)")
    if failed_files:
        log_step(f"   Failed: {len(failed_files)} file(s)")
        for fname in failed_files:
            log_step(f"      - {fname}")
    
    return downloaded_files

def upload_files_to_s3(local_directory, bucket_name, s3_prefix=''):
    """
    Upload all files from a local directory to an S3 bucket.
    """
    start_time = time.time()
    
    log_step("")
    log_step("☁️  Step 4/4: Uploading files to AWS S3...")
    log_step(f"   Bucket: {bucket_name}")
    log_step(f"   Prefix: {s3_prefix or '(root)'}")
    
    s3_client = boto3.client('s3')
    local_path = Path(local_directory)
    
    if not local_path.exists():
        log_step(f"❌ Error: Directory '{local_directory}' does not exist")
        sys.exit(1)
    
    # Get all files recursively
    log_step("   Preparing file list...")
    files_to_upload = [f for f in local_path.rglob('*') if f.is_file()]
    
    if not files_to_upload:
        log_step(f"❌ No files found in '{local_directory}'")
        return
    
    log_step(f"   Found {len(files_to_upload)} file(s) to upload")
    log_step("")
    
    uploaded_count = 0
    failed_count = 0
    total_size = 0
    
    for idx, file_path in enumerate(files_to_upload, 1):
        try:
            relative_path = file_path.relative_to(local_path)
            s3_key = str(Path(s3_prefix) / relative_path).replace('\\', '/')
            file_size = file_path.stat().st_size
            
            log_step(f"   📤 [{idx}/{len(files_to_upload)}] Uploading: {relative_path}")
            log_step(f"      Size: {format_size(file_size)}, Target: s3://{bucket_name}/{s3_key}")
            
            s3_client.upload_file(str(file_path), bucket_name, s3_key)
            uploaded_count += 1
            total_size += file_size
            log_step(f"      ✓ Upload successful")
            
        except ClientError as e:
            log_step(f"      ✗ Error uploading {file_path}: {e}")
            failed_count += 1
        except Exception as e:
            log_step(f"      ✗ Unexpected error uploading {file_path}: {e}")
            failed_count += 1
    
    elapsed = time.time() - start_time
    log_step("")
    log_step(f"✓ Upload complete! ({elapsed:.1f} seconds)")
    log_step(f"   Successfully uploaded: {uploaded_count} file(s)")
    log_step(f"   Total size: {format_size(total_size)}")
    if failed_count > 0:
        log_step(f"   Failed: {failed_count} file(s)")
    
    if failed_count > 0:
        sys.exit(1)


def main():
    """
    Main function: Download files from Google Drive and upload to AWS S3.
    """
    overall_start = time.time()
    
    # Get configuration from environment variables
    google_drive_folder_id = os.environ.get('GOOGLE_DRIVE_FOLDER_ID')
    bucket_name = os.environ.get('S3_BUCKET_NAME')
    s3_prefix = os.environ.get('S3_PREFIX', '')
    temp_directory = os.environ.get('TEMP_DIRECTORY', './temp_downloads')
    
    if not google_drive_folder_id:
        print("Error: GOOGLE_DRIVE_FOLDER_ID environment variable is required")
        sys.exit(1)
    
    if not bucket_name:
        print("Error: S3_BUCKET_NAME environment variable is required")
        sys.exit(1)
    
    print(f"\n{'='*60}")
    print(f"🚀 Google Drive to AWS S3 Transfer")
    print(f"{'='*60}")
    log_step("📋 Configuration:")
    log_step(f"   Google Drive Folder ID: {google_drive_folder_id}")
    log_step(f"   Temp Directory: {temp_directory}")
    log_step(f"   S3 Bucket: {bucket_name}")
    log_step(f"   S3 Prefix: {s3_prefix or '(root)'}")
    print(f"{'='*60}\n")
    
    # Step 1-3: Download from Google Drive
    download_from_google_drive(google_drive_folder_id, temp_directory)
    
    # Step 4: Upload to S3
    upload_files_to_s3(temp_directory, bucket_name, s3_prefix)
    
    overall_elapsed = time.time() - overall_start
    
    print(f"\n{'='*60}")
    log_step(f"✅ TRANSFER COMPLETE!")
    log_step(f"   Total time: {overall_elapsed:.1f} seconds ({overall_elapsed/60:.1f} minutes)")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()

