import sqlite3
import json
import gemma_client

def ask_compliance_iq(query_text: str, tenant_id: str = "tenant_a"):
    """
    Dynamic NL-to-SQL engine using Google Gemma.
    Translates user query into secure SELECT queries and falls back to keyword matching.
    """
    query_text_lower = query_text.lower()
    
    # 1. Retrieve model name from settings
    model = 'gemma2:2b'
    conn = sqlite3.connect('compliance.db', timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute("SELECT value FROM platform_settings WHERE key='gemma_model'").fetchone()
        if row:
            model = row['value']
    except Exception:
        pass
    finally:
        conn.close()

    # 2. Build the LLM prompt
    schema_prompt = (
        f"You are a secure financial investigator assistant. Translate the following user question into a single, valid, read-only SQLite SELECT statement.\n\n"
        f"Database Schema:\n"
        f"- Table: case_scores\n"
        f"  Columns: case_id (TEXT), tenant_id (TEXT), account_id (TEXT), risk_score (REAL), anomaly_score (REAL), status (TEXT), expected_roi (REAL), assigned_queue (TEXT)\n"
        f"- Table: transactions\n"
        f"  Columns: txn_id (TEXT), tenant_id (TEXT), sender_id (TEXT), receiver_id (TEXT), amount (REAL), timestamp (TEXT), type (TEXT), label (INTEGER)\n"
        f"- Table: sessions\n"
        f"  Columns: session_id (TEXT), tenant_id (TEXT), account_id (TEXT), txn_id (TEXT), device_id (TEXT), ip_address (TEXT), city (TEXT), is_vpn_or_proxy (INTEGER), country (TEXT)\n"
        f"- Table: kyc_records\n"
        f"  Columns: account_id (TEXT), name (TEXT), employer (TEXT), declared_purpose (TEXT), declared_income (REAL), account_type (TEXT)\n"
        f"- Table: audit_log\n"
        f"  Columns: log_id (TEXT), tenant_id (TEXT), case_id (TEXT), event_time (TEXT), reviewer_action (TEXT), notes (TEXT), reviewer_id (TEXT)\n\n"
        f"Rules:\n"
        f"1. Generate ONLY SELECT statements. No UPDATE, DELETE, INSERT, DROP or ALTER.\n"
        f"2. Always append a WHERE clause filtering by tenant_id = '{tenant_id}' if the table contains it.\n"
        f"3. Always add a LIMIT 10 clause to avoid massive results.\n"
        f"4. Respond STRICTLY in JSON format with keys:\n"
        f"   - 'sql' (The exact SELECT query string)\n"
        f"   - 'message' (A short explanation of what the query finds)\n\n"
        f"Question: \"{query_text}\"\n"
    )

    # 3. Call Gemma
    sql_query = None
    explanation = None
    try:
        res = gemma_client.gemma_call(schema_prompt, model=model, required_keys=['sql', 'message'])
        if res and 'sql' in res:
            sql_query = res['sql'].strip()
            explanation = res.get('message', 'Custom query generated.')
            
            # Basic security check
            sql_lower = sql_query.lower()
            forbidden = ['update', 'delete', 'insert', 'drop', 'alter', 'create', 'replace', 'truncate']
            if any(word in sql_lower for word in forbidden) or not sql_lower.startswith('select'):
                raise ValueError("Security violation: Only SELECT statements allowed.")
    except Exception as e:
        print(f"Gemma NL-to-SQL failed: {e}. Falling back to keywords.")

    # 4. Execute generated SQL or Fall back to keyword matching
    conn = sqlite3.connect('compliance.db', timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        if sql_query:
            try:
                res = conn.execute(sql_query).fetchall()
                return {
                    "sql": sql_query,
                    "results": [dict(r) for r in res],
                    "message": f"🤖 [Gemma Live] {explanation} (Found {len(res)} matching rows)"
                }
            except Exception as sql_err:
                print(f"Generated SQL execution failed: {sql_err}. Using fallback.")

        # Static Keyword Fallback
        if "high risk" in query_text_lower or "high-risk" in query_text_lower:
            sql = "SELECT case_id, risk_score, status FROM case_scores WHERE risk_score > 0.8 AND tenant_id = ? LIMIT 10"
            res = conn.execute(sql, (tenant_id,)).fetchall()
            return {"sql": sql, "results": [dict(r) for r in res], "message": f"Found {len(res)} high risk cases (Keyword Fallback)."}
        
        elif "escalated" in query_text_lower:
            sql = "SELECT case_id, risk_score, status FROM case_scores WHERE status = 'ESCALATED' AND tenant_id = ? LIMIT 10"
            res = conn.execute(sql, (tenant_id,)).fetchall()
            return {"sql": sql, "results": [dict(r) for r in res], "message": f"Found {len(res)} escalated cases (Keyword Fallback)."}

        elif "audit" in query_text_lower or "history" in query_text_lower:
            sql = "SELECT case_id, event_time, reviewer_action FROM audit_log WHERE tenant_id = ? ORDER BY event_time DESC LIMIT 5"
            res = conn.execute(sql, (tenant_id,)).fetchall()
            return {"sql": sql, "results": [dict(r) for r in res], "message": "Recent audit history (Keyword Fallback)."}

        else:
            sql = "SELECT COUNT(*) as total_cases FROM case_scores WHERE tenant_id = ?"
            res = conn.execute(sql, (tenant_id,)).fetchall()
            return {
                "sql": sql,
                "results": [dict(r) for r in res],
                "message": "I understood your query, but only specific keyword mappings are enabled in fallback mode (try 'high risk', 'escalated', 'audit')."
            }
    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()

if __name__ == "__main__":
    import os
    if os.path.exists('../compliance.db'):
        os.chdir('..')
    print("Testing with dynamic query:")
    print(json.dumps(ask_compliance_iq("List cases that are escalated"), indent=2))
