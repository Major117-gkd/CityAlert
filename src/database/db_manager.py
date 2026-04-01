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
            # Create table if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS leaks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    user_name TEXT,
                    photo_path TEXT,
                    latitude REAL,
                    longitude REAL,
                    address TEXT,
                    severity TEXT DEFAULT 'Inconnue',
                    ai_severity TEXT DEFAULT 'Inconnue',
                    technician TEXT,
                    status TEXT DEFAULT 'Signalé',
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Migration: Add missing columns if table already existed with old schema
            cursor.execute("PRAGMA table_info(leaks)")
            columns = [info[1] for info in cursor.fetchall()]
            
            if "address" not in columns:
                cursor.execute("ALTER TABLE leaks ADD COLUMN address TEXT")
                print("Migration: Added 'address' column to leaks table.")
            
            if "severity" not in columns:
                cursor.execute("ALTER TABLE leaks ADD COLUMN severity TEXT DEFAULT 'Inconnue'")
                print("Migration: Added 'severity' column to leaks table.")
            
            if "ai_severity" not in columns:
                cursor.execute("ALTER TABLE leaks ADD COLUMN ai_severity TEXT DEFAULT 'Inconnue'")
                print("Migration: Added 'ai_severity' column to leaks table.")
            
            if "technician" not in columns:
                cursor.execute("ALTER TABLE leaks ADD COLUMN technician TEXT")
                print("Migration: Added 'technician' column to leaks table.")
                
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

    def get_all_leaks(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = '''
                SELECT id, user_id, user_name, photo_path, latitude, longitude, 
                       address, severity, ai_severity, technician, status, timestamp 
                FROM leaks 
                ORDER BY timestamp DESC
            '''
            cursor.execute(query)
            return cursor.fetchall()

    def get_user_incidents(self, user_id):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, category, address, severity, status, timestamp FROM incidents WHERE user_id = ? ORDER BY timestamp DESC', (user_id,))
            return cursor.fetchall()

    def update_leak_status(self, leak_id, status, technician=None):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if technician:
                cursor.execute('UPDATE leaks SET status = ?, technician = ? WHERE id = ?', (status, technician, leak_id))
            else:
                cursor.execute('UPDATE leaks SET status = ? WHERE id = ?', (status, leak_id))
            conn.commit()

    def get_leak_by_id(self, leak_id):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM leaks WHERE id = ?', (leak_id,))
            return cursor.fetchone()
