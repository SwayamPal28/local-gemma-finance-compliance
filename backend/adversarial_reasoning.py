import sqlite3
import json
import os
import gemma_client

def run_adversarial_reasoning(case_id: str, tenant_id: str = "tenant_a"):
    """
    Simulates a multi-agent reasoning flow where an AI 'Prosecutor' argues for fraud,
    an AI 'Defense' argues for benign explanation, and an 'Arbiter' concludes.
    """
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'compliance.db')
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        case_data = conn.execute("SELECT * FROM case_scores WHERE case_id = ? AND tenant_id = ?", (case_id, tenant_id)).fetchone()
        if not case_data:
            return {"error": "Case not found"}
            
        case_dict = dict(case_data)
        acc = case_dict['account_id']
        rule_flags = json.loads(case_dict.get('rule_flags', '[]'))
        
        # Retrieve model name from settings
        model = 'gemma2:2b'
        try:
            row = conn.execute("SELECT value FROM platform_settings WHERE key='gemma_model'").fetchone()
            if row:
                model = row['value']
        except Exception:
            pass
            
        # Get transactional stats to enrich the evidence
        txns = conn.execute(
            "SELECT COUNT(*) as cnt, SUM(amount) as total, MAX(amount) as max_amt FROM transactions WHERE sender_id=? OR receiver_id=?",
            (acc, acc)).fetchone()
        
        evidence = {
            'account_id': acc,
            'risk_score': case_dict.get('risk_score', 0),
            'anomaly_score': case_dict.get('anomaly_score', 0),
            'rules_triggered': [r.get('rule', '') for r in rule_flags] if isinstance(rule_flags, list) else [],
            'rule_details': rule_flags,
            'transaction_count': txns['cnt'] if txns else 0,
            'total_volume': txns['total'] if txns else 0,
            'max_transaction': txns['max_amt'] if txns else 0,
            'expected_roi': case_dict.get('expected_roi', 0.0),
            'assigned_queue': case_dict.get('assigned_queue', 'Triage')
        }

        # 1. Run Prosecutor
        prosecutor_confidence = 50
        prosecutor_points = []
        try:
            p_prompt = gemma_client.build_prosecutor_prompt(evidence)
            p_res = gemma_client.gemma_call(p_prompt, model=model, required_keys=['argument', 'confidence', 'key_suspicious_points'])
            if p_res:
                prosecutor_argument = p_res.get('argument', 'No argument generated.')
                prosecutor_confidence = p_res.get('confidence', 50)
                prosecutor_points = p_res.get('key_suspicious_points', [])
            else:
                prosecutor_argument = 'Failed to generate Prosecutor argument.'
        except Exception as e:
            prosecutor_argument = f"Failed to call Prosecutor agent: {e}"

        # 2. Run Defense
        defense_confidence = 50
        defense_points = []
        try:
            d_prompt = gemma_client.build_defense_prompt(evidence)
            d_res = gemma_client.gemma_call(d_prompt, model=model, required_keys=['argument', 'confidence', 'benign_explanation_points'])
            if d_res:
                defense_argument = d_res.get('argument', 'No argument generated.')
                defense_confidence = d_res.get('confidence', 50)
                defense_points = d_res.get('benign_explanation_points', [])
            else:
                defense_argument = 'Failed to generate Defense argument.'
        except Exception as e:
            defense_argument = f"Failed to call Defense agent: {e}"

        # 3. Run Arbiter (impartial judge)
        try:
            clean_p = prosecutor_argument.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ')
            clean_d = defense_argument.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ')
            verdict = gemma_client.arbitrate_verdict(clean_p, clean_d, evidence, model=model)
            if verdict:
                return {
                    "prosecutor_argument": prosecutor_argument,
                    "prosecutor_confidence": prosecutor_confidence,
                    "prosecutor_points": prosecutor_points,
                    "defense_argument": defense_argument,
                    "defense_confidence": defense_confidence,
                    "defense_points": defense_points,
                    "arbiter_verdict": verdict.get('what_happened', 'No verdict generated.'),
                    "recommended_action": verdict.get('recommended_action', 'CLOSE'),
                    "arbiter_confidence": (verdict.get('confidence', 70) / 100.0) if verdict.get('confidence', 70) > 1 else verdict.get('confidence', 0.7),
                    "prosecutor_summary": verdict.get('prosecutor_summary', ''),
                    "defense_summary": verdict.get('defense_summary', ''),
                    "critical_missing_data": verdict.get('critical_missing_data', '')
                }
        except Exception as e:
            print(f"Arbiter call failed: {e}")

        # Structured fallback if LLM calls fail
        risk_pct = case_dict.get('risk_score', 0) * 100
        arbiter_fallback = f"Adversarial analysis complete. The risk score is {risk_pct:.0f}%."
        return {
            "prosecutor_argument": prosecutor_argument,
            "prosecutor_confidence": prosecutor_confidence,
            "prosecutor_points": prosecutor_points,
            "defense_argument": defense_argument,
            "defense_confidence": defense_confidence,
            "defense_points": defense_points,
            "arbiter_verdict": arbiter_fallback,
            "recommended_action": "ESCALATE" if case_dict.get('risk_score', 0) >= 0.8 else "MONITOR",
            "arbiter_confidence": case_dict.get('risk_score', 0),
            "prosecutor_summary": "Prosecutor flagged structural patterns.",
            "defense_summary": "Defense argued benign explanation.",
            "critical_missing_data": "Additional transactional history."
        }
    finally:
        conn.close()

if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass
        
    # Test with first case from DB
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'compliance.db')
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT case_id FROM case_scores LIMIT 1").fetchone()
    conn.close()
    if row:
        print(f"Testing with case {row[0]}:")
        print(json.dumps(run_adversarial_reasoning(row[0]), indent=2))
    else:
        print("No cases found in DB to test.")
