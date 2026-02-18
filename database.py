import sqlite3
import os
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_path=None):
        if db_path is None:
            db_path = os.getenv("DATABASE_PATH", "echoframe.db")
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    chat_id INTEGER PRIMARY KEY,
                    username TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # Jobs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    status TEXT, -- QUEUED, PROCESSING, COMPLETED, FAILED
                    input_path TEXT,
                    output_path TEXT,
                    error_msg TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    finished_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (chat_id)
                )
            ''')
            conn.commit()

    def add_user(self, chat_id, username):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT OR IGNORE INTO users (chat_id, username) VALUES (?, ?)', (chat_id, username))
            conn.commit()

    def create_job(self, user_id, input_path):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO jobs (user_id, status, input_path) VALUES (?, ?, ?)',
                (user_id, 'QUEUED', input_path)
            )
            job_id = cursor.lastrowid
            conn.commit()
            return job_id

    def update_job_status(self, job_id, status, output_path=None, error_msg=None):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            finished_at = datetime.now().isoformat() if status in ['COMPLETED', 'FAILED'] else None
            if finished_at:
                cursor.execute(
                    'UPDATE jobs SET status = ?, output_path = ?, error_msg = ?, finished_at = ? WHERE id = ?',
                    (status, output_path, error_msg, finished_at, job_id)
                )
            else:
                cursor.execute(
                    'UPDATE jobs SET status = ?, output_path = ?, error_msg = ? WHERE id = ?',
                    (status, output_path, error_msg, job_id)
                )
            conn.commit()

    def get_user_history(self, user_id, limit=5):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT id, status, created_at FROM jobs WHERE user_id = ? AND status = "COMPLETED" ORDER BY created_at DESC LIMIT ?',
                (user_id, limit)
            )
            return cursor.fetchall()

    def get_active_jobs(self, user_id):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT id, status, created_at FROM jobs WHERE user_id = ? AND status IN ("QUEUED", "PROCESSING") ORDER BY created_at ASC',
                (user_id,)
            )
            return cursor.fetchall()

    def get_queue_position(self, job_id):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT COUNT(*) FROM jobs WHERE status = "QUEUED" AND id <= ?',
                (job_id,)
            )
            return cursor.fetchone()[0]
