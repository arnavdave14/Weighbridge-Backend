import secrets

def generate_share_token(length: int = 12) -> str:
    """
    Generates a secure, random, URL-safe token.
    Default length of 12 gives approx 16 chars when base64 encoded.
    """
    return secrets.token_urlsafe(length)
