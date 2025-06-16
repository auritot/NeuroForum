from cryptography.fernet import Fernet
import os

# Load key from environment variable
FERNET_KEY = os.environ.get('FERNET_KEY')
if not FERNET_KEY:
    raise ValueError("FERNET_KEY not set in environment.")

fernet = Fernet(FERNET_KEY.encode())

def encrypt_message(message: str) -> str:
    return fernet.encrypt(message.encode()).decode()

def decrypt_message(token: str) -> str:
    return fernet.decrypt(token.encode()).decode()
