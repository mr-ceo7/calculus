# Deploying to Render

This guide explains how to deploy the Smart Notes Generator to Render.

## Prerequisites

- GitHub account with the repository pushed
- Render account (free tier available)

## Deployment Steps

### 1. Push to GitHub

Ensure your repository is pushed to GitHub:

```bash
git add .
git commit -m "Prepare for Render deployment"
git push origin master
```

### 2. Connect to Render

1. Go to [render.com](https://render.com)
2. Sign in with GitHub
3. Click "New" > "Web Service"
4. Connect your GitHub repository
5. Select this repository

### 3. Configure the Web Service

In Render dashboard, configure:

**Name:** `smart-notes-generator` (or your preferred name)

**Environment:** Python 3.11+

**Build Command:**
```bash
pip install -r requirements.txt
```

**Start Command:**
```bash
gunicorn -w 4 -b 0.0.0.0:$PORT "wsgi:app"
```

### 4. Environment Variables

Add these environment variables in Render dashboard:

| Key | Value | Notes |
|-----|-------|-------|
| `FLASK_ENV` | `production` | Required |
| `SECRET_KEY` | (generate new) | Generate with: `python -c 'import secrets; print(secrets.token_hex(32))'` |
| `LOG_LEVEL` | `INFO` | Optional, default is INFO |

### 5. Generate Secure Secret Key

Run locally to generate a secure key:

```bash
python -c 'import secrets; print(secrets.token_hex(32))'
```

Copy the output and paste it as the `SECRET_KEY` environment variable in Render.

### 6. Deploy

1. Click "Create Web Service"
2. Render will automatically deploy from your repository
3. Wait for the build to complete (usually 2-3 minutes)

### 7. Monitor Deployment

- Check the "Logs" tab for any errors
- Once deployed, your app will be available at: `https://your-service-name.onrender.com`

## Troubleshooting

### Build Fails
- Check build logs in Render dashboard
- Ensure `requirements.txt` has all dependencies
- Verify `wsgi.py` and `Procfile` are in the root directory

### App Won't Start
- Check that `SECRET_KEY` environment variable is set
- Verify `FLASK_ENV=production` is set
- Look at runtime logs for specific errors

### File Upload Issues
- Render provides ephemeral storage; files are deleted when the service restarts
- For persistent storage, use Render's PostgreSQL or external storage (AWS S3, etc.)

## Production Notes

### Performance
- The free tier on Render has limited resources
- For production use, upgrade to a paid plan
- Current configuration uses 4 worker processes

### Storage
- Uploaded and generated files are stored in `/src/uploads` and `/src/outputs`
- These are temporary and will be cleared on service restart/redeploy
- For persistent storage, implement cloud storage integration

### Security
- Always use a strong `SECRET_KEY` in production
- Consider enabling HTTPS (Render handles this automatically)
- Set `FLASK_ENV=production` to disable debug mode

## Local Development

To run locally with production settings:

```bash
FLASK_ENV=production SECRET_KEY=test-key python run.py
```

Or use the wsgi entry point:

```bash
gunicorn -w 1 "wsgi:app"
```

## Rolling Back

If deployment causes issues:

1. Go to Render dashboard
2. Check "Deployments" history
3. Click on a previous successful deployment
4. Click "Redeploy"

## Support

For Render support, visit: https://render.com/docs
