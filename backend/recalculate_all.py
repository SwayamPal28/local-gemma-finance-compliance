import real_data_setup
import anomaly
import rules
import sqlite3

if __name__ == "__main__":
    print("1. Resetting database with real data setup...")
    real_data_setup.load_data()
    
    print("\n2. Running compliance rules engine (initial pass to create cases)...")
    rules.run_rules_engine()
    
    print("\n3. Running anomaly detection engine (to generate real anomaly scores)...")
    anomaly.run_anomaly_engine()
    
    print("\n4. Running compliance rules engine again (to update risk scores with real anomaly scores)...")
    rules.run_rules_engine()
    
    print("\n5. Clearing cached graph data (will regenerate on demand)...")
    conn = sqlite3.connect('compliance.db')
    conn.execute("UPDATE case_scores SET graph_flags = NULL")
    conn.commit()
    conn.close()
    
    print("\nAll data recalculated successfully!")
