import sqlite3, json
c = sqlite3.connect('compliance.db')
rows = c.execute('SELECT account_id, risk_score, rule_flags FROM case_scores WHERE risk_score >= 0.6 ORDER BY risk_score DESC LIMIT 15').fetchall()
for r in rows:
    rules = [x.get('rule','') for x in json.loads(r[2])]
    print(f'{r[0]}: risk={r[1]:.3f}, rules={rules}')

# Check sessions for VPN
vpn = c.execute('SELECT COUNT(*) FROM sessions WHERE is_vpn_or_proxy = 1').fetchone()
print(f"\nVPN sessions: {vpn[0]}")
mule = c.execute("SELECT device_id, COUNT(DISTINCT account_id) as cnt FROM sessions GROUP BY device_id HAVING cnt > 1").fetchall()
print(f"Shared devices (mule ring): {len(mule)}")
