import requests

def is_password_compromised(password):
    import hashlib
    sha1 = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
    prefix = sha1[:5]
    suffix = sha1[5:]
    
    try:
        response = requests.get(f"https://api.pwnedpasswords.com/range/{prefix}", timeout=5)
        if response.status_code == 200:
            hashes = (line.split(":") for line in response.text.splitlines())
            for h, count in hashes:
                if h == suffix:
                    return int(count)
        return 0
    except requests.RequestException:
        return 0  # Fail open to avoid blocking users unnecessarily

def validate_password_nist(password):
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."

    compromise_count = is_password_compromised(password)
    if compromise_count > 0:
        return False, f"This password has appeared in {compromise_count} data breaches. Choose another."

    return True, ""

