# Quick Start Guide: Google Drive to AWS S3

## Step-by-Step Setup

### 1️⃣ Create Google Service Account (5 minutes)

1. Go to https://console.cloud.google.com/
2. Create or select a project
3. Enable **Google Drive API**:
   - Menu → APIs & Services → Library
   - Search "Google Drive API" → Enable

4. Create Service Account:
   - APIs & Services → Credentials
   - Create Credentials → Service Account
   - Name it (e.g., "github-s3-transfer")
   - Create → Done

5. Create JSON Key:
   - Click on service account
   - Keys tab → Add Key → Create New Key
   - Choose JSON → Create
   - **Save this file!**

6. Copy the service account email (e.g., `name@project.iam.gserviceaccount.com`)

### 2️⃣ Share Google Drive Folder

1. Open Google Drive
2. Right-click your folder → Share
3. Paste the service account email
4. Set permission to **Viewer**
5. Uncheck "Notify people"
6. Click Share

### 3️⃣ Get Folder ID

Open your folder in Google Drive. Look at the URL:
```
https://drive.google.com/drive/folders/1a2B3c4D5e6F7g8H9i0J
                                          ^^^^^^^^^^^^^^^^^^^^
                                          This is your Folder ID
```

Copy the Folder ID (everything after `/folders/`)

### 4️⃣ Add GitHub Secrets

Go to your repo → Settings → Secrets and variables → Actions

Add these secrets:

| Secret Name | Value |
|------------|-------|
| `AWS_ACCESS_KEY_ID` | Your AWS access key |
| `AWS_SECRET_ACCESS_KEY` | Your AWS secret key |
| `S3_BUCKET_NAME` | Your S3 bucket name (optional) |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Entire contents of the JSON file |

For the JSON secret:
- Open the downloaded JSON file in Notepad
- Select ALL (Ctrl+A)
- Copy (Ctrl+C)
- Paste into GitHub secret value

### 5️⃣ Run the Workflow

1. Go to **Actions** tab in your repo
2. Click **Upload Files from Google Drive to AWS S3**
3. Click **Run workflow**
4. Enter:
   - **Google Drive Folder ID**: (from step 3)
   - **S3 bucket name**: Leave empty (will use secret) or enter bucket name
   - **S3 prefix**: Default is `KCSB-Data` (folder in S3)
5. Click **Run workflow**

Watch the progress in the Actions tab!

## 🎯 That's it!

Your files will be:
1. Downloaded from Google Drive
2. Uploaded to AWS S3
3. Organized with the same folder structure

## 💡 Tips

- You can run this workflow multiple times
- It will overwrite existing files in S3 with the same name
- The workflow runs on GitHub's servers (not your computer)
- Temporary files are automatically cleaned up
- Google Docs/Sheets/Slides are skipped (use Google Takeout for those)

## ❓ Common Issues

**"403 Forbidden"** → Folder not shared with service account
**"Invalid JSON"** → Didn't copy entire JSON file content
**"Access Denied" (S3)** → Check AWS credentials and bucket permissions
