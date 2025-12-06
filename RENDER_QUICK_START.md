# Quick Render Deployment Checklist

## ✅ Files Created for Deployment

- `wsgi.py` - WSGI entry point for production
- `Procfile` - Process specification for Render
- `render.yaml` - Render configuration (optional, can use dashboard)
- `DEPLOYMENT.md` - Detailed deployment guide
- `.env.example` - Environment variable template
- `requirements.txt` - Updated with gunicorn

## 🚀 Quick Start

### Step 1: Generate Secret Key

```bash
python -c 'import secrets; print(secrets.token_hex(32))'
```

Save this value - you'll need it for Render.

### Step 2: Commit and Push to GitHub

```bash
git add .
git commit -m "Setup Render deployment"
git push origin master
```

### Step 3: Create Web Service on Render

1. Go to https://render.com
2. Click "New" → "Web Service"
3. Select your GitHub repository
4. Fill in the form:
   - **Name**: `smart-notes-generator`
   - **Environment**: `Python 3.11`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn -w 4 -b 0.0.0.0:$PORT "wsgi:app"`

### Step 4: Add Environment Variables

In Render dashboard, go to "Environment" and add:

```
FLASK_ENV=production
SECRET_KEY=<paste your generated key>
LOG_LEVEL=INFO
```

### Step 5: Deploy

Click "Create Web Service" and wait for deployment to complete.

## 📝 Important Notes

- **Uploads are temporary**: Files are deleted when service restarts. For persistent storage, integrate with AWS S3 or similar.
- **Cold starts**: Free tier services sleep after inactivity. Upgrade to "Standard" plan for always-on service.
- **Performance**: Free tier has limited CPU/RAM. Upgrade plan for production use.

## 🔗 Your Live URL

After deployment, your app will be available at:
```
https://<your-service-name>.onrender.com
```

## 🆘 Troubleshooting

See `DEPLOYMENT.md` for detailed troubleshooting guide.

Common issues:
- **Build fails**: Check `requirements.txt` has all dependencies
- **App won't start**: Verify `SECRET_KEY` environment variable is set
- **404 errors**: Ensure static files are properly served

## 📚 More Info

- Full guide: See `DEPLOYMENT.md`
- Render docs: https://render.com/docs
- Flask deployment: https://flask.palletsprojects.com/deployment/
