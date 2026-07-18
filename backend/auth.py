import sqlite3
import hashlib
import secrets
import pyotp
import qrcode
import io
import base64
import datetime

DB_PATH = 'compliance.db'

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

def init_auth_tables():
    """Create users table if it doesn't exist."""
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            full_name TEXT DEFAULT '',
            role TEXT DEFAULT 'analyst',
            totp_secret TEXT DEFAULT NULL,
            totp_enabled INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def hash_password(password, salt=None):
    """Hash a password with a salt using SHA-256."""
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return hashed, salt

def register_user(username, password, full_name=''):
    """Register a new user. Returns user dict or raises error."""
    conn = get_db()
    try:
        # Check if user already exists
        existing = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if existing:
            raise ValueError("Username already exists")
        
        password_hash, salt = hash_password(password)
        conn.execute(
            "INSERT INTO users (username, password_hash, salt, full_name) VALUES (?, ?, ?, ?)",
            (username, password_hash, salt, full_name)
        )
        conn.commit()
        user = conn.execute("SELECT id, username, full_name, role, totp_enabled FROM users WHERE username = ?", (username,)).fetchone()
        return dict(user)
    finally:
        conn.close()

def authenticate_user(username, password):
    """Verify username/password. Returns user dict or None."""
    conn = get_db()
    try:
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if not user:
            return None
        user_dict = dict(user)
        password_hash, _ = hash_password(password, user_dict['salt'])
        if password_hash != user_dict['password_hash']:
            return None
        # Return safe user info (no password/salt)
        return {
            'id': user_dict['id'],
            'username': user_dict['username'],
            'full_name': user_dict['full_name'],
            'role': user_dict['role'],
            'totp_enabled': bool(user_dict['totp_enabled']),
        }
    finally:
        conn.close()

def setup_totp(username):
    """Generate a new TOTP secret and QR code for 2FA setup."""
    conn = get_db()
    try:
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if not user:
            raise ValueError("User not found")
        
        # Generate TOTP secret
        secret = pyotp.random_base32()
        
        # Save the secret (but don't enable yet until verified)
        conn.execute("UPDATE users SET totp_secret = ? WHERE username = ?", (secret, username))
        conn.commit()
        
        # Generate provisioning URI for Google Authenticator
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(name=username, issuer_name="Veritas AML")
        
        # Generate QR code as base64
        qr = qrcode.QRCode(version=1, box_size=6, border=2)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        qr_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        return {
            'secret': secret,
            'qr_code': f"data:image/png;base64,{qr_base64}",
            'manual_code': secret,
        }
    finally:
        conn.close()

def verify_and_enable_totp(username, otp_code):
    """Verify the OTP and enable 2FA if correct."""
    conn = get_db()
    try:
        user = conn.execute("SELECT totp_secret FROM users WHERE username = ?", (username,)).fetchone()
        if not user or not user['totp_secret']:
            return False
        
        totp = pyotp.TOTP(user['totp_secret'])
        if totp.verify(otp_code, valid_window=1):
            conn.execute("UPDATE users SET totp_enabled = 1 WHERE username = ?", (username,))
            conn.commit()
            return True
        return False
    finally:
        conn.close()

def verify_totp(username, otp_code):
    """Verify a TOTP code during login."""
    conn = get_db()
    try:
        user = conn.execute("SELECT totp_secret, totp_enabled FROM users WHERE username = ?", (username,)).fetchone()
        if not user or not user['totp_enabled'] or not user['totp_secret']:
            return False
        
        totp = pyotp.TOTP(user['totp_secret'])
        return totp.verify(otp_code, valid_window=1)
    finally:
        conn.close()

def disable_totp(username):
    """Disable 2FA for a user."""
    conn = get_db()
    try:
        conn.execute("UPDATE users SET totp_enabled = 0, totp_secret = NULL WHERE username = ?", (username,))
        conn.commit()
        return True
    finally:
        conn.close()

# Initialize tables on import
init_auth_tables()
