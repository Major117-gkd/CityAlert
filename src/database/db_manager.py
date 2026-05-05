import sqlite3
import os
from datetime import datetime

class DBManager:
    def __init__(self, db_path="data/water_leaks.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Create table if it doesn't exist (Sync with Django's table)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS incidents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    user_name TEXT,
                    user_email TEXT,
                    image TEXT,
                    category TEXT DEFAULT 'Eau',
                    latitude REAL,
                    longitude REAL,
                    address TEXT,
                    description TEXT,
                    severity TEXT DEFAULT 'Inconnue',
                    ai_severity TEXT DEFAULT 'Inconnue',
                    assigned_technician_id INTEGER,
                    status TEXT DEFAULT 'Signalé',
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()

    def add_incident(self, user_id, user_name, image_path, category, latitude, longitude, address=None, severity='Inconnue', ai_severity='Inconnue'):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO incidents (user_id, user_name, image, category, latitude, longitude, address, severity, ai_severity, status, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Signalé', CURRENT_TIMESTAMP)
            ''', (user_id, user_name, image_path, category, latitude, longitude, address, severity, ai_severity))
            conn.commit()
            return cursor.lastrowid

    def get_all_incidents(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = '''
                SELECT id, user_id, user_name, image, latitude, longitude, 
                       address, severity, ai_severity, status, timestamp 
                FROM incidents 
                ORDER BY timestamp DESC
            '''
            cursor.execute(query)
            return cursor.fetchall()

    def get_user_incidents(self, user_id):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, category, address, severity, status, timestamp FROM incidents WHERE user_id = ? ORDER BY timestamp DESC', (user_id,))
            return cursor.fetchall()

    def update_incident_status(self, incident_id, status):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE incidents SET status = ? WHERE id = ?', (status, incident_id))
            conn.commit()

    def get_incident_by_id(self, incident_id):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM incidents WHERE id = ?', (incident_id,))
            return cursor.fetchone()
