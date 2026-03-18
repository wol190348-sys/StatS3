# ProJar

## Google Drive to AWS S3 Transfer Tool

Automatically transfer files from Google Drive to AWS S3 using GitHub Actions.

## 📋 Prerequisites

- GitHub repository
- Google Drive account with files to transfer
- AWS account with S3 access
- Google Cloud Project with Drive API enabled
- Service Account credentials

## 🔧 Setup Instructions

### 1. Create Google Cloud Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the **Google Drive API**:
   - Go to "APIs & Services" → "Library"
   - Search for "Google Drive API"
   - Click "Enable"

4. Create a Service Account:
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "Service Account"
   - Give it a name (e.g., "github-drive-transfer")
   - Click "Create and Continue"
   - Skip optional steps, click "Done"

5. Create and Download Service Account Key:
   - Click on the service account you just created
   - Go to "Keys" tab
   - Click "Add Key" → "Create new key"
   - Choose **JSON** format
   - Click "Create" (file will download automatically)

6. Share Google Drive Folder with Service Account:
   - Open your Google Drive folder containing the files
   - Click "Share" button
   - Paste the service account email (looks like: `name@project.iam.gserviceaccount.com`)
   - Give it **Viewer** access
   - Click "Send"

7. Get the Folder ID:
   - Open your Google Drive folder in browser
   - Copy the ID from the URL: `https://drive.google.com/drive/folders/FOLDER_ID_HERE`

### 2. Configure GitHub Secrets

Add these secrets to your GitHub repository:

1. Go to your repository → **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret** for each:

   **AWS Secrets:**
   - **AWS_ACCESS_KEY_ID**: Your AWS access key ID
   - **AWS_SECRET_ACCESS_KEY**: Your AWS secret access key
   - **S3_BUCKET_NAME** (optional): Your default S3 bucket name

   **Google Drive Secret:**
   - **GOOGLE_SERVICE_ACCOUNT_JSON**: Paste the **entire contents** of the JSON file you downloaded
     - Open the JSON file in a text editor
     - Copy ALL the content (including the `{ }` braces)
     - Paste it as the secret value

### 3. Run the Workflow

1. Go to your repository on GitHub
2. Click **Actions** tab
3. Select **Upload Files from Google Drive to AWS S3** workflow
4. Click **Run workflow** button
5. Fill in the required information:
   - **Google Drive Folder ID**: The folder ID from step 1.7
   - **S3 bucket name**: Leave empty to use secret, or enter bucket name
   - **S3 prefix**: Default is `KCSB-Data` (you can change it)
6. Click **Run workflow**

## 📁 Project Structure

```
.
├── .github/
│   └── workflows/
│       └── upload-to-s3.yml    # GitHub Actions workflow
├── upload_to_s3.py              # Python transfer script
├── requirements.txt             # Python dependencies
├── .gitignore                   # Git ignore file
└── README.md                    # This file
```

## 🚀 How It Works

1. **Workflow Triggered**: You manually trigger the GitHub Actions workflow
2. **Download from Google Drive**: Script authenticates using service account and downloads all files from the specified folder
3. **Upload to S3**: Downloaded files are uploaded to your S3 bucket
4. **Cleanup**: Temporary files are removed from GitHub runner
5. **Complete**: You get a success message!

## 🔒 Security Notes

- **Never commit credentials** to your repository
- Service account JSON should only be stored in GitHub Secrets
- AWS credentials should only be stored in GitHub Secrets
- Service account has read-only access to shared folders
- Ensure your S3 bucket has appropriate access policies
- Review IAM permissions for your AWS user

## 📝 Features

- ✅ Downloads files from Google Drive folders
- ✅ Supports nested folder structures
- ✅ Preserves folder hierarchy in S3
- ✅ Manual workflow trigger (runs on-demand)
- ✅ Secure credential management via GitHub Secrets
- ✅ Progress reporting and error handling
- ✅ Automatic cleanup of temporary files
- ✅ Skips Google Workspace files (Docs, Sheets, Slides)

## 🛠️ Local Testing (Optional)

You can test the script locally:

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set environment variables:
   ```powershell
   # Windows PowerShell
   $env:GOOGLE_SERVICE_ACCOUNT_JSON = Get-Content -Raw "path\to\service-account.json"
   $env:GOOGLE_DRIVE_FOLDER_ID = "your-folder-id"
   $env:AWS_ACCESS_KEY_ID = "your-access-key"
   $env:AWS_SECRET_ACCESS_KEY = "your-secret-key"
   $env:S3_BUCKET_NAME = "your-bucket-name"
   $env:S3_PREFIX = "KCSB-Data"
   ```

3. Run the script:
   ```bash
   python upload_to_s3.py
   ```

## ❓ Troubleshooting

### "Error 403: Forbidden" from Google Drive
- Ensure the Google Drive folder is shared with the service account email
- Verify the service account has at least "Viewer" permission

### "Invalid JSON in service account credentials"
- Make sure you copied the entire JSON file content including `{ }`
- Check for any extra spaces or characters

### "Access Denied" from S3
- Verify your AWS credentials are correct
- Ensure your AWS user has S3 write permissions
- Check if the S3 bucket exists and is in the correct region

### No files downloaded
- Check if the folder ID is correct
- Google Workspace files (Docs, Sheets) are skipped - only binary files are transferred
- Verify the service account has access to the folder

## 📄 License

MIT License