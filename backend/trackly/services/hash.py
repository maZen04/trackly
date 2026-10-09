import hashlib

def generate_hash(content):
    content_hash = hashlib.sha256(
        content.encode("utf-8")
    ).hexdigest()

    return content_hash
