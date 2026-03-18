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

def get_google_drive_service():
    """
    Initialize and return Google Drive service using service account credentials.
    """
    try:
        # Get service account JSON from environment variable
        service_account_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
        if not service_account_json:
            print("Error: GOOGLE_SERVICE_ACCOUNT_JSON environment variable is required")
            sys.exit(1)
        
        # Parse the JSON
        service_account_info = json.loads(service_account_json)
        
        # Create credentials
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=['https://www.googleapis.com/auth/drive.readonly']
        )
        
        # Build the service
        service = build('drive', 'v3', credentials=credentials)
        print("✓ Connected to Google Drive")
        return service
        
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in service account credentials: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error initializing Google Drive service: {e}")
        sys.exit(1)

def download_file_from_drive(service, file_id, file_name, local_path):
    """
    Download a single file from Google Drive.
    """
    try:
        request = service.files().get_media(fileId=file_id)
        file_path = Path(local_path) / file_name
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                print(f"  Download progress: {int(status.progress() * 100)}%", end='\r')
        
        # Write to file
        with open(file_path, 'wb') as f:
            f.write(fh.getvalue())
        
        print(f"  ✓ Downloaded: {file_name}")
        return file_path
        
    except Exception as e:
        print(f"  ✗ Error downloading {file_name}: {e}")
        return None

def list_files_in_folder(service, folder_id, path=''):
    """
    Recursively list all files in a Google Drive folder.
    Returns list of tuples: (file_id, file_name, relative_path)
    """
    files_list = []
    
    try:
        query = f"'{folder_id}' in parents and trashed=false"
        results = service.files().list(
            q=query,
            fields="files(id, name, mimeType)",
            pageSize=1000
        ).execute()
        
        items = results.get('files', [])
        
        for item in items:
            file_name = item['name']
            file_id = item['id']
            mime_type = item['mimeType']
            current_path = os.path.join(path, file_name) if path else file_name
            
            if mime_type == 'application/vnd.google-apps.folder':
                # Recursively process subfolder
                files_list.extend(list_files_in_folder(service, file_id, current_path))
            else:
                # Skip Google Workspace files (Docs, Sheets, etc.) - they need export
                if not mime_type.startswith('application/vnd.google-apps'):
                    files_list.append((file_id, file_name, path))
        
        return files_list
        
    except Exception as e:
        print(f"Error listing files in folder {folder_id}: {e}")
        return []

def download_from_google_drive(folder_id, local_directory):
    """
    Download all files from a Google Drive folder to local directory.
    """
    service = get_google_drive_service()
    local_path = Path(local_directory)
    local_path.mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'='*50}")
    print(f"Downloading files from Google Drive...")
    print(f"{'='*50}\n")
    
    # Get list of all files
    files_list = list_files_in_folder(service, folder_id)
    
    if not files_list:
        print("No files found in the specified Google Drive folder")
        sys.exit(1)
    
    print(f"Found {len(files_list)} file(s) to download\n")
    
    downloaded_files = []
    for file_id, file_name, relative_path in files_list:
        download_path = local_path / relative_path if relative_path else local_path
        result = download_file_from_drive(service, file_id, file_name, download_path)
        if result:
            downloaded_files.append(result)
    
    print(f"\n✓ Downloaded {len(downloaded_files)} file(s)")
    return downloaded_files

def upload_files_to_s3(local_directory, bucket_name, s3_prefix=''):
    """
    Upload all files from a local directory to an S3 bucket.
    """
    s3_client = boto3.client('s3')
    local_path = Path(local_directory)
    
    if not local_path.exists():
        print(f"Error: Directory '{local_directory}' does not exist")
        sys.exit(1)
    
    # Get all files recursively
    files_to_upload = [f for f in local_path.rglob('*') if f.is_file()]
    
    if not files_to_upload:
        print(f"No files found in '{local_directory}'")
        return
    
    print(f"\n{'='*50}")
    print(f"Uploading to AWS S3...")
    print(f"{'='*50}\n")
    print(f"Found {len(files_to_upload)} file(s) to upload\n")
    
    uploaded_count = 0
    failed_count = 0
    
    for file_path in files_to_upload:
        try:
            relative_path = file_path.relative_to(local_path)
            s3_key = str(Path(s3_prefix) / relative_path).replace('\\', '/')
            
            print(f"Uploading: {relative_path} -> s3://{bucket_name}/{s3_key}")
            s3_client.upload_file(str(file_path), bucket_name, s3_key)
            uploaded_count += 1
            
        except ClientError as e:
            print(f"  ✗ Error uploading {file_path}: {e}")
            failed_count += 1
        except Exception as e:
            print(f"  ✗ Unexpected error uploading {file_path}: {e}")
            failed_count += 1
    
    print(f"\n{'='*50}")
    print(f"Upload Summary:")
    print(f"  Successfully uploaded: {uploaded_count}")
    print(f"  Failed: {failed_count}")
    print(f"{'='*50}")
    
    if failed_count > 0:
        sys.exit(1)


def main():
    """
    Main function: Download files from Google Drive and upload to AWS S3.
    """
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
    
    print(f"\n{'='*50}")
    print(f"Google Drive to AWS S3 Transfer")
    print(f"{'='*50}")
    print(f"Configuration:")
    print(f"  Google Drive Folder ID: {google_drive_folder_id}")
    print(f"  Temp Directory: {temp_directory}")
    print(f"  S3 Bucket: {bucket_name}")
    print(f"  S3 Prefix: {s3_prefix or '(root)'}")
    print(f"{'='*50}")
    
    # Step 1: Download from Google Drive
    download_from_google_drive(google_drive_folder_id, temp_directory)
    
    # Step 2: Upload to S3
    upload_files_to_s3(temp_directory, bucket_name, s3_prefix)
    
    print(f"\n{'='*50}")
    print(f"✓ Transfer Complete!")
    print(f"{'='*50}\n")

if __name__ == "__main__":
    main()

