import sqlite3
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import datetime

DB_PATH = 'compliance.db'

def init_federated_tables():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS federated_models (
            tenant_id TEXT PRIMARY KEY,
            total_amount_mean REAL,
            total_amount_var REAL,
            avg_amount_mean REAL,
            avg_amount_var REAL,
            tx_count_mean REAL,
            tx_count_var REAL,
            anomaly_threshold REAL,
            last_updated TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS global_intelligence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            epsilon REAL,
            total_amount_mean REAL,
            total_amount_var REAL,
            avg_amount_mean REAL,
            avg_amount_var REAL,
            tx_count_mean REAL,
            tx_count_var REAL,
            anomaly_threshold REAL,
            tenants_participated INTEGER,
            last_updated TEXT
        )
    """)
    conn.commit()
    conn.close()

def apply_differential_privacy(value, epsilon=1.0, sensitivity=1.0):
    if epsilon <= 0:
        return value
    scale = sensitivity / epsilon
    noise = np.random.laplace(0, scale)
    return value + noise

def train_local_model(tenant_id):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql('SELECT sender_id, amount FROM transactions WHERE tenant_id = ?', conn, params=(tenant_id,))
    if len(df) < 10:
        conn.close()
        return False
        
    features = df.groupby('sender_id').agg(
        total_amount=('amount', 'sum'),
        avg_amount=('amount', 'mean'),
        tx_count=('amount', 'count')
    ).reset_index()
    
    if len(features) < 5:
        conn.close()
        return False
        
    X = features[['total_amount', 'avg_amount', 'tx_count']].fillna(0)
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    clf = IsolationForest(contamination=0.1, random_state=42)
    clf.fit(X_scaled)
    scores = -clf.decision_function(X_scaled)
    threshold = np.percentile(scores, 90)
    
    stats = {
        'total_amount_mean': float(X['total_amount'].mean()),
        'total_amount_var': float(X['total_amount'].var()),
        'avg_amount_mean': float(X['avg_amount'].mean()),
        'avg_amount_var': float(X['avg_amount'].var()),
        'tx_count_mean': float(X['tx_count'].mean()),
        'tx_count_var': float(X['tx_count'].var()),
        'anomaly_threshold': float(threshold)
    }
    
    conn.execute("""
        INSERT OR REPLACE INTO federated_models 
        (tenant_id, total_amount_mean, total_amount_var, avg_amount_mean, avg_amount_var, 
         tx_count_mean, tx_count_var, anomaly_threshold, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        tenant_id,
        stats['total_amount_mean'], stats['total_amount_var'],
        stats['avg_amount_mean'], stats['avg_amount_var'],
        stats['tx_count_mean'], stats['tx_count_var'],
        stats['anomaly_threshold'],
        datetime.datetime.now().isoformat()
    ))
    
    features['anomaly_score'] = scores
    
    # Use sigmoid function to normalize scores to (0, 1) to provide better spread
    # Adjust scores so the mean is roughly 0 and variance is 1 before sigmoid
    scores_mean = scores.mean()
    scores_std = scores.std() if scores.std() > 0 else 1.0
    features['normalized_score'] = 1 / (1 + np.exp(-((scores - scores_mean) / scores_std)))
        
    records = []
    for _, row in features.iterrows():
        acc = row['sender_id']
        score = row['normalized_score']
        # Only setting anomaly_score to prevent overwriting rule-based risk_score
        records.append((score, f"CASE_{acc}"))
        
    # Only UPDATE existing cases, don't insert random accounts without full data
    conn.executemany("""
    UPDATE case_scores 
    SET anomaly_score = ?
    WHERE case_id = ?
    """, records)
    
    conn.commit()
    conn.close()
    return True

def aggregate_global_model(epsilon=0.5):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql('SELECT * FROM federated_models', conn)
    if len(df) == 0:
        conn.close()
        return False
        
    noisy_stats = {}
    cols_to_aggregate = ['total_amount_mean', 'total_amount_var', 'avg_amount_mean', 'avg_amount_var', 'tx_count_mean', 'tx_count_var', 'anomaly_threshold']
    
    for col in cols_to_aggregate:
        sensitivity = df[col].max() - df[col].min()
        if sensitivity == 0:
            sensitivity = df[col].mean() * 0.1
            
        noisy_values = df[col].apply(lambda x: apply_differential_privacy(x, epsilon, sensitivity))
        noisy_stats[col] = float(noisy_values.mean())
        
    conn.execute("""
        INSERT INTO global_intelligence 
        (epsilon, total_amount_mean, total_amount_var, avg_amount_mean, avg_amount_var, 
         tx_count_mean, tx_count_var, anomaly_threshold, tenants_participated, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        epsilon,
        noisy_stats['total_amount_mean'], noisy_stats['total_amount_var'],
        noisy_stats['avg_amount_mean'], noisy_stats['avg_amount_var'],
        noisy_stats['tx_count_mean'], noisy_stats['tx_count_var'],
        noisy_stats['anomaly_threshold'],
        len(df),
        datetime.datetime.now().isoformat()
    ))
    
    conn.commit()
    conn.close()
    return True

def apply_federated_scoring():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    global_model = conn.execute('SELECT * FROM global_intelligence ORDER BY id DESC LIMIT 1').fetchone()
    if not global_model:
        conn.close()
        return None
        
    cases = conn.execute('SELECT case_id, anomaly_score, tenant_id FROM case_scores').fetchall()
    updates = []
    
    for case in cases:
        local_tenant = case['tenant_id']
        local_model = conn.execute('SELECT anomaly_threshold FROM federated_models WHERE tenant_id = ?', (local_tenant,)).fetchone()
        
        if not local_model:
            continue
            
        local_thresh = local_model['anomaly_threshold']
        global_thresh = global_model['anomaly_threshold']
        
        if global_thresh > local_thresh and local_thresh > 0:
            adjustment_factor = local_thresh / global_thresh
            new_score = case['anomaly_score'] * adjustment_factor
            updates.append((min(new_score, 1.0), case['case_id']))
            
    if updates:
        conn.executemany('UPDATE case_scores SET anomaly_score = ? WHERE case_id = ?', updates)
        
    conn.commit()
    conn.close()
    return True

def get_federated_status():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    latest_global = conn.execute('SELECT * FROM global_intelligence ORDER BY id DESC LIMIT 1').fetchone()
    tenants = conn.execute('SELECT COUNT(*) as count FROM federated_models').fetchone()['count']
    conn.close()
    
    status = 'active' if latest_global else 'uninitialized'
    return {
        'status': status,
        'participating_tenants': tenants,
        'global_threshold': latest_global['anomaly_threshold'] if latest_global else None,
        'last_updated': latest_global['last_updated'] if latest_global else None
    }
