import hashlib

def hash_content(content):
    content_hash = hashlib.sha256(
        content.encode("utf-8")
    ).hexdigest()

    return content_hash
