from cryptography.fernet import Fernet, MultiFernet
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
import os
import base64

# Load master keys from environment variable
FERNET_KEYS = os.environ.get("FERNET_KEY")
if not FERNET_KEYS:
    raise ValueError("FERNET_KEY not set in environment.")

# Parse and decode keys
master_keys = [base64.urlsafe_b64decode(k) for k in FERNET_KEYS.split(",")]

def derive_fernet_for_room(room_name: str) -> MultiFernet:
    fernet_list = []
    for master_key in master_keys:
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=room_name.encode(),  # per-room uniqueness
            info=b"chatroom encryption",
            backend=default_backend(),
        )
        derived_key = hkdf.derive(master_key)
        fernet_key = base64.urlsafe_b64encode(derived_key)
        fernet_list.append(Fernet(fernet_key))
    return MultiFernet(fernet_list)

def encrypt_message(message: str, room_name: str) -> str:
    fernet = derive_fernet_for_room(room_name)
    return fernet.encrypt(message.encode()).decode()

def decrypt_message(token: str, room_name: str) -> str:
    fernet = derive_fernet_for_room(room_name)
    return fernet.decrypt(token.encode()).decode()
