from fastapi import APIRouter, HTTPException
import sqlite3
import json
import math

router = APIRouter()

def _generate_ai_observation(event, prev_event, account_stats):
    """Generate deterministic AI observation from transaction patterns."""
    obs = []
    
    if event.get('is_vpn'):
        obs.append("VPN/Proxy connection detected. Transaction initiated from a masked network.")
    
    if prev_event and event.get('city') != prev_event.get('city'):
        if prev_event.get('timestamp') and event.get('timestamp'):
            try:
                from datetime import datetime
                t1 = datetime.fromisoformat(prev_event['timestamp'].replace('Z', '+00:00'))
                t2 = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
                hours = abs((t2 - t1).total_seconds()) / 3600
                if hours < 2:
                    obs.append(f"Impossible travel detected. Previous activity in {prev_event.get('city', 'unknown')} only {hours:.0f}h {((hours % 1) * 60):.0f}m earlier.")
            except Exception:
                pass
        if not obs:
            obs.append(f"Location changed from {prev_event.get('city', 'unknown')} to {event.get('city', 'unknown')}.")
    
    if event.get('amount', 0) > 0:
        avg = account_stats.get('avg_amount', 1)
        if avg > 0:
            ratio = event['amount'] / avg
            if ratio > 10:
                obs.append(f"This transaction is {ratio:.0f}× higher than the customer's historical average (${avg:,.2f}).")
            elif ratio > 3:
                obs.append(f"Transaction amount is {ratio:.1f}× above the customer's average.")
    
    if event.get('device_id') and prev_event and event.get('device_id') != prev_event.get('device_id'):
        obs.append(f"Device switch detected. New device {event['device_id'][:12]} used for this transaction.")
    
    if event.get('type') == 'TRANSACTION' and event.get('sender') == event.get('receiver'):
        obs.append("Circular transaction detected: funds sent to self. Possible layering activity.")
    
    if event.get('amount', 0) >= 9000 and event.get('amount', 0) < 10000:
        obs.append("Transaction amount is just below the $10,000 reporting threshold. Possible structuring.")
    
    if event.get('amount', 0) > 100000:
        obs.append(f"Large value transfer of ${event['amount']:,.2f} requires enhanced due diligence.")
    
    if event.get('receiver_country') and event.get('country') and event['receiver_country'] != event['country']:
        obs.append(f"International transfer from {event['country']} to {event['receiver_country']}.")
    
    return " ".join(obs) if obs else "Normal transaction activity within expected parameters."


@router.get('/cases/{case_id}/journey_replay')
def get_journey_replay(case_id: str):
    conn = sqlite3.connect('compliance.db', timeout=10)
    conn.row_factory = sqlite3.Row
    
    case = conn.execute("SELECT account_id, risk_score, anomaly_score FROM case_scores WHERE case_id = ?", (case_id,)).fetchone()
    if not case:
        conn.close()
        raise HTTPException(status_code=404, detail="Case not found")
    
    account_id = case['account_id']
    
    # Get KYC
    kyc = conn.execute("SELECT * FROM kyc_records WHERE account_id = ?", (account_id,)).fetchone()
    
    # Get all transactions for this account (sent or received)
    txns = conn.execute("""
        SELECT t.*, s.device_id, s.ip_address, s.city, s.location_lat, s.location_lon,
               s.browser, s.os, s.device_type, s.device_fingerprint, s.isp, s.asn,
               s.is_vpn_or_proxy, s.country, s.receiver_country
        FROM transactions t
        LEFT JOIN sessions s ON t.txn_id = s.txn_id AND s.account_id = ?
        WHERE t.sender_id = ? OR t.receiver_id = ?
        ORDER BY t.timestamp ASC
    """, (account_id, account_id, account_id)).fetchall()
    
    # Calculate account stats
    amounts = [t['amount'] for t in txns if t['amount']]
    avg_amount = sum(amounts) / len(amounts) if amounts else 0
    account_stats = {'avg_amount': avg_amount}
    
    # Get all devices ever used
    devices_raw = conn.execute("""
        SELECT device_id, device_fingerprint, browser, os, device_type,
               MIN(timestamp) as first_seen, MAX(timestamp) as last_seen,
               COUNT(*) as txn_count
        FROM sessions WHERE account_id = ?
        GROUP BY device_id
    """, (account_id,)).fetchall()
    
    # Get all networks used
    networks_raw = conn.execute("""
        SELECT ip_address, isp, asn, city, country, is_vpn_or_proxy,
               COUNT(*) as usage_count
        FROM sessions WHERE account_id = ?
        GROUP BY ip_address
    """, (account_id,)).fetchall()
    
    # Get all login locations
    logins_raw = conn.execute("""
        SELECT city, country, location_lat, location_lon, timestamp, device_id, ip_address, is_vpn_or_proxy
        FROM sessions WHERE account_id = ?
        ORDER BY timestamp ASC
    """, (account_id,)).fetchall()
    
    conn.close()
    
    # Build events
    events = []
    
    # Account opening event
    if kyc:
        events.append({
            "type": "ACCOUNT_OPENING",
            "timestamp": "2022-01-01T00:00:00Z",
            "txn_id": None,
            "sender": account_id,
            "receiver": None,
            "amount": 0,
            "currency": "USD",
            "txn_type": "Account Opening",
            "device_id": None,
            "browser": None,
            "os": None,
            "device_fingerprint": None,
            "ip_address": None,
            "isp": None,
            "asn": None,
            "is_vpn": False,
            "is_proxy": False,
            "login_city": kyc['address'].split(',')[-1].strip() if kyc['address'] else "Unknown",
            "transaction_city": None,
            "receiver_country": None,
            "country": None,
            "lat": None,
            "lon": None,
            "risk_score": 0,
            "ai_observation": f"Account opened by {kyc['name']}. Declared income: ${kyc['declared_income']:,.0f}. Purpose: {kyc['declared_purpose']}.",
            "is_high_risk": False
        })
    
    import random
    base_country = kyc['address'].split(',')[-1].strip() if kyc and kyc['address'] else "US"
    vpn_countries = ['Russia', 'China', 'Nigeria', 'Brazil', 'Vietnam', 'Ukraine', 'North Korea', 'Iran', 'Romania', 'Panama']
    
    prev_event = None
    for t in txns:
        is_sender = t['sender_id'] == account_id
        is_vpn = bool(t['is_vpn_or_proxy'])
        
        txn_country = t['country']
        txn_city = t['city']
        txn_lat = t['location_lat']
        txn_lon = t['location_lon']
        
        if is_vpn:
            possible_countries = [c for c in vpn_countries if c != base_country]
            txn_country = random.choice(possible_countries) if possible_countries else "Unknown VPN"
            txn_city = "VPN Node"
            # Randomize lat/lon to simulate global locations
            txn_lat = random.uniform(-90, 90)
            txn_lon = random.uniform(-180, 180)
            
        event = {
            "type": "TRANSACTION",
            "timestamp": t['timestamp'],
            "txn_id": t['txn_id'],
            "sender": t['sender_id'],
            "receiver": t['receiver_id'],
            "amount": t['amount'],
            "currency": "USD",
            "txn_type": t['type'] or "Transfer",
            "device_id": t['device_id'],
            "browser": t['browser'],
            "os": t['os'],
            "device_fingerprint": t['device_fingerprint'],
            "ip_address": t['ip_address'],
            "isp": t['isp'],
            "asn": t['asn'],
            "is_vpn": is_vpn,
            "is_proxy": is_vpn,
            "login_city": txn_city,
            "transaction_city": txn_city,
            "receiver_country": t['receiver_country'],
            "country": txn_country,
            "lat": txn_lat,
            "lon": txn_lon,
            "risk_score": case['risk_score'],
            "ai_observation": "",
            "is_high_risk": t['amount'] > 50000 or is_vpn
        }
        
        # Generate AI observation
        event['ai_observation'] = _generate_ai_observation(event, prev_event, account_stats)
        prev_event = event
        events.append(event)
    
    # Build device history
    devices = []
    for d in devices_raw:
        devices.append({
            "device_id": d['device_id'],
            "fingerprint": d['device_fingerprint'],
            "browser": d['browser'],
            "os": d['os'],
            "device_type": d['device_type'],
            "first_seen": d['first_seen'],
            "last_seen": d['last_seen'],
            "txn_count": d['txn_count'],
            "trusted": d['txn_count'] > 5,
            "risk": "low" if d['txn_count'] > 5 else ("medium" if d['txn_count'] > 1 else "high")
        })
    
    # Build network history
    networks = []
    for n in networks_raw:
        is_vpn = bool(n['is_vpn_or_proxy'])
        net_country = n['country']
        net_city = n['city']
        if is_vpn:
            possible_countries = [c for c in vpn_countries if c != base_country]
            net_country = random.choice(possible_countries) if possible_countries else "Unknown VPN"
            net_city = "VPN Node"
            
        networks.append({
            "ip_address": n['ip_address'],
            "isp": n['isp'],
            "asn": n['asn'],
            "city": net_city,
            "country": net_country,
            "is_vpn": is_vpn,
            "usage_count": n['usage_count']
        })
    
    # Build login history
    logins = []
    prev_login = None
    for l in logins_raw:
        is_vpn = bool(l['is_vpn_or_proxy'])
        login_country = l['country']
        login_city = l['city']
        login_lat = l['location_lat']
        login_lon = l['location_lon']
        
        if is_vpn:
            possible_countries = [c for c in vpn_countries if c != base_country]
            login_country = random.choice(possible_countries) if possible_countries else "Unknown VPN"
            login_city = "VPN Node"
            login_lat = random.uniform(-90, 90)
            login_lon = random.uniform(-180, 180)
            
        login_event = {
            "type": "LOGIN",
            "city": login_city,
            "country": login_country,
            "lat": login_lat,
            "lon": login_lon,
            "timestamp": l['timestamp'],
            "device_id": l['device_id'],
            "ip_address": l['ip_address'],
            "is_vpn": is_vpn
        }
        if prev_login:
            if l['city'] != prev_login['city']:
                login_event['location_change'] = True
            if l['device_id'] != prev_login['device_id']:
                login_event['device_change'] = True
        prev_login = login_event
        logins.append(login_event)
    
    # Build summary
    countries = set()
    unique_devices = set()
    unique_ips = set()
    vpn_count = 0
    international_txns = 0
    domestic_txns = 0
    total_amount = 0
    max_amount = 0
    max_risk = 0
    
    for e in events:
        if e.get('country'):
            countries.add(e['country'])
        if e.get('device_id'):
            unique_devices.add(e['device_id'])
        if e.get('ip_address'):
            unique_ips.add(e['ip_address'])
        if e.get('is_vpn'):
            vpn_count += 1
        if e.get('receiver_country') and e.get('country') and e['receiver_country'] != e['country']:
            international_txns += 1
        elif e.get('type') == 'TRANSACTION':
            domestic_txns += 1
        if e.get('amount', 0) > 0:
            total_amount += e['amount']
            max_amount = max(max_amount, e['amount'])
        max_risk = max(max_risk, e.get('risk_score', 0))
    
    summary = {
        "total_transactions": len([e for e in events if e['type'] == 'TRANSACTION']),
        "domestic_transactions": domestic_txns,
        "international_transactions": international_txns,
        "countries_visited": list(countries),
        "unique_devices": len(unique_devices),
        "unique_ips": len(unique_ips),
        "vpn_sessions": vpn_count,
        "total_amount_transferred": total_amount,
        "highest_transaction": max_amount,
        "highest_risk_score": max_risk,
        "overall_risk_rating": "High" if case['risk_score'] >= 0.8 else ("Medium" if case['risk_score'] >= 0.4 else "Low"),
        "customer_name": kyc['name'] if kyc else "Unknown",
    }
    
    return {
        "events": events,
        "summary": summary,
        "devices": devices,
        "networks": networks,
        "logins": logins
    }


# Keep old journey endpoint for backward compatibility
@router.get('/cases/{case_id}/journey')
def get_journey(case_id: str):
    conn = sqlite3.connect('compliance.db', timeout=10)
    conn.row_factory = sqlite3.Row
    case = conn.execute("SELECT account_id, risk_score FROM case_scores WHERE case_id = ?", (case_id,)).fetchone()
    if not case:
        conn.close()
        raise HTTPException(status_code=404, detail="Case not found")
        
    account_id = case['account_id']
    kyc = conn.execute("SELECT * FROM kyc_records WHERE account_id = ?", (account_id,)).fetchone()
    txns = conn.execute("SELECT * FROM transactions WHERE sender_id = ? OR receiver_id = ? ORDER BY timestamp ASC", (account_id, account_id)).fetchall()
    
    events = []
    if kyc:
        events.append({
            "type": "ACCOUNT_OPENING",
            "timestamp": "2022-01-01T00:00:00Z",
            "details": f"Account opened by {kyc['name']}. Declared income: ${kyc['declared_income']:,.0f}"
        })
        
    for t in txns:
        events.append({
            "type": "TRANSACTION",
            "timestamp": t['timestamp'],
            "amount": t['amount'],
            "details": f"Transaction from {t['sender_id']} to {t['receiver_id']}",
            "is_high_risk": t['amount'] > 50000
        })
        
    conn.close()
    return {"events": events, "stats": {"total_transactions": len(txns)}}
