#!/usr/bin/env python3
"""
Flask Web Application for Workflow Debugging
Provides GUI for step-by-step debugging of automation workflows
"""

from flask import Flask, render_template, jsonify, request
from werkzeug.utils import secure_filename
from debug_tool import WorkflowDebugger
import os
import json
import tempfile
import uuid
import requests

app = Flask(__name__)
app.config['SECRET_KEY'] = 'workflow-debugger-secret-key-2025'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['UPLOAD_FOLDER'] = os.path.join(tempfile.gettempdir(), 'workflow_debug_uploads')

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Store multiple debugger instances by session
debuggers = {}

# Initialize default debugger (optional - only if files exist and are valid)
BASE_PATH = os.path.dirname(__file__)
try:
    default_debugger = WorkflowDebugger(
        smartflow_log_path=os.path.join(BASE_PATH, 'SmartflowsLOG.json'),
        smartflow_xml_path=os.path.join(BASE_PATH, 'smatflow.xml'),
        blockagent_log_path=os.path.join(BASE_PATH, 'BlockAgentLog.json'),
        blockagent_infra_path=os.path.join(BASE_PATH, 'BlockAgentInfra.json')
    )
    
    # Load data on startup
    print("Loading default workflow data...")
    default_debugger.load_all()
    print("Default data loaded successfully!")
    
    # Store default debugger
    for session_id in default_debugger.get_all_sessions():
        debuggers[session_id] = default_debugger
    print(f"Loaded {len(debuggers)} default session(s)")
except Exception as e:
    print(f"⚠️  Could not load default data: {e}")
    print("📝 App will start without default sessions. Use 'Load Session' to fetch data via API.")
    default_debugger = None

print("✅ Server ready! Use the 'Load Session' button to fetch session data.")
port = int(os.environ.get('PORT', 5000))
print(f"🌐 Server starting on port {port}")


@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')


@app.route('/api/sessions')
def get_sessions():
    """Get list of all sessions"""
    # Collect all unique sessions from all debuggers
    all_sessions = {}
    
    for session_id, debugger in debuggers.items():
        summary = debugger.get_conversation_summary(session_id)
        all_sessions[session_id] = {
            'session_id': session_id,
            'total_entries': summary['total_entries'],
            'conversation_turns': len(summary['conversation']),
            'smartflow_entries': summary['smartflow_entries'],
            'blockagent_entries': summary['blockagent_entries']
        }
    
    return jsonify({'sessions': list(all_sessions.values())})


@app.route('/api/session/<session_id>')
def get_session_details(session_id):
    """Get detailed timeline for a session"""
    debugger = debuggers.get(session_id)
    if not debugger:
        return jsonify({'error': 'Session not found'}), 404
    
    entries = debugger.get_session_timeline(session_id)
    
    timeline = []
    for entry in entries:
        timeline.append({
            'timestamp': entry.timestamp,
            'source': entry.source,
            'log_type': entry.log_type,
            'content': entry.content,
            'block_id': entry.block_id,
            'turn_id': entry.turn_id,
            'transaction_id': entry.transaction_id,
            'role': entry.role,
            'message_type': entry.message_type,
            'metadata': entry.metadata,
            'has_wait_on': entry.has_wait_on,
            'has_error': entry.has_error,
            'error_code': entry.error_code,
            'wait_on_value': entry.wait_on_value
        })
    
    return jsonify({
        'session_id': session_id,
        'timeline': timeline
    })


@app.route('/api/session/<session_id>/conversation')
def get_conversation(session_id):
    """Get conversation summary for a session"""
    debugger = debuggers.get(session_id)
    if not debugger:
        return jsonify({'error': 'Session not found'}), 404
    summary = debugger.get_conversation_summary(session_id)
    return jsonify(summary)


def extract_session_id_from_text(text_data):
    """Extract session ID from the text-based SmartFlow log format"""
    import re
    
    lines = text_data.strip().split('\n')
    
    # Look for SESSION ID header followed by the actual ID
    for i, line in enumerate(lines):
        if 'SESSION ID' in line.upper() and i + 2 < len(lines):
            # The session ID is typically 2 lines after "SESSION ID" header
            # Line format: 1760633456-000000000001105328-SR-000-000000000000DEN140-2EBE8011
            potential_session = lines[i + 2].strip()
            if re.match(r'\d{10}-\d+-SR-\d+-[A-Z0-9]+', potential_session):
                return potential_session
        
        # Also check for FLOW ID
        if 'FLOW ID:' in line:
            # ID is on the next line
            if i + 1 < len(lines):
                potential_session = lines[i + 1].strip()
                if re.match(r'\d{10}-\d+-SR-\d+-[A-Z0-9]+', potential_session):
                    return potential_session
    
    # Fallback: look for session_id in various formats
    session_match = re.search(r'"session_id":\s*"([^"]+)"', text_data)
    if session_match:
        return session_match.group(1)
    
    session_match = re.search(r'"sid":\s*"([^"]+)"', text_data)
    if session_match:
        return session_match.group(1)
    
    # Look for SESSION_ID in message strings
    session_match = re.search(r'"SESSION_ID":\s*"([^"]+)"', text_data)
    if session_match:
        return session_match.group(1)
    
    # Look for session ID pattern anywhere in text
    session_match = re.search(r'(\d{10}-\d+-SR-\d+-[A-Z0-9]+)', text_data)
    if session_match:
        return session_match.group(1)
    
    return None


def parse_smartflow_text_format(text_data):
    """Parse the text-based SmartFlow log format"""
    import re
    import json
    import base64
    
    entries = []
    lines = text_data.strip().split('\n')
    
    i = 0
    while i < len(lines):
        # Look for hostname line (lines with intelepeer.net)
        if i + 2 < len(lines) and 'intelepeer.net' in lines[i]:
            hostname = lines[i].strip()
            logger_path = lines[i + 1].strip()
            timestamp_line = lines[i + 2].strip()
            
            # Try to parse timestamp
            try:
                # Handle ISO format timestamps
                if 'T' in timestamp_line and 'Z' in timestamp_line:
                    timestamp = timestamp_line
                else:
                    # It might be a plain text line, skip
                    i += 1
                    continue
            except:
                i += 1
                continue
            
            # Next line should be the log content (JSON or plain text)
            if i + 3 < len(lines):
                # Check if it's a JSON object or plain text
                log_content_start = i + 3
                first_content_line = lines[log_content_start].strip()  # Strip to handle leading spaces
                
                if first_content_line.startswith('{'):
                    # It's a JSON object
                    json_lines = []
                    brace_count = 0
                    j = log_content_start
                    
                    while j < len(lines):
                        line = lines[j]
                        json_lines.append(line)
                        brace_count += line.count('{') - line.count('}')
                        # Break when we've closed all braces (after processing at least one line)
                        if brace_count == 0 and j > log_content_start:
                            break
                        j += 1
                    
                    try:
                        json_str = '\n'.join(json_lines)
                        log_obj = json.loads(json_str)
                        
                        # Extract the actual log data
                        if 'log' in log_obj:
                            log_data = log_obj['log']
                            
                            # Get session_id from multiple possible fields
                            session_id = (log_data.get('session_id') or 
                                         log_data.get('sid') or 
                                         log_data.get('SESSION_ID') or '')
                            
                            # Decode base64-encoded message if present
                            message = log_data.get('message', '')
                            decoded_data = {}
                            if message and isinstance(message, str):
                                # Check if message starts with base64-like pattern (after "request:" or "response:")
                                if 'request:' in message or 'response:' in message:
                                    try:
                                        # Extract base64 part
                                        base64_match = re.search(r'(?:request|response):\s*([A-Za-z0-9+/=]+)', message)
                                        if base64_match:
                                            base64_str = base64_match.group(1)
                                            decoded_bytes = base64.b64decode(base64_str)
                                            decoded_str = decoded_bytes.decode('utf-8')
                                            decoded_data = json.loads(decoded_str)
                                            # Use decoded data as message for better searching
                                            message = decoded_str
                                    except:
                                        pass  # Keep original message if decoding fails
                            
                            entry = {
                                'id': f"{timestamp}_{hostname}_{i}",
                                'timestamp': timestamp,
                                'host': hostname,
                                'log_file_path': logger_path,
                                'message': message,  # Now contains decoded data if available
                                'message_type': 'smartflow_json',
                                'levelname': log_data.get('levelname', ''),
                                'logger_name': log_data.get('name', ''),
                                'session_id': session_id,
                                'customer_id': log_data.get('customer_id') or log_data.get('cid', ''),
                                'command': log_data.get('command', ''),
                                'decoded_data': decoded_data  # Store decoded data separately
                            }
                            entries.append(entry)
                    except json.JSONDecodeError:
                        # Skip invalid JSON
                        pass
                    
                    i = j + 1
                else:
                    # It's plain text - collect until next hostname or empty line
                    text_lines = []
                    j = log_content_start
                    
                    while j < len(lines):
                        line = lines[j]
                        # Stop if we hit another hostname entry or empty line followed by hostname
                        if 'intelepeer.net' in line:
                            break
                        if line.strip():
                            text_lines.append(line.strip())
                        j += 1
                        # Limit plain text to reasonable size
                        if len(text_lines) > 20:
                            break
                    
                    if text_lines:
                        message = '\n'.join(text_lines)
                        
                        # Try to extract session_id from plain text
                        session_match = re.search(r'(1760\d{6}-\d+-SR-\d+-[A-Z0-9]+)', message)
                        session_id = session_match.group(1) if session_match else ''
                        
                        # Extract ANI if present (format: |Ani: +16028501188|)
                        ani_match = re.search(r'\|Ani:\s*([^|]+)\|', message, re.IGNORECASE)
                        ani = ani_match.group(1).strip() if ani_match else ''
                        
                        # Extract DNIS if present
                        dnis_match = re.search(r'\|Dnis:\s*([^|]+)\|', message, re.IGNORECASE)
                        dnis = dnis_match.group(1).strip() if dnis_match else ''
                        
                        entry = {
                            'id': f"{timestamp}_{hostname}_{i}",
                            'timestamp': timestamp,
                            'host': hostname,
                            'log_file_path': logger_path,
                            'message': message,
                            'message_type': 'smartflow_text',
                            'levelname': 'INFO',
                            'logger_name': logger_path.split('/')[-1] if '/' in logger_path else logger_path,
                            'session_id': session_id,
                            'customer_id': '',
                            'command': '',
                            'ANI': ani,  # Add extracted ANI
                            'DNIS': dnis  # Add extracted DNIS
                        }
                        entries.append(entry)
                    
                    i = j
            else:
                i += 1
        else:
            i += 1
    
    return entries

@app.route('/api/upload', methods=['POST'])
def upload_session():
    """Fetch and load session data using only session_id"""
    try:
        data = request.json
        
        # Get session ID
        session_id = data.get('session_id', '').strip()
        
        if not session_id:
            return jsonify({'error': 'Session ID is required'}), 400
        
        print(f"Fetching logs for session: {session_id}")
        
        # Fetch SmartFlows debug log from API
        print(f"Fetching SmartFlows debug log...")
        smartflow_api_url = f"https://api.intelepeer.com/_rest/v4/sfgen/_internal/debug/session/{session_id}"
        smartflow_api_key = os.environ.get('SMARTFLOW_API_KEY')
        if not smartflow_api_key:
            return jsonify({'error': 'SMARTFLOW_API_KEY environment variable is not set'}), 500
        smartflow_headers = {
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://customer.intelepeer.com",
            "Referer": "https://customer.intelepeer.com/",
            "Authorization": smartflow_api_key
        }
        
        try:
            smartflow_response = requests.get(smartflow_api_url, headers=smartflow_headers, timeout=30)
            smartflow_response.raise_for_status()
            smartflow_log_json = smartflow_response.json()
            print(f"Successfully fetched SmartFlows debug log")
        except requests.RequestException as e:
            return jsonify({'error': f'Failed to fetch SmartFlows debug log: {str(e)}'}), 500
        
        # Fetch BlockAgent log from API
        print(f"Fetching BlockAgent log...")
        blockagent_api_url = f"https://aiservice.intelepeer.com/aihub/v2/_internal/session/{session_id}"
        blockagent_api_key = os.environ.get('BLOCKAGENT_API_KEY')
        if not blockagent_api_key:
            return jsonify({'error': 'BLOCKAGENT_API_KEY environment variable is not set'}), 500
        blockagent_headers = {
            'Authorization': blockagent_api_key
        }
        
        try:
            blockagent_response = requests.get(blockagent_api_url, headers=blockagent_headers, timeout=30)
            blockagent_response.raise_for_status()
            blockagent_log_json = blockagent_response.json()
            print(f"Successfully fetched BlockAgent log")
        except requests.RequestException as e:
            return jsonify({'error': f'Failed to fetch BlockAgent log: {str(e)}'}), 500
        
        # Create unique folder for this session
        upload_id = str(uuid.uuid4())
        upload_folder = os.path.join(app.config['UPLOAD_FOLDER'], upload_id)
        os.makedirs(upload_folder, exist_ok=True)
        
        # Save logs to temporary files
        smartflow_log_path = os.path.join(upload_folder, 'smartflow_log.json')
        blockagent_log_path = os.path.join(upload_folder, 'blockagent_log.json')
        
        with open(smartflow_log_path, 'w') as f:
            json.dump(smartflow_log_json, f)
        
        with open(blockagent_log_path, 'w') as f:
            json.dump(blockagent_log_json, f)
        
        # Use default infrastructure files (can be enhanced later)
        smartflow_xml_path = os.path.join(BASE_PATH, 'smatflow.xml')
        blockagent_infra_path = os.path.join(BASE_PATH, 'BlockAgentInfra.json')
        
        # Create new debugger instance
        new_debugger = WorkflowDebugger(
            smartflow_log_path=smartflow_log_path,
            smartflow_xml_path=smartflow_xml_path,
            blockagent_log_path=blockagent_log_path,
            blockagent_infra_path=blockagent_infra_path
        )
        
        new_debugger.load_all()
        
        # Get session IDs from loaded data
        new_sessions = new_debugger.get_all_sessions()
        
        # Store debugger for each session
        for sess_id in new_sessions:
            debuggers[sess_id] = new_debugger
        
        return jsonify({
            'success': True,
            'sessions': new_sessions,
            'message': f'Successfully loaded session: {session_id}',
            'fetched_from_api': True
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/session/<session_id>/flow')
def get_flow_diagram(session_id):
    """Get visual flow diagram for a session"""
    debugger = debuggers.get(session_id)
    if not debugger:
        return jsonify({'error': 'Session not found'}), 404
    
    flow_data = debugger.extract_flow_diagram()
    return jsonify(flow_data)


@app.route('/api/block/<block_id>')
def get_block_info(block_id):
    """Get infrastructure info for a block"""
    # Try to find block in any debugger
    for debugger in debuggers.values():
        block_info = debugger.get_block_info(block_id)
        if block_info:
            return jsonify(block_info)
    return jsonify({'error': 'Block not found'}), 404


@app.route('/api/infrastructure/blockagent')
def get_blockagent_infrastructure():
    """Get full BlockAgent infrastructure"""
    # Return from first available debugger
    if debuggers:
        first_debugger = next(iter(debuggers.values()))
        return jsonify(first_debugger.blockagent_structure)
    return jsonify({'error': 'No data loaded'}), 404


@app.route('/api/infrastructure/smartflow')
def get_smartflow_infrastructure():
    """Get SmartFlow infrastructure"""
    # Return from first available debugger
    if debuggers:
        first_debugger = next(iter(debuggers.values()))
        return jsonify(first_debugger.smartflow_structure)
    return jsonify({'error': 'No data loaded'}), 404


@app.route('/api/clear_sessions', methods=['POST'])
def clear_sessions():
    """Clear all uploaded sessions (keep default only)"""
    global debuggers
    
    # Keep only default debugger if it exists
    debuggers.clear()
    if default_debugger:
        default_sessions = default_debugger.get_all_sessions()
        for session_id in default_sessions:
            debuggers[session_id] = default_debugger
    
    return jsonify({
        'success': True,
        'message': 'Cleared all uploaded sessions',
        'remaining_sessions': len(debuggers)
    })


@app.route('/api/export')
def export_data():
    """Export all data as JSON"""
    # Export from first available debugger
    if debuggers:
        first_debugger = next(iter(debuggers.values()))
        json_data = first_debugger.export_to_json()
    else:
        json_data = json.dumps({'error': 'No data loaded'})
    
    return app.response_class(
        response=json_data,
        status=200,
        mimetype='application/json'
    )


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)

