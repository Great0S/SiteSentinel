"""
Simple SQLite database for SiteSentinel
Provides persistent storage for websites, monitoring history, and configurations
"""

import sqlite3
import json
import threading
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def retry_database_operation(max_retries=3, base_delay=0.1):
    """Decorator to retry database operations with exponential backoff"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except sqlite3.OperationalError as e:
                    if "database is locked" in str(e).lower() and attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(
                            f"Database locked, retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                        time.sleep(delay)
                        continue
                    else:
                        logger.error(
                            f"Database operation failed after {attempt + 1} attempts: {e}")
                        raise
                except Exception as e:
                    logger.error(f"Unexpected database error: {e}")
                    raise
            return None
        return wrapper
    return decorator


class SiteSentinelDB:
    def __init__(self, db_path: str = 'sitesentinel.db'):
        self.db_path = db_path
        self.lock = threading.Lock()
        self.init_database()

    def _get_connection(self):
        """Get a database connection with proper configuration"""
        conn = sqlite3.connect(
            self.db_path, timeout=120.0, check_same_thread=False)
        # Set optimizations for concurrent access
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA synchronous=NORMAL')
        conn.execute('PRAGMA cache_size=2000')  # Increased cache
        conn.execute('PRAGMA temp_store=MEMORY')
        conn.execute('PRAGMA busy_timeout=60000')  # 60 second busy timeout
        # WAL checkpoint every 1000 pages
        conn.execute('PRAGMA wal_autocheckpoint=1000')
        return conn

    def init_database(self):
        """Initialize database tables"""
        with self._get_connection() as conn:
            # Enable WAL mode for better concurrency
            conn.execute('PRAGMA journal_mode=WAL')
            conn.execute('PRAGMA synchronous=NORMAL')
            conn.execute('PRAGMA cache_size=1000')
            conn.execute('PRAGMA temp_store=MEMORY')

            cursor = conn.cursor()

            # Websites table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS websites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE NOT NULL,
                    status TEXT DEFAULT 'UNKNOWN',
                    ip_address TEXT,
                    status_code INTEGER,
                    response_time TEXT,
                    error_count INTEGER DEFAULT 0,
                    last_check TIMESTAMP,
                    ssl_info TEXT,  -- JSON
                    dns_info TEXT,  -- JSON
                    health_score TEXT,  -- JSON
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Monitoring history table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS monitoring_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    website_id INTEGER,
                    status TEXT,
                    response_time TEXT,
                    status_code INTEGER,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (website_id) REFERENCES websites (id)
                )
            ''')

            # Webhooks table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS webhooks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    url TEXT NOT NULL,
                    events TEXT,  -- JSON array of event types
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_triggered TIMESTAMP
                )
            ''')

            # Settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            conn.commit()

    @retry_database_operation(max_retries=5, base_delay=0.2)
    def add_website(self, url: str, initial_data: Dict = None) -> int:
        """Add a new website to monitor"""
        with self.lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                data = initial_data or {}
                cursor.execute('''
                    INSERT INTO websites (url, status, ip_address, status_code, response_time, 
                                        error_count, ssl_info, dns_info, health_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    url,
                    data.get('status', 'UNKNOWN'),
                    data.get('ip'),
                    data.get('status_code'),
                    data.get('response_time'),
                    data.get('error_count', 0),
                    json.dumps(data.get('ssl', {})),
                    json.dumps(data.get('dns', {})),
                    json.dumps(data.get('health_score', {}))
                ))

                return cursor.lastrowid

    @retry_database_operation(max_retries=5, base_delay=0.2)
    def update_website(self, url: str, data: Dict):
        """Update website monitoring data"""
        with self.lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    UPDATE websites 
                    SET status = ?, ip_address = ?, status_code = ?, response_time = ?,
                        error_count = ?, last_check = ?, ssl_info = ?, dns_info = ?,
                        health_score = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE url = ?
                ''', (
                    data.get('status'),
                    data.get('ip'),
                    data.get('status_code'),
                    data.get('response_time'),
                    data.get('error_count', 0),
                    data.get('last_check'),
                    json.dumps(data.get('ssl', {})),
                    json.dumps(data.get('dns', {})),
                    json.dumps(data.get('health_score', {})),
                    url
                ))

                # Add to history
                self.add_monitoring_record(url, data)

    @retry_database_operation(max_retries=3, base_delay=0.1)
    def add_monitoring_record(self, url: str, data: Dict):
        """Add a monitoring record to history"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Get website ID
            cursor.execute('SELECT id FROM websites WHERE url = ?', (url,))
            result = cursor.fetchone()
            if result:
                website_id = result[0]
                cursor.execute('''
                    INSERT INTO monitoring_history (website_id, status, response_time, status_code)
                    VALUES (?, ?, ?, ?)
                ''', (
                    website_id,
                    data.get('status'),
                    data.get('response_time'),
                    data.get('status_code')
                ))

    def get_all_websites(self) -> Dict[str, Dict]:
        """Get all websites with their current status"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM websites')

            websites = {}
            for row in cursor.fetchall():
                url = row[1]  # url column
                websites[url] = {
                    'status': row[2],
                    'ip': row[3],
                    'status_code': row[4],
                    'response_time': row[5],
                    'error_count': row[6],
                    'last_check': row[7],
                    'ssl': json.loads(row[8] or '{}'),
                    'dns': json.loads(row[9] or '{}'),
                    'health_score': json.loads(row[10] or '{}'),
                    'created_at': row[11],
                    'updated_at': row[12]
                }

            return websites

    def remove_website(self, url: str) -> bool:
        """Remove a website from monitoring"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM websites WHERE url = ?', (url,))
                return cursor.rowcount > 0

    def get_monitoring_history(self, url: str, days: int = 7) -> List[Dict]:
        """Get monitoring history for a website"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT h.* FROM monitoring_history h
                JOIN websites w ON h.website_id = w.id
                WHERE w.url = ? AND h.timestamp >= datetime('now', '-{} days')
                ORDER BY h.timestamp DESC
            '''.format(days), (url,))

            history = []
            for row in cursor.fetchall():
                history.append({
                    'id': row[0],
                    'status': row[2],
                    'response_time': row[3],
                    'status_code': row[4],
                    'timestamp': row[5]
                })

            return history

    def get_uptime_stats(self, url: str, days: int = 30) -> Dict:
        """Calculate uptime statistics for a website"""
        history = self.get_monitoring_history(url, days)

        if not history:
            return {'uptime_percentage': 0, 'total_checks': 0, 'successful_checks': 0}

        total_checks = len(history)
        successful_checks = len([h for h in history if h['status'] == 'UP'])
        uptime_percentage = (successful_checks / total_checks) * \
            100 if total_checks > 0 else 0

        return {
            'uptime_percentage': round(uptime_percentage, 2),
            'total_checks': total_checks,
            'successful_checks': successful_checks,
            'failed_checks': total_checks - successful_checks
        }

    def set_setting(self, key: str, value: str):
        """Set a configuration setting"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO settings (key, value, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                ''', (key, value))

    def get_setting(self, key: str, default_value: str = None) -> str:
        """Get a configuration setting"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
            result = cursor.fetchone()
            return result[0] if result else default_value

    def get_all_settings(self) -> Dict[str, str]:
        """Get all configuration settings"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT key, value FROM settings')
            return {row[0]: row[1] for row in cursor.fetchall()}

    def delete_setting(self, key: str) -> bool:
        """Delete a configuration setting"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM settings WHERE key = ?', (key,))
                return cursor.rowcount > 0


# Global database instance
db = SiteSentinelDB()
