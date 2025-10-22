# Nelson's Block Agent Debug Tool

A powerful web-based debugging tool for analyzing SmartFlows and BlockAgent/GPT Agent logs by session ID.

## Features

- **Session-Based Loading**: Fetch logs automatically using just a session ID
- **Unified Timeline**: Chronologically merged SmartFlows and Agent interactions
- **Smart Filtering**: Filter by PluginId, SmartFlow action types, or custom criteria
- **Agent Detection**: Automatically detects BlockAgent or GPT Agent sessions
- **Rich Summary**: ANI/DNIS, utterances, wait_on events, and agent turn tracking
- **Pretty JSON Display**: Recursive parsing and formatting of nested JSON logs
- **SessionData Management**: Auto-collapse large SessionData fields with expand option

## Quick Start (Local)

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the app:
```bash
python3 app.py
```

3. Open http://localhost:5001 in your browser

4. Click "🔍 Load Session" and enter a session ID

## Deployment to Replit.com

### Step 1: Create a New Repl

1. Go to [Replit.com](https://replit.com) and sign in (or create an account)
2. Click **"+ Create Repl"**
3. Choose **"Import from GitHub"** OR **"Python"** template

### Step 2: Upload Your Files

**Option A: Import from GitHub (Recommended)**
1. First, push your project to GitHub:
   ```bash
   cd "/Users/nmedina/Documents/Documents/ -/ A-P2023-XNQ4Y3/IntelePeer/debug"
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin YOUR_GITHUB_REPO_URL
   git push -u origin main
   ```
2. In Replit, paste your GitHub repository URL
3. Click "Import from GitHub"

**Option B: Manual Upload**
1. Create a new Python Repl
2. Upload these files:
   - `app.py`
   - `debug_tool.py`
   - `requirements.txt`
   - `templates/index.html`
3. Create the `templates/` folder if needed

### Step 3: Configure Replit

1. **Install Dependencies**: Replit should auto-detect `requirements.txt` and install packages
   - If not, run in the Shell: `pip install -r requirements.txt`

2. **Set Run Command**: Click **"Configure the run button"** or edit `.replit` file:
   ```toml
   run = "python3 app.py"
   ```

3. **Configure Environment** (optional): Add these secrets in the "Secrets" tab (🔒):
   - None required for basic functionality
   - API keys are hardcoded in `app.py` (consider moving to secrets for production)

### Step 4: Modify app.py for Replit

Update the Flask app to bind to `0.0.0.0` and use Replit's port:

```python
# At the bottom of app.py, change:
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)

# To:
if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)
```

### Step 5: Run Your App

1. Click the **"Run"** button at the top
2. Replit will start your Flask app
3. A web view will appear showing your app
4. Click the **"Open in new tab"** button to get the public URL

### Step 6: Access Your App Anywhere

- Your app will have a URL like: `https://your-repl-name.username.repl.co`
- Share this URL to access the tool from anywhere
- The app will stay running as long as your Repl is active

## Deployment to Other Platforms

### Render.com

1. Create a new **Web Service**
2. Connect your GitHub repository
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `python3 app.py`
5. Add environment variable: `PORT=10000` (Render uses port 10000)

### Heroku

1. Install Heroku CLI: `brew install heroku/brew/heroku`
2. Create `Procfile`:
   ```
   web: python3 app.py
   ```
3. Deploy:
   ```bash
   heroku login
   heroku create your-app-name
   git push heroku main
   heroku open
   ```

### Railway.app

1. Go to [Railway.app](https://railway.app)
2. Click "New Project" → "Deploy from GitHub"
3. Select your repository
4. Railway auto-detects Python and installs dependencies
5. Your app will be live at `your-app.railway.app`

## Project Structure

```
debug/
├── app.py                 # Flask web server and API endpoints
├── debug_tool.py          # Core log parsing and timeline logic
├── requirements.txt       # Python dependencies
├── templates/
│   └── index.html        # Frontend UI (HTML/CSS/JavaScript)
└── README.md             # This file
```

## Usage

1. **Load Session**: Enter a session ID to fetch SmartFlows and BlockAgent/GPT Agent logs
2. **Navigate Timeline**: Use Previous/Next buttons or click entries to expand
3. **Filter Logs**: Toggle "Show All Entries" or use "SmartFlow Actions" to filter
4. **View Summary**: Click "Summary" to see session overview, agent turns, and statistics
5. **Export**: Download session data as JSON

## API Endpoints

- `GET /api/sessions` - List all loaded sessions
- `POST /api/upload` - Fetch and load logs for a session ID
- `GET /api/session/<session_id>` - Get timeline for a specific session
- `POST /api/clear_sessions` - Clear all sessions except default

## Security Notes

⚠️ **Important**: The current implementation has hardcoded API keys in `app.py`. For production:

1. Move API keys to environment variables:
   ```python
   SMARTFLOW_API_KEY = os.environ.get('SMARTFLOW_API_KEY')
   BLOCKAGENT_API_KEY = os.environ.get('BLOCKAGENT_API_KEY')
   ```

2. In Replit, add these to the "Secrets" tab
3. Consider adding authentication to protect your tool

## Support

For issues or questions, contact Nelson Medina or the IntelePeer development team.

## License

Internal IntelePeer Tool - Proprietary
