import base64
import hashlib
import logging
from datetime import timedelta
from cryptography.fernet import Fernet
from passlib.context import CryptContext
from app.config.settings import settings

logger = logging.getLogger(__name__)

# JWT Configuration for Admin/Employee flows
SECRET_KEY = settings.LOCAL_API_SECRET
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# Password hashing for AdminUsers
# Using pbkdf2_sha256 as primary to avoid environment-specific bcrypt issues on Python 3.14
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    """
    Mint a signed JWT for authentication.
    """
    from datetime import datetime, timezone
    from jose import jwt as jose_jwt
    
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jose_jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Symmetric Encryption for SMTP credentials
# Derive a valid Fernet key from the configured ENCRYPTION_KEY
def _get_fernet() -> Fernet:
    key_source = settings.ENCRYPTION_KEY.encode()
    key_hash = hashlib.sha256(key_source).digest()
    fernet_key = base64.urlsafe_b64encode(key_hash)
    return Fernet(fernet_key)

def encrypt_password(password: str) -> str:
    """Encrypts a plain text password for secure storage."""
    if not password:
        return ""
    try:
        f = _get_fernet()
        encrypted = f.encrypt(password.encode())
        return encrypted.decode()
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        raise RuntimeError("Failed to encrypt SMTP credentials.")

def decrypt_password(encrypted_password: str) -> str:
    """Decrypts an encrypted password for runtime use."""
    if not encrypted_password:
        return ""
    try:
        f = _get_fernet()
        decrypted = f.decrypt(encrypted_password.encode())
        return decrypted.decode()
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        raise RuntimeError("Failed to decrypt SMTP credentials. The encryption key may have changed.")
