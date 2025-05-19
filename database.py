"""
Database module for handling email storage operations with SQLite.
"""
import os
import json
import sqlite3
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid


class EmailDatabase:
    """
    Database class for storing and retrieving email data with PII masking information.
    Uses SQLite for storage in Hugging Face's persistent directory.
    """

    def __init__(self, connection_string: str = None):
        """
        Initialize the database connection.

        Args:
            connection_string: Database connection string or path.
                             For SQLite, this will be treated as a file path.
        """
        # Hugging Face Spaces has a /data directory that persists between restarts
        self.db_path = connection_string or os.environ.get(
            "DATABASE_PATH",
            "/data/emails.db"  # This path persists in Hugging Face Spaces
        )

        # Get the global access key from environment variables
        self.access_key = os.environ.get(
            "EMAIL_ACCESS_KEY",
            "default_secure_access_key"
        )

        # Ensure the data directory exists
        self._ensure_data_directory()

        self._create_tables()

    def _ensure_data_directory(self):
        """Ensure the data directory exists, and use a fallback if needed."""
        try:
            data_dir = os.path.dirname(self.db_path)
            if data_dir and not os.path.exists(data_dir):
                os.makedirs(data_dir, exist_ok=True)
        except (OSError, PermissionError):
            # If we can't write to /data, fall back to the current directory
            self.db_path = "emails.db"
            print(f"Warning: Using fallback database path: {self.db_path}")

    def _get_connection(self):
        """Get a database connection."""
        return sqlite3.connect(self.db_path)

    def _create_tables(self):
        """Create the necessary tables if they don't exist."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            # Create the emails table to store original emails and their masked versions
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS emails (
                id TEXT PRIMARY KEY,
                original_email TEXT NOT NULL,
                masked_email TEXT NOT NULL,
                masked_entities TEXT NOT NULL,
                category TEXT,
                created_at TEXT NOT NULL
            )
            ''')

            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def _generate_id(self) -> str:
        """Generate a unique ID for the email record."""
        return str(uuid.uuid4())

    def store_email(
        self, original_email: str, masked_email: str,
        masked_entities: List[Dict[str, Any]], category: Optional[str] = None
    ) -> str:
        """
        Store the original email along with its masked version and related information.

        Args:
            original_email: The original email with PII
            masked_email: The masked version of the email
            masked_entities: List of entities that were masked
            category: Optional category of the email

        Returns:
            email_id for future reference
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            email_id = self._generate_id()

            # Store the email data
            cursor.execute(
                'INSERT INTO emails '
                '(id, original_email, masked_email, masked_entities, category, created_at) '
                'VALUES (?, ?, ?, ?, ?, ?)',
                (
                    email_id,
                    original_email,
                    masked_email,
                    json.dumps(masked_entities),  # JSON string for SQLite
                    category,
                    datetime.now().isoformat()
                )
            )

            conn.commit()
            return email_id
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def get_original_email(self, email_id: str, access_key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve the original email with PII using the access key.

        Args:
            email_id: The ID of the email record
            access_key: The security key required to access the original email

        Returns:
            Dictionary with email data or None if not found or access_key is invalid
        """
        # Verify the access key matches the global access key
        if access_key != self.access_key:
            return None

        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute(
                'SELECT id, original_email, masked_email, masked_entities, category, '
                'created_at FROM emails WHERE id = ?',
                (email_id,)
            )

            row = cursor.fetchone()
            if not row:
                return None

            return {
                "id": row[0],
                "original_email": row[1],
                "masked_email": row[2],
                "masked_entities": json.loads(row[3]),  # Convert JSON to dict
                "category": row[4],
                "created_at": row[5]
            }
        finally:
            conn.close()

    def get_email_by_id(self, email_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve the masked email data without the original PII-containing email.

        Args:
            email_id: The ID of the email

        Returns:
            Dictionary with masked email data or None if not found
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute(
                'SELECT id, masked_email, masked_entities, category, created_at '
                'FROM emails WHERE id = ?',
                (email_id,)
            )

            row = cursor.fetchone()
            if not row:
                return None

            return {
                "id": row[0],
                "masked_email": row[1],
                "masked_entities": json.loads(row[2]),  # Convert JSON to dict
                "category": row[3],
                "created_at": row[4]
            }
        finally:
            conn.close()

    def get_email_by_masked_content(self, masked_email: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve the original email using the masked email content.

        Args:
            masked_email: The masked version of the email to search for

        Returns:
            Dictionary with full email data or None if not found
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute(
                'SELECT id, original_email, masked_email, masked_entities, category, '
                'created_at FROM emails WHERE masked_email = ?',
                (masked_email,)
            )

            row = cursor.fetchone()
            if not row:
                return None

            return {
                "id": row[0],
                "original_email": row[1],
                "masked_email": row[2],
                "masked_entities": json.loads(row[3]),  # Convert JSON to dict
                "category": row[4],
                "created_at": row[5]
            }
        finally:
            conn.close()
