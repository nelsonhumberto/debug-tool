# Quick Deployment Checklist for Replit

## 📋 Pre-Upload Checklist

✅ All documentation files removed  
✅ Sample data files removed  
✅ `venv/` directory ignored (will not upload)  
✅ `app.py` configured for cloud deployment  
✅ `.gitignore` created  
✅ README.md updated with instructions  

## 🚀 Upload to Replit - Step by Step

### Method 1: Direct Upload (Easiest)

1. **Create New Repl**
   - Go to https://replit.com
   - Click "+ Create Repl"
   - Select "Python" template
   - Name it: `nelson-debug-tool` (or your choice)

2. **Upload Files**
   - Delete the default `main.py` if present
   - Upload these files from your project:
     - `app.py`
     - `debug_tool.py`
     - `requirements.txt`
     - `README.md`
   - Create `templates/` folder
   - Upload `templates/index.html`

3. **Configure Run Button**
   - Click the 3 dots next to "Run" button
   - Select "Configure the run button"
   - Set command to: `python3 app.py`
   - Click "Done"

4. **Install Dependencies**
   - Replit should auto-install from `requirements.txt`
   - If not, open Shell tab and run: `pip install -r requirements.txt`

5. **Run Your App**
   - Click the green "Run" button
   - Wait for Flask to start
   - Your app will open in the Webview panel
   - Click "Open in new tab" for the public URL

### Method 2: GitHub Import (Recommended for Version Control)

1. **Push to GitHub First**
   ```bash
   cd "/Users/nmedina/Documents/Documents/ -/ A-P2023-XNQ4Y3/IntelePeer/debug"
   
   # Initialize git (if not already)
   git init
   
   # Add all files (venv/ will be ignored automatically)
   git add .
   
   # Commit
   git commit -m "Nelson's Block Agent Debug Tool - Production Ready"
   
   # Add your GitHub repo (create one first at github.com)
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
   
   # Push
   git push -u origin main
   ```

2. **Import to Replit**
   - Go to https://replit.com
   - Click "+ Create Repl"
   - Select "Import from GitHub"
   - Paste your GitHub repo URL
   - Click "Import from GitHub"
   - Replit will clone and set up everything automatically!

## 🔧 Post-Deployment Configuration

### Optional: Move API Keys to Secrets

For better security, move hardcoded API keys to environment variables:

1. In Replit, click the 🔒 "Secrets" tab (left sidebar)

2. Add these secrets:
   - Key: `SMARTFLOW_API_KEY`, Value: `88aa3ad186ab15c74f8a5c91c67ced94`
   - Key: `BLOCKAGENT_API_KEY`, Value: `3d9e9be5272b49540f9b1a5370695ee3`

3. Update `app.py` to use secrets:
   ```python
   import os
   
   # At the top, replace hardcoded keys with:
   SMARTFLOW_API_KEY = os.environ.get('SMARTFLOW_API_KEY', '88aa3ad186ab15c74f8a5c91c67ced94')
   BLOCKAGENT_API_KEY = os.environ.get('BLOCKAGENT_API_KEY', '3d9e9be5272b49540f9b1a5370695ee3')
   
   # Then use SMARTFLOW_API_KEY and BLOCKAGENT_API_KEY in your code
   ```

## 📱 Access Your App

Once deployed, your app will be available at:
- `https://your-repl-name.username.repl.co`

Example: `https://nelson-debug-tool.nelsonmedina.repl.co`

## 🐛 Troubleshooting

### App won't start
- Check the Console for errors
- Verify `requirements.txt` is in the root directory
- Try manually installing: `pip install flask requests`

### Port errors
- The code already handles PORT environment variable
- Replit automatically sets this, no action needed

### Missing templates
- Make sure `templates/` folder exists
- Verify `index.html` is inside `templates/`

### "Module not found" errors
- Run in Shell: `pip install -r requirements.txt`
- Restart the Repl

## 💡 Tips

- **Keep Repl Awake**: Free Repls sleep after inactivity. Upgrade to Hacker plan for 24/7 uptime
- **Custom Domain**: Upgrade to link your own domain
- **Collaboration**: Share your Repl with team members for collaborative debugging
- **Version Control**: Use GitHub import for easy updates and rollbacks

## 📊 What Gets Uploaded

✅ **Included:**
- `app.py` - Main Flask application
- `debug_tool.py` - Log parsing logic
- `requirements.txt` - Dependencies
- `templates/index.html` - Frontend
- `README.md` - Documentation
- `.gitignore` - Ignore rules

❌ **Excluded (by .gitignore):**
- `venv/` - Virtual environment
- `__pycache__/` - Python cache
- `*.log` - Log files
- `temp_*.json`, `session_*.json` - Temporary files

## 🎉 You're Done!

Your debug tool is now accessible from anywhere in the world!

Share the Replit URL with your team and start debugging sessions remotely.

