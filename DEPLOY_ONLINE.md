# Deploy Medical Diagnosis System Online

## 🚀 Quick Deployment Options

### Option 1: Render.com (Recommended - Free & Easy)

**Steps**:
1. **Push to GitHub**:
```bash
cd /Users/praneethkatakam/.gemini/antigravity/scratch/rag_causal_discovery
git add .
git commit -m "Ready for deployment"
git remote add origin https://github.com/YOUR_USERNAME/medical-diagnosis-ai.git
git push -u origin main
```

2. **Deploy on Render**:
   - Go to https://render.com
   - Sign up/Login with GitHub
   - Click "New +" → "Web Service"
   - Connect your GitHub repo
   - Settings:
     - **Name**: medical-diagnosis-ai
     - **Environment**: Python 3
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `uvicorn app:app --host 0.0.0.0 --port $PORT`
   - Click "Create Web Service"

3. **Set Environment Variables** (in Render dashboard):
   - `AUTH_USERNAME` = admin
   - `AUTH_PASSWORD` = your_secure_password

**Result**: Your app will be live at `https://medical-diagnosis-ai.onrender.com`

**Pros**: ✅ Free, ✅ Auto HTTPS, ✅ Easy setup
**Cons**: ⚠️ Sleeps after 15 min inactivity (free tier)

---

### Option 2: Railway.app (Fast & Modern)

**Steps**:
1. Push code to GitHub (same as above)
2. Go to https://railway.app
3. Click "Start a New Project" → "Deploy from GitHub"
4. Select your repo
5. Railway auto-detects Python and deploys!

**Environment Variables**:
- Add `AUTH_USERNAME` and `AUTH_PASSWORD` in settings

**Result**: Live at `https://your-app.railway.app`

**Pros**: ✅ Very fast, ✅ Modern UI, ✅ Auto-deploy on push
**Cons**: ⚠️ $5/month after free trial

---

### Option 3: Vercel (Serverless)

**Note**: Requires slight modification for serverless

**Steps**:
1. Install Vercel CLI:
```bash
npm i -g vercel
```

2. Create `vercel.json`:
```json
{
  "builds": [
    {
      "src": "app.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "app.py"
    }
  ]
}
```

3. Deploy:
```bash
vercel --prod
```

**Pros**: ✅ Free, ✅ Fast, ✅ Global CDN
**Cons**: ⚠️ Serverless limits (10s timeout)

---

### Option 4: Heroku (Classic)

**Steps**:
1. Create `Procfile`:
```
web: uvicorn app:app --host 0.0.0.0 --port $PORT
```

2. Create `runtime.txt`:
```
python-3.11.0
```

3. Deploy:
```bash
heroku login
heroku create medical-diagnosis-ai
git push heroku main
heroku config:set AUTH_USERNAME=admin
heroku config:set AUTH_PASSWORD=your_password
```

**Pros**: ✅ Reliable, ✅ Good docs
**Cons**: ⚠️ No longer free

---

## 🎯 Recommended: Render.com

**Why?**
- ✅ Completely free
- ✅ Auto HTTPS/SSL
- ✅ Easy GitHub integration
- ✅ Auto-deploy on push
- ✅ Built-in monitoring

**5-Minute Setup**:
```bash
# 1. Initialize git (if not done)
git init
git add .
git commit -m "Initial commit"

# 2. Create GitHub repo and push
# (Do this on github.com)

# 3. Deploy on Render
# (Click buttons on render.com)

# Done! Your app is live!
```

---

## 📋 Pre-Deployment Checklist

- [ ] Change `AUTH_PASSWORD` in `.env` to strong password
- [ ] Test locally: `python3 -m uvicorn app:app --host 0.0.0.0 --port 8001`
- [ ] Commit all changes to git
- [ ] Push to GitHub
- [ ] Set environment variables on hosting platform
- [ ] Test deployed URL
- [ ] Share with users!

---

## 🔒 Security Notes

**Before going public**:
1. **Change default password** in `.env`
2. **Use strong password**: 16+ chars, mixed case, symbols
3. **Consider adding**:
   - Rate limiting (already implemented ✅)
   - CORS restrictions (if needed)
   - API key authentication (for production)

---

## 🌐 Your Live URL

After deployment, your app will be accessible at:
- **Render**: `https://medical-diagnosis-ai.onrender.com`
- **Railway**: `https://medical-diagnosis-ai.railway.app`
- **Vercel**: `https://medical-diagnosis-ai.vercel.app`

**Share this URL** with anyone to access your AI Medical Diagnosis System!

---

## 🚀 Next Steps After Deployment

1. **Test all features**:
   - Patient selection
   - Prediction generation
   - DAG visualization
   - Chat interface

2. **Monitor performance**:
   - Check response times
   - Monitor errors in platform dashboard

3. **Share & Iterate**:
   - Get user feedback
   - Make improvements
   - Push updates (auto-deploys!)

---

## 💡 Quick Start Command

```bash
# One-command deploy to Render (after GitHub setup)
echo "Visit https://render.com and click 'New Web Service'"
echo "Connect your GitHub repo and click Deploy!"
```

**That's it!** Your medical diagnosis system will be live on the internet! 🎉
