import sqlite3
import federated_learning

DB_PATH = 'compliance.db'

def run_anomaly_detection(*args, **kwargs):
    run_anomaly_engine()
    return []

def run_anomaly_engine():
    print("Starting anomaly detection and federated learning cycle...")
    
    federated_learning.init_federated_tables()
    
    conn = sqlite3.connect(DB_PATH)
    tenants = [row[0] for row in conn.execute('SELECT DISTINCT tenant_id FROM transactions').fetchall()]
    conn.close()
    
    print(f"Found {len(tenants)} active tenants for local model training.")
    
    for tenant_id in tenants:
        print(f"  Training local model for tenant: {tenant_id}")
        success = federated_learning.train_local_model(tenant_id)
        if success:
            print(f"    -> Local model trained successfully")
        else:
            print(f"    -> Insufficient data for local model")
            
    print("Aggregating local models into global intelligence...")
    success = federated_learning.aggregate_global_model(epsilon=0.5)
    
    if success:
        print("  Global model updated with differential privacy (epsilon=0.5)")
        print("Applying federated insights to local anomaly scores...")
        federated_learning.apply_federated_scoring()
        print("Anomaly detection cycle completed successfully.")
    else:
        print("  Failed to aggregate global model (no local models available)")

if __name__ == '__main__':
    run_anomaly_engine()
