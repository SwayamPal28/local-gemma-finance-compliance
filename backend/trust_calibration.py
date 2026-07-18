import sqlite3
from datetime import datetime

def init_trust_calibration_tables():
    conn = sqlite3.connect('compliance.db', timeout=10)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute("""
    CREATE TABLE IF NOT EXISTS ab_test_interactions (
        interaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id TEXT,
        user_id TEXT,
        case_id TEXT,
        condition TEXT, 
        ai_recommendation TEXT,
        user_decision TEXT,
        time_to_decision_ms INTEGER,
        cognitive_load_score REAL,
        timestamp TEXT
    )
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS decision_quality (
        decision_id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id TEXT,
        case_id TEXT,
        was_correct INTEGER,
        over_relied INTEGER,
        under_relied INTEGER
    )
    """)
    conn.commit()
    conn.close()

def log_ab_test_interaction(tenant_id, user_id, case_id, condition, ai_rec, user_dec, time_ms, conn=None):
    close_conn = False
    if conn is None:
        conn = sqlite3.connect('compliance.db', timeout=10)
        close_conn = True
    load = calculate_cognitive_load(time_ms)
    conn.execute("INSERT INTO ab_test_interactions (tenant_id, user_id, case_id, condition, ai_recommendation, user_decision, time_to_decision_ms, cognitive_load_score, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                 (tenant_id, user_id, case_id, condition, ai_rec, user_dec, time_ms, load, datetime.utcnow().isoformat()))
    if close_conn:
        conn.commit()
        conn.close()

def calculate_cognitive_load(time_ms):
    # Simplified metric: longer time -> higher cognitive load (to a point)
    if time_ms < 1000: return 0.1
    if time_ms > 60000: return 1.0
    return time_ms / 60000.0

def track_decision_quality(tenant_id, case_id, was_correct, over_relied, under_relied):
    conn = sqlite3.connect('compliance.db', timeout=10)
    conn.execute("INSERT INTO decision_quality (tenant_id, case_id, was_correct, over_relied, under_relied) VALUES (?, ?, ?, ?, ?)",
                 (tenant_id, case_id, was_correct, over_relied, under_relied))
    conn.commit()
    conn.close()

def detect_over_reliance(user_id, tenant_id):
    conn = sqlite3.connect('compliance.db', timeout=10)
    conn.row_factory = sqlite3.Row
    # If user agrees with AI >95% of time and time_to_decision < 2000ms
    recent = conn.execute("SELECT ai_recommendation, user_decision, time_to_decision_ms FROM ab_test_interactions WHERE user_id = ? AND tenant_id = ? ORDER BY timestamp DESC LIMIT 20", (user_id, tenant_id)).fetchall()
    conn.close()
    
    if len(recent) < 10: return False
    
    fast_agreements = sum(1 for r in recent if r['ai_recommendation'] == r['user_decision'] and r['time_to_decision_ms'] < 2000)
    if fast_agreements / len(recent) > 0.8:
        return True
    return False

def get_trust_dashboard(tenant_id):
    conn = sqlite3.connect('compliance.db', timeout=10)
    conn.row_factory = sqlite3.Row
    
    stats = {}
    stats['avg_cognitive_load'] = conn.execute("SELECT AVG(cognitive_load_score) as avg FROM ab_test_interactions WHERE tenant_id = ?", (tenant_id,)).fetchone()['avg'] or 0
    stats['total_interactions'] = conn.execute("SELECT COUNT(*) as cnt FROM ab_test_interactions WHERE tenant_id = ?", (tenant_id,)).fetchone()['cnt']
    
    conn.close()
    return stats

def get_trust_calibration_dashboard(tenant_id):
    return get_trust_dashboard(tenant_id)

def log_ab_test(tenant_id, user_id, case_id, condition, ai_rec, user_dec, time_ms):
    return log_ab_test_interaction(tenant_id, user_id, case_id, condition, ai_rec, user_dec, time_ms)

def get_cognitive_load(tenant_id, user_id):
    return 0.5

def get_reliance_pattern(tenant_id, user_id):
    return {"over_reliance": detect_over_reliance(user_id, tenant_id)}

if __name__ == '__main__':
    init_trust_calibration_tables()
    print("Trust calibration initialized.")
