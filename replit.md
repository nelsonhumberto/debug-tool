# Nelson's Block Agent Debug Tool

## Overview
A web-based debugging tool for analyzing SmartFlows and BlockAgent/GPT Agent logs by session ID. This application fetches logs from IntelePeer APIs and provides a unified timeline view for debugging automation workflows.

## Current State
- **Status**: Fully functional and deployed on Replit
- **Port**: 5000 (frontend webview)
- **Framework**: Flask 3.0.0 with Python 3.11

## Recent Changes (October 22, 2025)
- Configured for Replit environment
- Moved API keys to environment variables for security
- Updated port from 5001 to 5000 (Replit requirement)
- Configured deployment with Gunicorn for production
- All dependencies installed and tested

## Project Architecture

### Core Components
1. **app.py** - Flask web server and API endpoints
   - Fetches logs from SmartFlows and BlockAgent APIs
   - Provides REST API for session management
   - Serves the frontend UI

2. **debug_tool.py** - Core log parsing and timeline logic
   - Parses SmartFlow and BlockAgent logs
   - Builds unified timeline from multiple sources
   - Extracts conversation summaries and flow diagrams

3. **templates/index.html** - Frontend UI
   - Single-page application with timeline view
   - Session loading and filtering
   - JSON pretty-printing and data visualization

### Key Features
- Session-based loading via API
- Unified timeline merging SmartFlows and Agent interactions
- Smart filtering by PluginId and action types
- Agent detection (BlockAgent vs GPT Agent)
- Wait-on event detection
- Error status code highlighting

## Environment Variables

### Required for Production
- `SMARTFLOW_API_KEY` - API key for SmartFlows debug endpoint (optional, has fallback)
- `BLOCKAGENT_API_KEY` - API key for BlockAgent session endpoint (optional, has fallback)

### System Variables
- `PORT` - Server port (defaults to 5000)

## Deployment

### Development
The workflow runs: `python3 app.py`
- Uses Flask development server
- Debug mode enabled
- Auto-reloading on file changes

### Production
Deployment uses: `gunicorn --bind=0.0.0.0:5000 --reuse-port app:app`
- Production WSGI server
- Autoscale deployment type (stateless)
- No build step required

## Dependencies
- Flask==3.0.0
- Werkzeug==3.0.1
- requests==2.31.0
- gunicorn (for production)

## File Structure
```
.
├── app.py                 # Main Flask application
├── debug_tool.py          # Log parsing engine
├── templates/
│   └── index.html        # Frontend UI
├── requirements.txt      # Python dependencies
├── .gitignore           # Git ignore rules
├── README.md            # User documentation
├── DEPLOY_TO_REPLIT.md  # Deployment guide
└── replit.md            # This file
```

## Usage
1. Open the web interface
2. Click "Load Session" button
3. Enter a session ID
4. View unified timeline with SmartFlow and Agent logs
5. Use filters to narrow down specific events
6. Export session data as JSON if needed

## API Endpoints
- `GET /` - Main UI
- `GET /api/sessions` - List all loaded sessions
- `POST /api/upload` - Fetch and load session by ID
- `GET /api/session/<session_id>` - Get timeline for session
- `GET /api/session/<session_id>/conversation` - Get conversation summary
- `POST /api/clear_sessions` - Clear all sessions
- `GET /api/export` - Export session data as JSON

## Security Notes
- API keys are now environment variables with fallback values
- Not suitable for public deployment without authentication
- Intended for internal IntelePeer use only

## Known Limitations
- Default data files (SmartflowsLOG.json, etc.) are not included in repository
- Application works via API fetching - no local sample data required
- Development server warning (use Gunicorn for production)
