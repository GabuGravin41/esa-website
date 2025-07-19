# 🚀 Quick Start Deployment Guide

## Deploy Your ESA-KU Website in 5 Minutes!

### Option 1: Render.com (Recommended)

1. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Ready for deployment"
   git push origin main
   ```

2. **Deploy to Render**
   - Go to [render.com](https://render.com)
   - Sign up with GitHub
   - Click "New +" → "Web Service"
   - Connect your repository
   - Render will auto-detect the configuration
   - Click "Create Web Service"

3. **Your site will be live at**: `https://your-app-name.onrender.com`

### Option 2: Railway.app

1. **Push to GitHub** (same as above)

2. **Deploy to Railway**
   - Go to [railway.app](https://railway.app)
   - Sign up with GitHub
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your repository
   - Railway will auto-deploy

3. **Your site will be live at**: `https://your-app-name.railway.app`

## What's Included

✅ **Optimized for free tiers**  
✅ **Automatic database setup**  
✅ **Static file handling**  
✅ **Security configurations**  
✅ **Admin user creation**  
✅ **SSL/HTTPS enabled**  

## Default Admin Access

- **Username**: `admin`
- **Password**: `Nairobi100!`
- **Email**: `esa.kenyattauniv@gmail.com`

**⚠️ Change this password immediately after deployment!**

## Need Help?

- 📖 Full guide: `DEPLOYMENT.md`
- 🐛 Troubleshooting: Check the logs in your deployment platform
- 💬 Community: Django forums, Stack Overflow

## Free Tier Limits

| Platform | Runtime | Database | Bandwidth |
|----------|---------|----------|-----------|
| Render   | 750h/mo | 1GB      | 100GB/mo  |
| Railway  | 500h/mo | 1GB      | 100GB/mo  |

Both platforms will sleep after 15 minutes of inactivity to save resources. 