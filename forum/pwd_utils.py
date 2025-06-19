import requests

def is_password_compromised(password):
    import hashlib
    sha1 = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
    prefix = sha1[:5]
    suffix = sha1[5:]
    response = requests.get(f"https://api.pwnedpasswords.com/range/{prefix}")
    if response.status_code == 200:
        hashes = (line.split(":") for line in response.text.splitlines())
        return any(h == suffix for h, count in hashes)
    return False  # If API fails, don't block password by default

def validate_password_nist(password):
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if is_password_compromised(password):
        return False, "This password has been found in known data breaches. Choose another."
    return True, ""
