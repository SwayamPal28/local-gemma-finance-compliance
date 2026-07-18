import sqlite3
import random

DB_PATH = 'compliance.db'

def migrate_sessions():
    conn = sqlite3.connect(DB_PATH)
    
    # Check if columns exist
    cursor = conn.execute("PRAGMA table_info(sessions)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'is_new_device' not in columns:
        print("Adding is_new_device to sessions table")
        conn.execute("ALTER TABLE sessions ADD COLUMN is_new_device BOOLEAN DEFAULT 0")
        
    if 'is_vpn_or_proxy' not in columns:
        print("Adding is_vpn_or_proxy to sessions table")
        conn.execute("ALTER TABLE sessions ADD COLUMN is_vpn_or_proxy BOOLEAN DEFAULT 0")
        
    conn.commit()
    
    # Mock data randomly
    print("Mocking VPN and New Device flags...")
    
    # We will randomly assign 5% of sessions as VPN and 10% as new devices
    # For a more deterministic test, we'll assign VPN to a specific device if possible
    # Let's just use random for the whole table for now.
    
    # Fetch all session_ids
    session_ids = [row[0] for row in conn.execute("SELECT session_id FROM sessions").fetchall()]
    
    for sid in session_ids:
        is_vpn = 1 if random.random() < 0.05 else 0
        is_new = 1 if random.random() < 0.10 else 0
        conn.execute("UPDATE sessions SET is_vpn_or_proxy = ?, is_new_device = ? WHERE session_id = ?", (is_vpn, is_new, sid))
        
    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate_sessions()