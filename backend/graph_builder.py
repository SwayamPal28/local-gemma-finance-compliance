import sqlite3
import json

def build_graph(case_id):
    account_id = case_id.replace('CASE_', '')
    import os
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'compliance.db')
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    
    # Try importing pyvis, fallback if not available
    try:
        from pyvis.network import Network
    except ImportError:
        # Fallback to simple HTML representation if pyvis isn't installed
        html = f"""
        <div style="padding: 20px; color: white; text-align: center;">
            <h3>Graph Visualization Requires 'pyvis'</h3>
            <p>Please run <code>pip install pyvis</code></p>
        </div>
        """
        conn.execute("UPDATE case_scores SET graph_flags = ? WHERE case_id = ?", (html, case_id))
        conn.commit()
        conn.close()
        return html

    net = Network(height="400px", width="100%", bgcolor="#12121a", font_color="white", directed=True)
    
    # Add main account node
    net.add_node(account_id, label=f"Account:\\n{account_id}", color="#ff4757", shape="dot", size=25)
    
    # Get KYC data
    kyc = conn.execute("SELECT name, employer, declared_purpose, declared_income, ocr_confidence, account_type FROM kyc_records WHERE account_id = ?", (account_id,)).fetchone()
    if kyc:
        kyc_title = f"Name: {kyc['name']}\\nPurpose: {kyc['declared_purpose']}\\nIncome: ${kyc['declared_income']:,}\\nOCR Confidence: {kyc['ocr_confidence']*100:.0f}%"
        net.add_node("KYC", label="KYC Record", title=kyc_title, color="#2ed573", shape="box")
        net.add_edge(account_id, "KYC")
        if kyc['employer']:
            net.add_node(kyc['employer'], label=kyc['employer'], color="#ffa502", shape="triangle")
            net.add_edge("KYC", kyc['employer'], label="Employed By")

    # Get Devices / IPs
    sessions = conn.execute("SELECT DISTINCT device_id, ip_address, city FROM sessions WHERE account_id = ?", (account_id,)).fetchall()
    for s in sessions:
        if s['device_id']:
            dev_node_id = s['device_id']
            if dev_node_id not in net.get_nodes():
                net.add_node(dev_node_id, label="Device", title=f"Device ID:\\n{s['device_id']}", color="#e74c3c", shape="hexagon")
                net.add_edge(account_id, dev_node_id, label="Used Device")
        if s['ip_address']:
            ip_node_id = s['ip_address']
            if ip_node_id not in net.get_nodes():
                net.add_node(ip_node_id, label=f"IP: {s['city']}", title=f"Resolved IP ({s['ip_address']})", color="#9b59b6", shape="square")
                net.add_edge(account_id, ip_node_id, label="IP")

    # Get Transactions (Outbound)
    out_txns = conn.execute("SELECT receiver_id, COUNT(*) as count, SUM(amount) as total FROM transactions WHERE sender_id = ? GROUP BY receiver_id LIMIT 15", (account_id,)).fetchall()
    for t in out_txns:
        recv = t['receiver_id']
        if recv not in net.get_nodes():
            # Color self-transfers red
            color = "#ff4757" if recv == account_id else "#70a1ff"
            net.add_node(recv, label=recv, color=color, shape="dot", size=15)
        edge_color = "#ff475744" if recv == account_id else "#ffffff44"
        net.add_edge(account_id, recv, label=f"${t['total']:,.2f}\\n({t['count']} txns)", color=edge_color)

    # Get Transactions (Inbound)
    in_txns = conn.execute("SELECT sender_id, COUNT(*) as count, SUM(amount) as total FROM transactions WHERE receiver_id = ? AND sender_id != ? GROUP BY sender_id LIMIT 15", (account_id, account_id)).fetchall()
    for t in in_txns:
        snd = t['sender_id']
        if snd not in net.get_nodes():
            net.add_node(snd, label=snd, color="#70a1ff", shape="dot", size=15)
        net.add_edge(snd, account_id, label=f"${t['total']:,.2f}\\n({t['count']} txns)", color="#ffffff44")

    # Physics options for stability
    net.set_options(json.dumps({
        "physics": {
            "forceAtlas2Based": {
                "gravitationalConstant": -50,
                "centralGravity": 0.01,
                "springLength": 100
            },
            "solver": "forceAtlas2Based",
            "stabilization": {"iterations": 50}
        }
    }))
    
    html = net.generate_html()
    # Return full HTML document so frontend iframe can load pyvis scripts
        
    conn.execute("UPDATE case_scores SET graph_flags = ? WHERE case_id = ?", (html, case_id))
    conn.commit()
    conn.close()
    return html

if __name__ == '__main__':
    print("Graph builder module updated.")
