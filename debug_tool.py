#!/usr/bin/env python3
"""
Workflow Debug Tool - Main Backend
Correlates SmartFlow and BlockAgent logs for debugging automation workflows
"""

import json
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from collections import defaultdict
import re


@dataclass
class LogEntry:
    """Unified log entry structure"""
    timestamp: str
    source: str  # 'smartflow' or 'blockagent'
    session_id: str
    log_type: str
    content: Any
    block_id: Optional[str] = None
    turn_id: Optional[str] = None
    transaction_id: Optional[str] = None
    role: Optional[str] = None  # user/assistant for BlockAgent
    message_type: Optional[str] = None  # for SmartFlow
    metadata: Dict = None
    has_wait_on: bool = False  # Indicates wait_on event
    has_error: bool = False  # Indicates HTTP error (status >= 400)
    error_code: Optional[int] = None  # HTTP status code if error
    wait_on_value: Optional[str] = None  # Value of wait_on field
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        
        # Detect wait_on and errors
        self._detect_important_fields()
    
    def _detect_important_fields(self):
        """Detect wait_on fields and error status codes"""
        import re
        import json as json_lib
        
        def recursive_search(obj, search_key, max_depth=10, current_depth=0, skip_session_data=False):
            """Recursively search for a key in nested structures, optionally skipping SessionData"""
            if current_depth >= max_depth:
                return None
            
            if isinstance(obj, dict):
                # Check all keys at this level
                for key, value in obj.items():
                    # Skip SessionData if requested
                    if skip_session_data and key == 'SessionData':
                        continue
                    
                    if search_key in str(key).lower():
                        return value
                
                # Recurse into values
                for key, value in obj.items():
                    # Skip SessionData if requested
                    if skip_session_data and key == 'SessionData':
                        continue
                    
                    result = recursive_search(value, search_key, max_depth, current_depth + 1, skip_session_data)
                    if result is not None:
                        return result
            elif isinstance(obj, (list, tuple)):
                for item in obj:
                    result = recursive_search(item, search_key, max_depth, current_depth + 1, skip_session_data)
                    if result is not None:
                        return result
            
            return None
        
        content_str = str(self.content) if self.content else ''
        
        # Also check metadata for additional context
        metadata_str = str(self.metadata) if self.metadata else ''
        combined_str = content_str + ' ' + metadata_str
        
        # Check for wait_on (now with recursive search, excluding SessionData)
        if 'wait_on' in combined_str.lower():
            # Try recursive search in nested structures first (SKIP SessionData)
            if isinstance(self.content, (dict, list)):
                wait_on_result = recursive_search(self.content, 'wait_on', skip_session_data=True)
                if wait_on_result:
                    self.wait_on_value = str(wait_on_result)
            
            # Also check metadata recursively (SKIP SessionData)
            if not self.wait_on_value and isinstance(self.metadata, (dict, list)):
                wait_on_result = recursive_search(self.metadata, 'wait_on', skip_session_data=True)
                if wait_on_result:
                    self.wait_on_value = str(wait_on_result)
            
            # Fallback to regex patterns in string (but exclude if inside SessionData)
            if not self.wait_on_value:
                # First check if wait_on appears ONLY in SessionData
                # If SessionData exists, create a version without it
                content_without_session_data = combined_str
                
                # Try to parse as JSON and remove SessionData
                if '{' in combined_str:
                    try:
                        # Try to parse the content
                        if isinstance(self.content, str) and self.content.strip().startswith('{'):
                            parsed = json_lib.loads(self.content)
                            if 'SessionData' in parsed:
                                # Remove SessionData and re-stringify
                                parsed_copy = parsed.copy()
                                parsed_copy.pop('SessionData', None)
                                content_without_session_data = str(parsed_copy)
                        elif isinstance(self.content, dict) and 'SessionData' in self.content:
                            parsed_copy = self.content.copy()
                            parsed_copy.pop('SessionData', None)
                            content_without_session_data = str(parsed_copy)
                    except:
                        pass
                
                # Now search for wait_on with value in the cleaned string
                # Pattern 1: "wait_on": "value"
                match = re.search(r'"?wait_on"?\s*:\s*"([^"]+)"', content_without_session_data, re.IGNORECASE)
                if match:
                    self.wait_on_value = match.group(1)
                else:
                    # Pattern 2: $VAR.wait_on": "value"
                    match = re.search(r'\$[^"]+\.wait_on"\s*:\s*"([^"]+)"', content_without_session_data, re.IGNORECASE)
                    if match:
                        self.wait_on_value = match.group(1)
                    else:
                        # Pattern 3: wait_on=value or wait_on:value without quotes
                        match = re.search(r'wait_on[=:]\s*([^\s,}\]]+)', content_without_session_data, re.IGNORECASE)
                        if match:
                            self.wait_on_value = match.group(1).strip('"\'')
            
            # ONLY set has_wait_on to True if we actually found a VALUE
            if self.wait_on_value:
                self.has_wait_on = True
            else:
                self.has_wait_on = False
        
        # Check for HTTP error status codes (with recursive search, skip SessionData)
        if isinstance(self.content, (dict, list)):
            status_code = recursive_search(self.content, 'statuscode', skip_session_data=True) or recursive_search(self.content, 'status_code', skip_session_data=True)
            if status_code and isinstance(status_code, (int, str)):
                try:
                    code = int(status_code)
                    if code >= 400:
                        self.has_error = True
                        self.error_code = code
                except:
                    pass
        
        # Look for status codes in string content with multiple patterns
        if not self.has_error:
            # Pattern 1: "statuscode": 404
            status_match = re.search(r'"?statuscode"?\s*:\s*(\d+)', combined_str, re.IGNORECASE)
            if not status_match:
                # Pattern 2: status_code: 404
                status_match = re.search(r'status[_\s]code\s*[:=]\s*(\d+)', combined_str, re.IGNORECASE)
            if not status_match:
                # Pattern 3: HTTP status codes like "404" or "500"
                status_match = re.search(r'status[:\s]+([4-5]\d{2})', combined_str, re.IGNORECASE)
            
            if status_match:
                try:
                    code = int(status_match.group(1))
                    if code >= 400:
                        self.has_error = True
                        self.error_code = code
                except:
                    pass


class WorkflowDebugger:
    """Main debugger class that parses and correlates logs"""
    
    def __init__(self, smartflow_log_path: str, smartflow_xml_path: str,
                 blockagent_log_path: str, blockagent_infra_path: str):
        self.smartflow_log_path = smartflow_log_path
        self.smartflow_xml_path = smartflow_xml_path
        self.blockagent_log_path = blockagent_log_path
        self.blockagent_infra_path = blockagent_infra_path
        
        self.smartflow_logs = []
        self.blockagent_logs = []
        self.unified_timeline = []
        self.sessions = defaultdict(list)
        self.smartflow_structure = {}
        self.blockagent_structure = {}
        
    def load_all(self):
        """Load all logs and infrastructure"""
        print("Loading SmartFlow logs...")
        self.load_smartflow_logs()
        print(f"Loaded {len(self.smartflow_logs)} SmartFlow log entries")
        
        print("Loading BlockAgent logs...")
        self.load_blockagent_logs()
        print(f"Loaded {len(self.blockagent_logs)} BlockAgent transactions")
        
        print("Loading infrastructure...")
        self.load_infrastructure()
        
        print("Building unified timeline...")
        self.build_unified_timeline()
        print(f"Created timeline with {len(self.unified_timeline)} entries")
        
        print("Grouping by sessions...")
        self.group_by_sessions()
        print(f"Found {len(self.sessions)} unique sessions")
        
    def load_smartflow_logs(self):
        """Parse SmartFlow logs"""
        with open(self.smartflow_log_path, 'r') as f:
            data = json.load(f)
            
        for entry in data:
            # Extract session ID from message or other fields
            session_id = self._extract_session_id_from_smartflow(entry)
            
            # Parse nested JSON in message field if present
            message = entry.get('message', '')
            actual_timestamp = entry.get('timestamp', '')
            message_content = message
            plugin_id = ''
            log_type = ''
            
            # Check if message contains nested JSON (escaped)
            parsed_data = None
            inner_parsed_data = None
            
            if isinstance(message, str) and message.strip().startswith('{'):
                try:
                    # Parse the first level of nested JSON
                    nested_data = json.loads(message)
                    parsed_data = nested_data
                    
                    # Extract the actual timestamp from nested data if available
                    if 'timestamp' in nested_data:
                        actual_timestamp = nested_data['timestamp']
                    
                    # Check if there's a second level of nesting in 'message' field
                    if 'message' in nested_data and isinstance(nested_data['message'], str):
                        message_content = nested_data['message']
                        # Try to parse the second level
                        if message_content.strip().startswith('{'):
                            try:
                                inner_data = json.loads(message_content)
                                inner_parsed_data = inner_data
                                # PRIORITIZE the inner data for PluginId and LogType (this is where they are!)
                                plugin_id = inner_data.get('PluginId', inner_data.get('pluginId', inner_data.get('plugin_id', '')))
                                log_type = inner_data.get('LogType', inner_data.get('logType', ''))
                            except (json.JSONDecodeError, ValueError):
                                # If second level parsing fails, keep the message as is
                                pass
                    
                    # If we didn't find them in inner data, try the first level
                    if not plugin_id:
                        plugin_id = nested_data.get('PluginId', nested_data.get('pluginId', nested_data.get('plugin_id', '')))
                    if not log_type:
                        # Only use 'level' as last resort, prefer LogType/logType
                        log_type = nested_data.get('LogType', nested_data.get('logType', nested_data.get('level', '')))
                    
                    # If we didn't set message_content yet, use the nested data
                    if not message_content or message_content == message:
                        if 'message' in nested_data:
                            message_content = nested_data['message']
                        else:
                            message_content = json.dumps(nested_data, indent=2)
                            
                except (json.JSONDecodeError, ValueError):
                    # If parsing fails, use the raw message
                    message_content = message
            
            # Also check top-level fields (check multiple variations)
            if not plugin_id:
                plugin_id = entry.get('PluginId', entry.get('pluginId', entry.get('plugin_id', '')))
            if not log_type:
                log_type = entry.get('LogType', entry.get('logType', entry.get('log_type', '')))
            
            # Check if this entry has SessionData (check in INNER data, not outer!)
            has_session_data = False
            if inner_parsed_data and 'SessionData' in inner_parsed_data:
                has_session_data = True
            elif parsed_data and 'SessionData' in parsed_data:
                has_session_data = True
            
            # Check if this is a GPT Agent interaction (EXTCALL with user_message or ai_response)
            gpt_role = None
            gpt_content = None
            
            if plugin_id and plugin_id.startswith('EXTCALL_'):
                # Check for GPT Agent user input (IpdOut with user_message)
                if log_type == 'IpdOut' and inner_parsed_data:
                    ipd_msg = inner_parsed_data.get('IpdMsg', {})
                    if isinstance(ipd_msg, dict):
                        body = ipd_msg.get('body', {})
                        if isinstance(body, dict) and 'user_message' in body:
                            gpt_role = 'user'
                            gpt_content = body.get('user_message', '')
                
                # Check for GPT Agent assistant response (IpdIn or PluginTran with ai_response)
                if not gpt_role and log_type in ['IpdIn', 'PluginTran']:
                    # Look for $EXTCALL_XX.ai_response in the content
                    if inner_parsed_data:
                        # Check if ai_response exists directly
                        ai_response = inner_parsed_data.get('ai_response', '')
                        if not ai_response:
                            # Check in SessionData for $EXTCALL_XX.ai_response
                            session_data = inner_parsed_data.get('SessionData', {})
                            if isinstance(session_data, dict):
                                for key, value in session_data.items():
                                    if '.ai_response' in key and plugin_id.replace('EXTCALL_', '') in key:
                                        ai_response = value
                                        break
                        
                        if ai_response:
                            gpt_role = 'assistant'
                            gpt_content = ai_response
            
            log_entry = LogEntry(
                timestamp=actual_timestamp,
                source='smartflow',
                session_id=session_id,
                log_type=log_type if log_type else 'system_log',
                content=gpt_content if gpt_content else message_content,
                role=gpt_role,  # Set role for GPT agent entries
                message_type=entry.get('message_type', 'unknown'),
                metadata={
                    'host': entry.get('host', ''),
                    'role': entry.get('role', ''),
                    'log_file_path': entry.get('log_file_path', ''),
                    'id': entry.get('id', ''),
                    'ANI': entry.get('ANI', ''),  # Include extracted ANI
                    'DNIS': entry.get('DNIS', ''),  # Include extracted DNIS
                    'PluginId': plugin_id,
                    'logType': log_type,
                    'has_session_data': has_session_data,  # Mark entries with SessionData
                    'agent_type': 'gpt' if gpt_role else None  # Mark GPT agent entries
                }
            )
            self.smartflow_logs.append(log_entry)
            
    def _extract_session_id_from_smartflow(self, entry: Dict) -> str:
        """Extract session ID from SmartFlow log entry"""
        message = entry.get('message', '')
        
        # Parse nested JSON if present
        if isinstance(message, str) and message.strip().startswith('{'):
            try:
                nested_data = json.loads(message)
                # Try to extract from nested message field
                nested_message = nested_data.get('message', '')
                if nested_message:
                    match = re.search(r'\d{10}-\d+-SR-\d+-\d+[A-Z0-9]+-[A-Z0-9]+', nested_message)
                    if match:
                        return match.group(0)
            except (json.JSONDecodeError, ValueError):
                pass
        
        # Try to extract from message string directly
        if isinstance(message, str):
            # Look for pattern like: 1760571668-000000000001105328-SR-000-000000000000DEN130-44144A80
            match = re.search(r'\d{10}-\d+-SR-\d+-\d+[A-Z0-9]+-[A-Z0-9]+', message)
            if match:
                return match.group(0)
        
        # Try from dictionary message
        if isinstance(message, dict):
            session_id = message.get('SESSION_ID', '')
            if session_id:
                return session_id
                
        return 'unknown'
    
    def load_blockagent_logs(self):
        """Parse BlockAgent logs"""
        with open(self.blockagent_log_path, 'r') as f:
            data = json.load(f)
            
        session_id = data.get('session_id', 'unknown')
        transactions = data.get('transactions', [])
        
        # Extract agent info from the agents object
        agents = data.get('agents', {})
        agent_name = ''
        agent_version = ''
        if agents:
            first_agent_id = list(agents.keys())[0]
            agent_data = agents[first_agent_id]
            agent_name = agent_data.get('agent_name', '')
            agent_version = agent_data.get('version', '')
        
        for txn in transactions:
            log_entry = LogEntry(
                timestamp=txn.get('created_date', ''),
                source='blockagent',
                session_id=session_id,
                log_type='conversation',
                content=txn.get('content', ''),
                block_id=txn.get('block_id', ''),
                turn_id=txn.get('turn_id', ''),
                transaction_id=txn.get('transaction_id', ''),
                role=txn.get('role', ''),
                metadata={
                    'agent_id': txn.get('agent_id', ''),
                    'model_name': txn.get('model_name', ''),
                    'completion_tokens': txn.get('completion_tokens'),
                    'prompt_tokens': txn.get('prompt_tokens'),
                    'response_time': txn.get('response_time'),
                    'tool_calls': txn.get('tool_calls', []),
                    'citations': txn.get('citations', []),
                    'agent_name': agent_name,
                    'agent_version': agent_version
                }
            )
            self.blockagent_logs.append(log_entry)
            
    def load_infrastructure(self):
        """Load infrastructure definitions"""
        # Load SmartFlow XML structure
        try:
            with open(self.smartflow_xml_path, 'r') as f:
                content = f.read()
                # Extract XML from the MongoDB export format
                xml_match = re.search(r'<\?xml.*?</chain>', content, re.DOTALL)
                if xml_match:
                    xml_content = xml_match.group(0)
                    # Parse basic structure (simplified for now)
                    self.smartflow_structure = {
                        'raw_xml': xml_content[:1000] + '...',  # Store snippet
                        'type': 'smartflow_xml'
                    }
        except Exception as e:
            print(f"Error loading SmartFlow XML: {e}")
            
        # Load BlockAgent infrastructure
        try:
            with open(self.blockagent_infra_path, 'r') as f:
                self.blockagent_structure = json.load(f)
        except Exception as e:
            print(f"Error loading BlockAgent infrastructure: {e}")
            
    def build_unified_timeline(self):
        """Build unified timeline from all logs"""
        all_logs = self.smartflow_logs + self.blockagent_logs
        
        # Sort by timestamp
        self.unified_timeline = sorted(
            all_logs,
            key=lambda x: self._parse_timestamp(x.timestamp)
        )
        
    def _parse_timestamp(self, ts_str: str) -> datetime:
        """Parse various timestamp formats"""
        if not ts_str:
            return datetime.min
            
        formats = [
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y-%m-%d %H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%S.%f',
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(ts_str, fmt)
            except:
                continue
                
        return datetime.min
        
    def group_by_sessions(self):
        """Group timeline entries by session ID"""
        for entry in self.unified_timeline:
            if entry.session_id != 'unknown':
                self.sessions[entry.session_id].append(entry)
                
    def get_session_timeline(self, session_id: str) -> List[LogEntry]:
        """Get all logs for a specific session"""
        return self.sessions.get(session_id, [])
        
    def get_all_sessions(self) -> List[str]:
        """Get list of all session IDs"""
        return list(self.sessions.keys())
        
    def get_conversation_summary(self, session_id: str) -> Dict:
        """Get a summary of the conversation for a session"""
        entries = self.get_session_timeline(session_id)
        
        conversation = []
        for entry in entries:
            if entry.source == 'blockagent' and entry.role in ['user', 'assistant']:
                conversation.append({
                    'role': entry.role,
                    'content': entry.content,
                    'timestamp': entry.timestamp,
                    'block_id': entry.block_id,
                    'turn_id': entry.turn_id,
                    'metadata': entry.metadata
                })
                
        return {
            'session_id': session_id,
            'conversation': conversation,
            'total_entries': len(entries),
            'smartflow_entries': len([e for e in entries if e.source == 'smartflow']),
            'blockagent_entries': len([e for e in entries if e.source == 'blockagent'])
        }
        
    def get_block_info(self, block_id: str) -> Optional[Dict]:
        """Get infrastructure info for a specific block"""
        if not self.blockagent_structure:
            return None
            
        # Search through block structure
        for block in self.blockagent_structure:
            if block.get('block_id') == block_id:
                return block
                
        return None
        
    def extract_flow_diagram(self) -> Dict:
        """Extract flow diagram from SmartFlow XML and BlockAgent infrastructure"""
        flow = {
            'nodes': [],
            'edges': [],
            'smartflow_nodes': [],
            'blockagent_nodes': []
        }
        
        # Extract BlockAgent blocks and turns
        if self.blockagent_structure and isinstance(self.blockagent_structure, list):
            for idx, block in enumerate(self.blockagent_structure):
                block_id = block.get('block_id', f'block_{idx}')
                block_name = block.get('name', 'Unknown Block')
                
                node = {
                    'id': block_id,
                    'label': block_name,
                    'type': 'blockagent',
                    'turns': []
                }
                
                # Add turns
                if 'turns' in block:
                    for turn in block['turns']:
                        turn_id = turn.get('turn_id', '')
                        turn_name = turn.get('name', '')
                        node['turns'].append({
                            'id': turn_id,
                            'name': turn_name
                        })
                        
                        # Add edges from turn's edges
                        if 'edges' in turn:
                            for edge in turn['edges']:
                                connect_to = edge.get('connect_to')
                                if connect_to and isinstance(connect_to, dict):
                                    target_turn = connect_to.get('turn_id', '')
                                    if target_turn:
                                        flow['edges'].append({
                                            'from': turn_id,
                                            'to': target_turn,
                                            'label': edge.get('name', ''),
                                            'type': 'blockagent'
                                        })
                
                flow['blockagent_nodes'].append(node)
                flow['nodes'].append(node)
        
        # Parse SmartFlow XML for plugin connections
        if self.smartflow_structure and 'raw_xml' in self.smartflow_structure:
            xml_content = self.smartflow_structure['raw_xml']
            try:
                # Extract plugin names and connections using regex
                plugin_pattern = r'<plugin\s+name="([^"]+)"[^>]*label="([^"]*)"[^>]*type="([^"]*)"'
                chain_pattern = r'<chain[^>]*left="([^"]*)"[^>]*right="([^"]*)"'
                
                plugins = re.findall(plugin_pattern, xml_content)
                chains = re.findall(chain_pattern, xml_content)
                
                # Add plugins as nodes
                for name, label, plugin_type in plugins:
                    flow['smartflow_nodes'].append({
                        'id': name,
                        'label': label or name,
                        'type': 'smartflow',
                        'plugin_type': plugin_type
                    })
                    flow['nodes'].append({
                        'id': name,
                        'label': label or name,
                        'type': 'smartflow',
                        'plugin_type': plugin_type
                    })
                
                # Add chain connections as edges
                for left, right in chains:
                    if left and right and right != 'END_CALL':
                        flow['edges'].append({
                            'from': left,
                            'to': right,
                            'type': 'smartflow'
                        })
            except Exception as e:
                print(f"Error parsing SmartFlow XML: {e}")
        
        return flow
    
    def export_to_json(self) -> str:
        """Export all data as JSON"""
        data = {
            'sessions': {},
            'infrastructure': {
                'blockagent': self.blockagent_structure,
                'smartflow': self.smartflow_structure
            }
        }
        
        for session_id in self.get_all_sessions():
            entries = self.get_session_timeline(session_id)
            data['sessions'][session_id] = {
                'entries': [asdict(e) for e in entries],
                'summary': self.get_conversation_summary(session_id)
            }
            
        return json.dumps(data, indent=2, default=str)


if __name__ == '__main__':
    # Test the debugger
    import os
    
    base_path = os.path.dirname(__file__)
    
    debugger = WorkflowDebugger(
        smartflow_log_path=os.path.join(base_path, 'SmartflowsLOG.json'),
        smartflow_xml_path=os.path.join(base_path, 'smatflow.xml'),
        blockagent_log_path=os.path.join(base_path, 'BlockAgentLog.json'),
        blockagent_infra_path=os.path.join(base_path, 'BlockAgentInfra.json')
    )
    
    debugger.load_all()
    
    print("\n=== Sessions Found ===")
    for session_id in debugger.get_all_sessions():
        print(f"Session: {session_id}")
        summary = debugger.get_conversation_summary(session_id)
        print(f"  - Total entries: {summary['total_entries']}")
        print(f"  - Conversation turns: {len(summary['conversation'])}")
        print()

