import sqlite3
conn = sqlite3.connect('compliance.db')
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print([t[0] for t in tables])

# Check gemma_reports schema
try:
    print("gemma_reports:", [c[1] for c in conn.execute('PRAGMA table_info(gemma_reports)').fetchall()])
except:
    print("no gemma_reports")

# Check case_scores schema
print("case_scores:", [c[1] for c in conn.execute('PRAGMA table_info(case_scores)').fetchall()])

# Count accounts
rows = conn.execute('SELECT COUNT(*) FROM case_scores').fetchone()
print(f"Total accounts: {rows[0]}")

# Sample txn
txn = conn.execute('SELECT * FROM transactions LIMIT 1').fetchone()
print(f"Sample txn: {list(txn)}")

# Count txns per account (a few samples)
import json
cases = conn.execute('SELECT account_id, risk_score, rule_flags FROM case_scores LIMIT 5').fetchall()
for c in cases:
    acc = c[0]
    cnt = conn.execute('SELECT COUNT(*) FROM transactions WHERE sender_id=? OR receiver_id=?', (acc, acc)).fetchone()[0]
    rules = json.loads(c[2])
    print(f"  {acc}: risk={c[1]:.3f}, rules={len(rules)}, txns={cnt}")
