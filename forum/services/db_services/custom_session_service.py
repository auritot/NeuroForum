import os
import json
from django.db import connection, transaction
from datetime import datetime, timedelta, timezone
from cryptography.fernet import Fernet
import base64

class CustomSessionService:
    def __init__(self):
        FERNET_KEYS = os.environ.get("FERNET_KEY")
        if not FERNET_KEYS:
            raise ValueError("FERNET_KEY not set in environment.")
        
        self.cipher = Fernet(FERNET_KEYS)

    def generate_session_id(self):
        return os.urandom(32).hex()

    def save(self, session_id, session_data, expiry_minutes=30):
        expiry_time = datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes)
        json_data = json.dumps(session_data).encode()
        encrypted = self.cipher.encrypt(json_data)
        encrypted_b64 = base64.b64encode(encrypted).decode()

        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        REPLACE INTO custom_sessions (session_id, session_data, session_expiry)
                        VALUES (%s, %s, %s)
                         """, 
                        [session_id, encrypted_b64, expiry_time]
                    )
                    
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return None

    def load(self, session_id):
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT session_data, session_expiry
                    FROM custom_sessions
                    WHERE session_id = %s
                    """, 
                    [session_id]
                )
                row = cursor.fetchone()
                if not row: return None

                encrypted_b64, expiry = row
                
                if expiry.tzinfo is None:
                    expiry = expiry.replace(tzinfo=timezone.utc)

                if expiry < datetime.now(timezone.utc):
                    self.delete(session_id)
                    return None

                if isinstance(encrypted_b64, bytes):
                    encrypted_data = base64.b64decode(encrypted_b64)
                else:
                    encrypted_data = base64.b64decode(encrypted_b64.encode())
                decrypted_json = self.cipher.decrypt(encrypted_data)
                return json.loads(decrypted_json.decode())
        except Exception as e:
            print(f" An unexpected error occurred: {e}")
            return None

    def delete(self, session_id):
        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        DELETE FROM custom_sessions
                        WHERE session_id = %s
                        """, 
                        [session_id]
                    )
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return None
