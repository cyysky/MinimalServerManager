# Minimal Server Manager - Log Service
# Handles log parsing, analysis and storage

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import LogSource, LogResult, Server

import re
import os
 
class LogService:
    """
    Service for managing and analyzing server logs
    Handles log parsing, pattern matching and storage
    """
    
    def __init__(self, database_url: str):
        self.logger = logging.getLogger('LogService')
        self.database_url = database_url
        
        # Create database engine and session
        self.engine = create_engine(database_url, connect_args={"check_same_thread": False})
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.Session = SessionLocal
        
        # Log file cache
        self.log_file_cache = {}  # source_id: (file_path, position)
    
    def analyze_logs(self, server_id: int) -> Dict[str, Any]:
        """
        Analyze logs for a specific server
        Returns analysis results and any found patterns
        """
        results = {
            'error_count': 0,
            'warning_count': 0,
            'pattern_matches': [],
            'recent_entries': []
        }
        
        db = self.Session()
        try:
            # Get log sources for this server
            sources = db.query(LogSource).filter(
                LogSource.server_id == server_id,
                LogSource.enabled == True
            ).all()
            
            if not sources:
                return results
            
            # Analyze each log source
            for source in sources:
                log_results = self._parse_log_file(source)
                results['error_count'] += log_results['error_count']
                results['warning_count'] += log_results['warning_count']
                results['pattern_matches'].extend(log_results['pattern_matches'])
                results['recent_entries'].extend(log_results['recent_entries'][:10])  # Limit to 10 recent
            
            # Sort and limit results
            results['pattern_matches'].sort(key=lambda x: x['count'], reverse=True)
            results['pattern_matches'] = results['pattern_matches'][:20]  # Top 20 matches
            results['recent_entries'].sort(key=lambda x: x['timestamp'], reverse=True)
            results['recent_entries'] = results['recent_entries'][:20]  # Most recent 20
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error analyzing logs for server {server_id}: {e}")
            return results
        finally:
            db.close()
    
    def _parse_log_file(self, log_source: LogSource) -> Dict[str, Any]:
        """
        Parse a single log file based on its configuration
        """
        results = {
            'error_count': 0,
            'warning_count': 0,
            'pattern_matches': [],
            'recent_entries': []
        }
        
        try:
            # Check if log file exists and is accessible
            if not os.path.exists(log_source.source_path):
                self.logger.warning(f"Log file not found: {log_source.source_path}")
                return results
            
            # Get current position or start from beginning
            current_position = self.log_file_cache.get(log_source.id, 0)
            
            # Open and read the log file
            with open(log_source.source_path, 'r') as f:
                # Seek to last known position
                if current_position > 0:
                    f.seek(current_position)
                
                # Read new lines
                lines = f.readlines()
                
                # Update position
                if lines:
                    self.log_file_cache[log_source.id] = f.tell()
                
                # Parse each line
                for line_index, line in enumerate(lines):
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Parse line according to log format
                    log_entry = self._parse_log_line(line, log_source.source_type)
                    if log_entry:
                        results['recent_entries'].append(log_entry)
                        
                        # Count errors and warnings (basic patterns)
                        if re.search(r'(ERROR|CRITICAL|FATAL|SEVERE)', line, re.IGNORECASE):
                            results['error_count'] += 1
                        if re.search(r'(WARN|WARNING)', line, re.IGNORECASE):
                            results['warning_count'] += 1
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error parsing log file {log_source.source_path}: {e}")
            return results
    
    def _parse_log_line(self, line: str, log_format: str) -> Optional[Dict[str, Any]]:
        """
        Parse a log line according to the specified format
        """
        try:
            # Common log formats
            if log_format == 'common':
                # Common Log Format: IP - user [timestamp] "request" status size
                pattern = r'(\S+) (\S+) (\S+) \[([^\]]+)\] "([^"]+)" (\d+) (\S+)'
                match = re.match(pattern, line)
                if match:
                    return {
                        'timestamp': self._parse_common_log_time(match.group(4)),
                        'ip': match.group(1),
                        'user': match.group(2),
                        'method': match.group(3),
                        'request': match.group(5),
                        'status': match.group(6),
                        'size': match.group(7),
                        'raw': line
                    }
            
            elif log_format == 'syslog':
                # Syslog format: timestamp hostname process[pid]: message
                pattern = r'(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}) ([^\s]+) ([^:]+): (.+)'
                match = re.match(pattern, line)
                if match:
                    return {
                        'timestamp': match.group(1),
                        'hostname': match.group(2),
                        'process': match.group(3),
                        'message': match.group(4),
                        'raw': line
                    }
            
            elif log_format == 'json':
                # JSON log format
                try:
                    json_data = json.loads(line)
                    return {
                        'json': json_data,
                        'timestamp': json_data.get('timestamp', json_data.get('@timestamp', datetime.now().isoformat())),
                        'raw': line
                    }
                except json.JSONDecodeError:
                    pass
            
            # Fallback: basic parsing for any format
            return {
                'timestamp': datetime.now().isoformat(),
                'message': line,
                'raw': line
            }
            
        except Exception as e:
            self.logger.warning(f"Error parsing log line: {line}. Error: {e}")
            return None
    
    def _parse_common_log_time(self, time_str: str) -> str:
        """
        Parse Common Log Format timestamp
        """
        try:
            # Format: 18/Sep/2023:10:23:45 -0400
            dt = datetime.strptime(time_str, '%d/%b/%Y:%H:%M:%S %z')
            return dt.isoformat()
        except ValueError:
            return datetime.now().isoformat()
    
    def create_log_source(self, server_id: int, name: str, file_path: str,
                          format: str = 'auto', error_pattern: str = None,
                          warning_pattern: str = None,
                          custom_patterns: Dict[str, str] = None,
                          is_active: bool = True) -> bool:
        """
        Create a new log source configuration
        """
        db = self.Session()
        try:
            log_source = LogSource(
                server_id=server_id,
                name=name,
                source_type=format,
                source_path=file_path,
                enabled=is_active
            )
            
            db.add(log_source)
            db.commit()
            
            self.logger.info(f"Created log source: {name}")
            return True
            
        except Exception as e:
            db.rollback()
            self.logger.error(f"Error creating log source: {e}")
            return False
        finally:
            db.close()
    
    def get_log_sources(self, server_id: int = None) -> List[LogSource]:
        """
        Get log sources, optionally filtered by server
        """
        db = self.Session()
        try:
            query = db.query(LogSource)
            if server_id:
                query = query.filter(LogSource.server_id == server_id)
            return query.order_by(LogSource.name).all()
        except Exception as e:
            self.logger.error(f"Error getting log sources: {e}")
            return []
        finally:
            db.close()
    
    def save_log_results(self, server_id: int, log_results: Dict[str, Any]) -> bool:
        """
        Save log analysis results to database
        """
        db = self.Session()
        try:
            # Save overall results
            for key, value in log_results.items():
                if key != 'recent_entries':  # Skip saving individual entries
                    log_result = LogResult(
                        server_id=server_id,
                        result_type=key,
                        result_value=str(value),
                        timestamp=datetime.utcnow()
                    )
                    db.add(log_result)
            
            # Save pattern matches if any
            if 'pattern_matches' in log_results:
                for pattern_match in log_results['pattern_matches']:
                    log_result = LogResult(
                        server_id=server_id,
                        result_type=f"pattern_{pattern_match['name']}",
                        result_value=json.dumps({
                            'count': pattern_match['count'],
                            'examples': pattern_match['examples']
                        }),
                        timestamp=datetime.utcnow()
                    )
                    db.add(log_result)
            
            db.commit()
            self.logger.info(f"Saved log results for server {server_id}")
            return True
            
        except Exception as e:
            db.rollback()
            self.logger.error(f"Error saving log results: {e}")
            return False
        finally:
            db.close()
    
    def get_recent_log_entries(self, log_source_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent log entries from a specific log source
        """
        entries = []
        
        db = self.Session()
        try:
            log_source = db.query(LogSource).filter(LogSource.id == log_source_id).first()
            if not log_source or not os.path.exists(log_source.source_path):
                return entries
            
            # Read last N lines from the log file
            with open(log_source.source_path, 'r') as f:
                # Read lines from the end
                lines = []
                for line in f.readlines()[-limit:]:
                    line = line.strip()
                    if line:
                        parsed = self._parse_log_line(line, log_source.source_type)
                        if parsed:
                            entries.append(parsed)
            
            return entries
            
        except Exception as e:
            self.logger.error(f"Error getting recent log entries: {e}")
            return entries
        finally:
            db.close()

# Singleton instance
log_service = None

def init_log_service(database_url: str):
    global log_service
    if log_service is None:
        log_service = LogService(database_url)
    return log_service