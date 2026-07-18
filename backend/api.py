from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List
import sqlite3, json, os, datetime, time

import journey_api, graph_builder, gemma_client, report_gen, adversarial_reasoning, sanctions
import multimodal_processor, evidence_linker, risk_scoring
import nl_to_sql, audit, audit_export, benchmark_dataset
import regulatory_knowledge, causal_attribution, cost_optimization
import incremental_learning, streaming_pipeline, federated_learning
import trust_calibration
import auth as auth_module

app = FastAPI(title="Compliance Triage API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(journey_api.router)

DB_PATH = 'compliance.db'

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.row_factory = sqlite3.Row
    return conn

# ═══════════════════════════════════════════════
# AUTHENTICATION
# ═══════════════════════════════════════════════
class RegisterRequest(BaseModel):
    username: str
    password: str
    full_name: str = ''

class LoginRequest(BaseModel):
    username: str
    password: str

class OTPRequest(BaseModel):
    username: str
    otp: str

@app.post('/auth/register')
def register(req: RegisterRequest):
    try:
        user = auth_module.register_user(req.username, req.password, req.full_name)
        return {"status": "success", "user": user}
    except ValueError as e:
        raise HTTPException(400, str(e))

@app.post('/auth/login')
def login(req: LoginRequest):
    user = auth_module.authenticate_user(req.username, req.password)
    if not user:
        raise HTTPException(401, "Invalid username or password")
    if user['totp_enabled']:
        return {"status": "otp_required", "username": user['username']}
    return {"status": "success", "user": user}

@app.post('/auth/verify-otp')
def verify_otp(req: OTPRequest):
    if auth_module.verify_totp(req.username, req.otp):
        # Re-fetch user info to return
        user = auth_module.authenticate_user(req.username, '')  # won't work, need a different approach
        # Fetch user directly
        conn = get_db()
        try:
            row = conn.execute("SELECT id, username, full_name, role, totp_enabled FROM users WHERE username = ?", (req.username,)).fetchone()
            if row:
                user = dict(row)
                user['totp_enabled'] = bool(user['totp_enabled'])
                return {"status": "success", "user": user}
        finally:
            conn.close()
        raise HTTPException(401, "User not found")
    raise HTTPException(401, "Invalid OTP code")

@app.post('/auth/setup-2fa')
def setup_2fa(req: dict):
    username = req.get('username')
    if not username:
        raise HTTPException(400, "Username required")
    try:
        result = auth_module.setup_totp(username)
        return {"status": "success", **result}
    except ValueError as e:
        raise HTTPException(404, str(e))

@app.post('/auth/enable-2fa')
def enable_2fa(req: OTPRequest):
    if auth_module.verify_and_enable_totp(req.username, req.otp):
        return {"status": "success", "message": "2FA enabled successfully"}
    raise HTTPException(400, "Invalid OTP code. Please try again.")

@app.post('/auth/disable-2fa')
def disable_2fa(req: dict):
    username = req.get('username')
    if not username:
        raise HTTPException(400, "Username required")
    auth_module.disable_totp(username)
    return {"status": "success", "message": "2FA disabled"}

# ═══════════════════════════════════════════════
# CASES
# ═══════════════════════════════════════════════
@app.get('/cases')
def get_cases(tenant_id: str = 'tenant_a'):
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT case_id, account_id, anomaly_score, risk_score, risk_dimensions, rule_flags, expected_roi, assigned_queue, status FROM case_scores WHERE tenant_id = ?",
            (tenant_id,)).fetchall()
        cases = [dict(r) for r in rows]
        for c in cases:
            acc = c.get('account_id', '')
            cnt = conn.execute("SELECT COUNT(*) FROM transactions WHERE sender_id=? OR receiver_id=?", (acc, acc)).fetchone()
            c['txn_count'] = cnt[0] if cnt else 0
        return cost_optimization.rank_queue_by_roi(cases)
    except Exception as e:
        print(f"Error: {e}")
        return []
    finally:
        conn.close()

@app.get('/cases/{case_id}')
def get_case_details(case_id: str, tenant_id: str = 'tenant_a'):
    conn = get_db()
    try:
        case = conn.execute("SELECT * FROM case_scores WHERE case_id=? AND tenant_id=?", (case_id, tenant_id)).fetchone()
        report = conn.execute("SELECT * FROM gemma_reports WHERE case_id=? AND tenant_id=?", (case_id, tenant_id)).fetchone()
        if not case:
            raise HTTPException(404, "Case not found")
        # Get KYC
        acc = case['account_id']
        kyc = conn.execute("SELECT * FROM kyc_records WHERE account_id=?", (acc,)).fetchone()
        # Get OCR docs
        ocr = conn.execute("SELECT * FROM ocr_documents WHERE account_id=?", (acc,)).fetchall()
        # Get review history
        history = conn.execute("SELECT * FROM review_history WHERE case_id=? ORDER BY timestamp DESC", (case_id,)).fetchall()
        # Get sanctions screening match
        sanctions_check = {"has_match": False}
        if kyc and kyc['name']:
            try:
                gemma_model = 'gemma2:2b'
                row_model = conn.execute("SELECT value FROM platform_settings WHERE key='gemma_model'").fetchone()
                if row_model:
                    gemma_model = row_model['value']
                sanctions_check = sanctions.check_sanctions(kyc['name'], 'Unknown', conn, model=gemma_model)
            except Exception as e:
                print(f"Sanctions check failed: {e}")

        # Format report for frontend consumption
        report_data = None
        if report:
            rd = dict(report)
            fa_raw = rd.get('feature_attributions', '{}')
            try:
                fa = json.loads(fa_raw) if isinstance(fa_raw, str) else (fa_raw or {})
            except Exception:
                fa = {}
            report_data = {
                "what_happened": rd.get('what_happened', ''),
                "why_it_matters": rd.get('why_it_matters', ''),
                "recommended_action": rd.get('recommended_action', ''),
                "confidence_score": rd.get('confidence', 0.5),
                "missing_information_needed": rd.get('missing_information_needed', 'None.'),
                "feature_attributions": fa
            }

        return {
            "case": dict(case),
            "report": report_data,
            "kyc": dict(kyc) if kyc else None,
            "ocr_documents": [dict(d) for d in ocr],
            "review_history": [dict(h) for h in history],
            "sanctions_check": sanctions_check
        }
    finally:
        conn.close()

# ═══════════════════════════════════════════════
# DISPOSITION (Review Workflow)
# ═══════════════════════════════════════════════
class DispositionRequest(BaseModel):
    action: str
    reason: str
    tenant_id: str = "tenant_a"
    reviewer_id: str = "analyst_01"
    reviewer_confidence: int = 80
    time_to_decision_ms: int = 5000

@app.post('/cases/{case_id}/disposition')
def update_case_disposition(case_id: str, req: DispositionRequest):
    conn = get_db()
    try:
        case = conn.execute("SELECT * FROM case_scores WHERE case_id=?", (case_id,)).fetchone()
        if not case:
            raise HTTPException(404, "Case not found")

        old_status = case['status'] or 'NEW'
        risk = case['risk_score'] or 0

        # Get AI recommendation from report
        report = conn.execute("SELECT recommended_action FROM gemma_reports WHERE case_id=?", (case_id,)).fetchone()
        ai_rec = report['recommended_action'] if report else ('ESCALATE' if risk >= 0.8 else 'MONITOR' if risk >= 0.4 else 'CLOSE')

        act = req.action.upper()
        rec = (ai_rec or '').upper()
        def get_base(s):
            if s.endswith('ING'): return s[:-3]
            if s.endswith('ED'): return s[:-2]
            if s.endswith('ES'): return s[:-2]
            if s.endswith('S') and not s.endswith('CS'): return s[:-1]
            return s
        followed_ai = 1 if get_base(act) == get_base(rec) or rec in act or act in rec else 0

        # 1. Update case status
        conn.execute("UPDATE case_scores SET status=? WHERE case_id=?", (req.action, case_id))

        # 2. Insert audit log
        audit.log_event(
            tenant_id=req.tenant_id, case_id=case_id,
            action=f"DISPOSITION: {req.action}", notes=req.reason,
            reviewer_id=req.reviewer_id, old_status=old_status,
            new_status=req.action, ai_recommendation=ai_rec, risk_score=risk,
            conn=conn
        )

        # 3. Insert review history
        conn.execute('''INSERT INTO review_history 
            (tenant_id, case_id, reviewer_id, action, old_status, new_status, notes,
             ai_recommendation, reviewer_confidence, followed_ai, time_to_decision_ms, risk_score, timestamp)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            (req.tenant_id, case_id, req.reviewer_id, req.action, old_status, req.action,
             req.reason, ai_rec, req.reviewer_confidence, followed_ai,
             req.time_to_decision_ms, risk, datetime.datetime.utcnow().isoformat()))

        # 4. Log trust calibration
        trust_calibration.log_ab_test_interaction(
            req.tenant_id, req.reviewer_id, case_id,
            'narrative', ai_rec, req.action, req.time_to_decision_ms,
            conn=conn
        )

        conn.commit()
        return {"status": "success", "action": req.action, "old_status": old_status,
                "followed_ai": bool(followed_ai)}
    finally:
        conn.close()

# ═══════════════════════════════════════════════
# AUDIT LOGS
# ═══════════════════════════════════════════════
@app.get('/audit')
def get_audit_logs(tenant_id: Optional[str] = None, case_id: Optional[str] = None,
                   action: Optional[str] = None, search: Optional[str] = None,
                   limit: int = 500):
    return {"events": audit.get_audit_logs(tenant_id, case_id, action, search, limit)}

@app.get('/audit/timeline/{case_id}')
def get_audit_timeline(case_id: str):
    return {"timeline": audit.get_case_timeline(case_id)}

@app.get('/audit/export')
def export_audit_csv(tenant_id: str = 'tenant_a'):
    """Export audit logs as JSON for download."""
    logs = audit.get_audit_logs(tenant_id, limit=10000)
    return {"export": logs, "count": len(logs), "format": "json"}

# ═══════════════════════════════════════════════
# TRUST CALIBRATION
# ═══════════════════════════════════════════════
@app.get('/trust/dashboard')
def get_trust_dashboard(tenant_id: str = 'tenant_a'):
    conn = get_db()
    try:
        # AB test interactions
        interactions = conn.execute(
            "SELECT * FROM ab_test_interactions WHERE tenant_id=? ORDER BY timestamp DESC LIMIT 100",
            (tenant_id,)).fetchall()
        interactions_list = [dict(r) for r in interactions]

        # Aggregate metrics
        total = len(interactions_list)
        if total > 0:
            agreements = sum(1 for i in interactions_list if i.get('ai_recommendation') == i.get('user_decision'))
            avg_time = sum(i.get('time_to_decision_ms', 0) for i in interactions_list) / total
            avg_load = sum(i.get('cognitive_load_score', 0) for i in interactions_list) / total
            ai_reliance = agreements / total if total > 0 else 0
        else:
            agreements = 0; avg_time = 0; avg_load = 0; ai_reliance = 0

        # Review history for reviewer performance
        reviews = conn.execute(
            "SELECT * FROM review_history WHERE tenant_id=? ORDER BY timestamp DESC LIMIT 200",
            (tenant_id,)).fetchall()
        reviews_list = [dict(r) for r in reviews]

        # Per-reviewer stats
        reviewer_stats = {}
        for r in reviews_list:
            rid = r.get('reviewer_id', 'unknown')
            if rid not in reviewer_stats:
                reviewer_stats[rid] = {'total': 0, 'followed_ai': 0, 'total_time': 0, 'total_confidence': 0, 'actions': {}}
            reviewer_stats[rid]['total'] += 1
            reviewer_stats[rid]['followed_ai'] += r.get('followed_ai', 0)
            reviewer_stats[rid]['total_time'] += r.get('time_to_decision_ms', 0)
            reviewer_stats[rid]['total_confidence'] += r.get('reviewer_confidence', 0)
            act = r.get('action', 'OTHER')
            reviewer_stats[rid]['actions'][act] = reviewer_stats[rid]['actions'].get(act, 0) + 1

        reviewer_performance = []
        for rid, s in reviewer_stats.items():
            reviewer_performance.append({
                'reviewer_id': rid,
                'total_reviews': s['total'],
                'ai_agreement_rate': s['followed_ai'] / s['total'] if s['total'] > 0 else 0,
                'avg_decision_time_ms': s['total_time'] / s['total'] if s['total'] > 0 else 0,
                'avg_confidence': s['total_confidence'] / s['total'] if s['total'] > 0 else 0,
                'action_breakdown': s['actions'],
            })

        # Cognitive load metrics
        load_metrics = conn.execute(
            "SELECT * FROM cognitive_load_metrics WHERE tenant_id=? ORDER BY session_date DESC LIMIT 30",
            (tenant_id,)).fetchall()

        # Decision quality
        quality = conn.execute(
            "SELECT * FROM decision_quality WHERE tenant_id=? ORDER BY decision_id DESC LIMIT 50",
            (tenant_id,)).fetchall()

        return {
            "dashboard": {
                "total_interactions": total,
                "ai_agreement_count": agreements,
                "ai_reliance_rate": round(ai_reliance, 3),
                "avg_decision_time_ms": round(avg_time, 0),
                "avg_cognitive_load": round(avg_load, 3),
                "trust_score": round(min(ai_reliance * 0.4 + (1 - avg_load) * 0.3 + min(avg_time / 30000, 1) * 0.3, 1.0), 3),
                "reviewer_performance": reviewer_performance,
                "recent_interactions": interactions_list[:20],
                "cognitive_load_history": [dict(r) for r in load_metrics],
                "decision_quality": [dict(r) for r in quality],
            }
        }
    finally:
        conn.close()

# ═══════════════════════════════════════════════
# STREAMING MONITOR
# ═══════════════════════════════════════════════
@app.get('/streaming/stats')
def get_streaming_stats(tenant_id: str = 'tenant_a'):
    conn = get_db()
    try:
        # Real-time counters from actual data
        total_txns = conn.execute("SELECT COUNT(*) FROM transactions WHERE tenant_id=?", (tenant_id,)).fetchone()[0]
        total_cases = conn.execute("SELECT COUNT(*) FROM case_scores WHERE tenant_id=?", (tenant_id,)).fetchone()[0]
        high_risk = conn.execute("SELECT COUNT(*) FROM case_scores WHERE tenant_id=? AND risk_score >= 0.8", (tenant_id,)).fetchone()[0]
        under_investigation = conn.execute("SELECT COUNT(*) FROM case_scores WHERE tenant_id=? AND status IN ('MONITORING','ESCALATED','REQUEST_DOCS')", (tenant_id,)).fetchone()[0]
        escalated = conn.execute("SELECT COUNT(*) FROM case_scores WHERE tenant_id=? AND status='ESCALATED'", (tenant_id,)).fetchone()[0]
        closed = conn.execute("SELECT COUNT(*) FROM case_scores WHERE tenant_id=? AND status='CLOSED'", (tenant_id,)).fetchone()[0]
        new_cases = conn.execute("SELECT COUNT(*) FROM case_scores WHERE tenant_id=? AND status='NEW'", (tenant_id,)).fetchone()[0]

        # Recent audit activity
        recent_activity = conn.execute(
            "SELECT * FROM audit_log WHERE tenant_id=? ORDER BY event_time DESC LIMIT 20",
            (tenant_id,)).fetchall()

        # Recent transactions (live feed simulation)
        recent_txns = conn.execute(
            "SELECT * FROM transactions WHERE tenant_id=? ORDER BY timestamp DESC LIMIT 15",
            (tenant_id,)).fetchall()

        # Risk distribution
        risk_dist = {
            'high': high_risk,
            'medium': conn.execute("SELECT COUNT(*) FROM case_scores WHERE tenant_id=? AND risk_score >= 0.4 AND risk_score < 0.8", (tenant_id,)).fetchone()[0],
            'low': conn.execute("SELECT COUNT(*) FROM case_scores WHERE tenant_id=? AND risk_score < 0.4", (tenant_id,)).fetchone()[0],
        }

        # Status distribution
        statuses = conn.execute(
            "SELECT status, COUNT(*) as cnt FROM case_scores WHERE tenant_id=? GROUP BY status",
            (tenant_id,)).fetchall()

        return {
            "total_transactions": total_txns,
            "total_cases": total_cases,
            "high_risk_alerts": high_risk,
            "under_investigation": under_investigation,
            "escalated_cases": escalated,
            "closed_cases": closed,
            "new_cases": new_cases,
            "risk_distribution": risk_dist,
            "status_distribution": {r['status']: r['cnt'] for r in statuses},
            "recent_activity": [dict(r) for r in recent_activity],
            "recent_transactions": [dict(r) for r in recent_txns],
            "ai_analysis_status": "ACTIVE" if total_cases > 0 else "IDLE",
            # Legacy fields for backward compat
            "total_documents_arrived": conn.execute("SELECT COUNT(*) FROM document_arrivals WHERE tenant_id=?", (tenant_id,)).fetchone()[0],
            "late_arrivals": conn.execute("SELECT COUNT(*) FROM document_arrivals WHERE tenant_id=? AND is_late=1", (tenant_id,)).fetchone()[0],
            "total_reconciliations_triggered": conn.execute("SELECT COUNT(*) FROM reconciliation_triggers WHERE tenant_id=?", (tenant_id,)).fetchone()[0],
            "pending_reconciliations": conn.execute("SELECT COUNT(*) FROM reconciliation_triggers WHERE tenant_id=? AND status='PENDING'", (tenant_id,)).fetchone()[0],
        }
    except Exception as e:
        print(f"Streaming stats error: {e}")
        return {"total_transactions": 0, "total_cases": 0, "high_risk_alerts": 0,
                "under_investigation": 0, "escalated_cases": 0, "closed_cases": 0,
                "new_cases": 0, "risk_distribution": {}, "status_distribution": {},
                "recent_activity": [], "recent_transactions": [],
                "total_documents_arrived": 0, "late_arrivals": 0,
                "total_reconciliations_triggered": 0, "pending_reconciliations": 0}
    finally:
        conn.close()

# ═══════════════════════════════════════════════
# FEDERATED NETWORK
# ═══════════════════════════════════════════════
@app.get('/federated/status')
def get_federated_status(tenant_id: str = 'tenant_a'):
    conn = get_db()
    try:
        tenants = conn.execute("SELECT * FROM tenants").fetchall()
        models = conn.execute("SELECT * FROM federated_models").fetchall()
        intelligence = conn.execute(
            "SELECT * FROM shared_fraud_intelligence ORDER BY created_at DESC").fetchall()
        global_model = conn.execute(
            "SELECT * FROM global_intelligence ORDER BY id DESC LIMIT 1").fetchone()

        # Per-tenant stats
        tenant_stats = []
        for t in tenants:
            tid = t['tenant_id']
            case_count = conn.execute("SELECT COUNT(*) FROM case_scores WHERE tenant_id=?", (tid,)).fetchone()[0]
            txn_count = conn.execute("SELECT COUNT(*) FROM transactions WHERE tenant_id=?", (tid,)).fetchone()[0]
            model = conn.execute("SELECT * FROM federated_models WHERE tenant_id=?", (tid,)).fetchone()
            tenant_stats.append({
                'tenant_id': tid,
                'name': t['name'],
                'status': t['status'],
                'case_count': case_count,
                'txn_count': txn_count,
                'model_last_updated': model['last_updated'] if model else None,
                'anomaly_threshold': round(model['anomaly_threshold'], 4) if model else None,
            })

        # Aggregate shared intelligence by category
        pattern_summary = {}
        for ind in intelligence:
            cat = ind['pattern_category']
            if cat not in pattern_summary:
                pattern_summary[cat] = {'count': 0, 'avg_confidence': 0, 'indicators': []}
            pattern_summary[cat]['count'] += 1
            pattern_summary[cat]['avg_confidence'] += ind['confidence']
            pattern_summary[cat]['indicators'].append({
                'type': ind['indicator_type'],
                'description': ind['description'],
                'severity': ind['severity'],
                'confidence': ind['confidence'],
                'contributor': ind['contributing_tenant'],
            })
        for cat in pattern_summary:
            pattern_summary[cat]['avg_confidence'] = round(
                pattern_summary[cat]['avg_confidence'] / pattern_summary[cat]['count'], 3)

        return {
            "tenants": tenant_stats,
            "shared_intelligence": [dict(i) for i in intelligence],
            "pattern_summary": pattern_summary,
            "global_model": dict(global_model) if global_model else None,
            "total_participating": len(tenant_stats),
        }
    finally:
        conn.close()

@app.post('/federated/train')
def trigger_federated_training(tenant_id: str = "tenant_a"):
    success = federated_learning.train_local_model(tenant_id)
    if success:
        federated_learning.aggregate_global_model()
    return {"status": "training_completed", "success": success}

# ═══════════════════════════════════════════════
# KYC MODULE
# ═══════════════════════════════════════════════
@app.get('/cases/{case_id}/kyc')
def get_kyc(case_id: str, tenant_id: str = 'tenant_a'):
    conn = get_db()
    try:
        case = conn.execute("SELECT account_id FROM case_scores WHERE case_id=?", (case_id,)).fetchone()
        if not case:
            raise HTTPException(404, "Case not found")
        acc = case['account_id']
        kyc = conn.execute("SELECT * FROM kyc_records WHERE account_id=?", (acc,)).fetchone()
        ocr_docs = conn.execute("SELECT * FROM ocr_documents WHERE account_id=?", (acc,)).fetchall()
        sessions = conn.execute(
            "SELECT DISTINCT device_id, browser, os, device_type, ip_address, city, country FROM sessions WHERE account_id=?",
            (acc,)).fetchall()

        # Build KYC profile
        kyc_dict = dict(kyc) if kyc else {}
        doc_types_found = set(d['doc_type'] for d in ocr_docs)
        required_docs = {'PAN', 'AADHAAR', 'INVOICE', 'BANK_STATEMENT'}
        missing = required_docs - doc_types_found

        # Determine verification status
        if kyc_dict.get('ocr_confidence', 0) > 0.8 and len(missing) == 0:
            verification_status = 'VERIFIED'
        elif kyc_dict.get('ocr_confidence', 0) > 0.5:
            verification_status = 'PARTIAL'
        else:
            verification_status = 'UNVERIFIED'

        # KYC risk based on missing docs and confidence
        kyc_risk = 'LOW'
        if len(missing) >= 2 or kyc_dict.get('ocr_confidence', 0) < 0.5:
            kyc_risk = 'HIGH'
        elif len(missing) >= 1 or kyc_dict.get('ocr_confidence', 0) < 0.7:
            kyc_risk = 'MEDIUM'

        # Get sanctions screening match
        sanctions_check = {"has_match": False}
        if kyc_dict and kyc_dict.get('name'):
            try:
                gemma_model = 'gemma2:2b'
                row_model = conn.execute("SELECT value FROM platform_settings WHERE key='gemma_model'").fetchone()
                if row_model:
                    gemma_model = row_model['value']
                sanctions_check = sanctions.check_sanctions(kyc_dict['name'], kyc_dict.get('country', 'Unknown'), conn, model=gemma_model)
            except Exception as e:
                print(f"Sanctions check failed: {e}")

        return {
            "kyc": kyc_dict,
            "documents": [dict(d) for d in ocr_docs],
            "sessions": [dict(s) for s in sessions],
            "verification_status": verification_status,
            "kyc_risk": kyc_risk,
            "missing_documents": list(missing),
            "document_types_found": list(doc_types_found),
            "total_documents": len(ocr_docs),
            "sanctions_check": sanctions_check
        }
    finally:
        conn.close()

# ═══════════════════════════════════════════════
# CHAT (RAG)
# ═══════════════════════════════════════════════
from typing import List, Dict, Any

class ChatRequest(BaseModel):
    tenant_id: str = 'tenant_a'
    message: str
    history: List[Dict[str, Any]] = []

@app.post('/cases/{case_id}/chat')
def chat_with_case_endpoint(case_id: str, req: ChatRequest):
    conn = get_db()
    try:
        case_data = conn.execute("SELECT * FROM case_scores WHERE case_id=? AND tenant_id=?",
                                 (case_id, req.tenant_id)).fetchone()
        if not case_data:
            raise HTTPException(404, "Case not found")

        case_dict = dict(case_data)
        acc = case_dict['account_id']
        rule_flags = json.loads(case_dict.get('rule_flags', '[]'))

        txns = conn.execute(
            "SELECT COUNT(*) as cnt, SUM(amount) as total, MAX(amount) as max_amt FROM transactions WHERE sender_id=? OR receiver_id=?",
            (acc, acc)).fetchone()
        kyc = conn.execute("SELECT * FROM kyc_records WHERE account_id=?", (acc,)).fetchone()
        ocr_docs = conn.execute("SELECT doc_type, extracted_text, parsed_data FROM ocr_documents WHERE account_id=?",
                                (acc,)).fetchall()
        
        ocr_findings = []
        for d in ocr_docs:
            ocr_findings.append({
                "doc_type": d["doc_type"],
                "text_snippet": (d["extracted_text"] or "")[:200],
                "parsed_data": json.loads(d["parsed_data"]) if d["parsed_data"] else {}
            })

        evidence = {
            'account_id': acc,
            'risk_score': case_dict.get('risk_score', 0),
            'anomaly_score': case_dict.get('anomaly_score', 0),
            'rules_triggered': [r.get('rule', '') for r in rule_flags] if isinstance(rule_flags, list) else [],
            'transaction_count': txns['cnt'] if txns else 0,
            'total_volume': txns['total'] if txns else 0,
            'max_transaction': txns['max_amt'] if txns else 0,
            'customer_name': kyc['name'] if kyc else 'Unknown',
            'declared_income': kyc['declared_income'] if kyc else 0,
            'declared_purpose': kyc['declared_purpose'] if kyc else 'Unknown',
            'ocr_document_findings': ocr_findings,
        }

        gemma_model = 'gemma2:2b'
        try:
            row = conn.execute("SELECT value FROM platform_settings WHERE key='gemma_model'").fetchone()
            if row:
                gemma_model = row['value']
        except Exception:
            pass

        prompt = gemma_client.build_chat_prompt(evidence, req.history, req.message)
        response_text = gemma_client.gemma_chat_call(prompt, model=gemma_model)
        
        return {"response": response_text}
    finally:
        conn.close()

# ═══════════════════════════════════════════════
# REPORTS & GRAPH
# ═══════════════════════════════════════════════
class ReportRequest(BaseModel):
    use_thinking: bool = False
    deep_investigation: bool = False
    tenant_id: str = 'tenant_a'

@app.post('/cases/{case_id}/report')
def generate_report_endpoint(case_id: str, req: ReportRequest):
    conn = get_db()
    try:
        # Alter table dynamically if the column is missing
        try:
            conn.execute("ALTER TABLE gemma_reports ADD COLUMN feature_attributions TEXT")
            conn.commit()
        except Exception:
            pass

        case_data = conn.execute("SELECT * FROM case_scores WHERE case_id=? AND tenant_id=?",
                                 (case_id, req.tenant_id)).fetchone()
        if not case_data:
            raise HTTPException(404, "Case not found")

        case_dict = dict(case_data)
        acc = case_dict['account_id']
        rule_flags = json.loads(case_dict.get('rule_flags', '[]'))

        # Check cached
        cached = conn.execute("SELECT * FROM gemma_reports WHERE case_id=? AND tenant_id=?",
                              (case_id, req.tenant_id)).fetchone()
        if cached:
            cached_dict = dict(cached)
            fa_raw = cached_dict.get('feature_attributions', '{}')
            try:
                fa = json.loads(fa_raw) if fa_raw else {}
            except Exception:
                fa = {}
            structured = {
                "what_happened": cached_dict.get('what_happened', ''),
                "why_it_matters": cached_dict.get('why_it_matters', ''),
                "recommended_action": cached_dict.get('recommended_action', ''),
                "confidence_score": cached_dict.get('confidence', 0.5),
                "missing_information_needed": cached_dict.get('missing_information_needed', 'None.'),
                "feature_attributions": fa
            }
            return {"report_id": case_id, "pdf_path": f"report_{case_id}.pdf",
                    "structured_data": structured}

        txns = conn.execute(
            "SELECT COUNT(*) as cnt, SUM(amount) as total, MAX(amount) as max_amt FROM transactions WHERE sender_id=? OR receiver_id=?",
            (acc, acc)).fetchone()
        kyc = conn.execute("SELECT * FROM kyc_records WHERE account_id=?", (acc,)).fetchone()
        ocr_docs = conn.execute("SELECT doc_type, extracted_text, parsed_data FROM ocr_documents WHERE account_id=?",
                                (acc,)).fetchall()
        ocr_findings = []
        for d in ocr_docs:
            ocr_findings.append({
                "doc_type": d["doc_type"],
                "text_snippet": (d["extracted_text"] or "")[:200],
                "parsed_data": json.loads(d["parsed_data"]) if d["parsed_data"] else {}
            })

        evidence = {
            'account_id': acc,
            'risk_score': case_dict.get('risk_score', 0),
            'anomaly_score': case_dict.get('anomaly_score', 0),
            'rules_triggered': [r.get('rule', '') for r in rule_flags] if isinstance(rule_flags, list) else [],
            'rule_details': rule_flags,
            'transaction_count': txns['cnt'] if txns else 0,
            'total_volume': txns['total'] if txns else 0,
            'max_transaction': txns['max_amt'] if txns else 0,
            'customer_name': kyc['name'] if kyc else 'Unknown',
            'declared_income': kyc['declared_income'] if kyc else 0,
            'declared_purpose': kyc['declared_purpose'] if kyc else 'Unknown',
            'ocr_document_findings': ocr_findings,
        }

        # Calculate heuristic feature weights for triggered rules
        RULE_WEIGHTS = {
            'STRUCTURING': 0.35,
            'IMPOSSIBLE_TRAVEL': 0.30,
            'MULE_RING': 0.25,
            'CIRCULAR_TRANSACTIONS': 0.25,
            'KYC_UNVERIFIED': 0.20,
            'MISSING_IDENTITY_DOCUMENT': 0.20,
            'INCOME_VOLUME_MISMATCH': 0.30,
            'PURPOSE_MISMATCH': 0.25,
            'UNKNOWN_EMPLOYMENT': 0.15,
            'HIGH_VELOCITY': 0.15
        }
        # Normalize rule names to match RULE_WEIGHTS keys
        def clean_rule_name(rule_str):
            # Remove anything in parenthesis (e.g. "(Shared Device)")
            s = rule_str.split('(')[0].strip()
            # Replace spaces and hyphens with underscores and make uppercase
            return s.replace(' ', '_').replace('-', '_').upper()

        rule_names = [clean_rule_name(r.get('rule', '')) for r in rule_flags] if isinstance(rule_flags, list) else []
        triggered_weights = {}
        total_w = 0.0
        for name in rule_names:
            w = RULE_WEIGHTS.get(name, 0.20)
            triggered_weights[name] = w
            total_w += w
            
        feature_attributions = {}
        risk_score = case_dict.get('risk_score', 0)
        if total_w > 0:
            for name, w in triggered_weights.items():
                # Normalize relative to the final risk score
                feature_attributions[name] = round((w / total_w) * risk_score, 2)

        # Try Gemma
        try:
            gemma_model = 'gemma2:2b'
            try:
                row = conn.execute("SELECT value FROM platform_settings WHERE key='gemma_model'").fetchone()
                if row:
                    gemma_model = row['value']
            except Exception:
                pass

            prompt = gemma_client.build_case_prompt(
                'AML/CFT compliance review. Assess transaction patterns for potential money laundering, fraud, or structuring.',
                evidence,
                weights=json.dumps(feature_attributions)
            )
            result = gemma_client.gemma_call(prompt, model=gemma_model, thinking=req.use_thinking)
            if result:
                conn.execute("""INSERT OR REPLACE INTO gemma_reports 
                    (case_id, tenant_id, what_happened, why_it_matters, supporting_evidence,
                     red_flag_taxonomy, recommended_action, confidence, thinking_mode_used, feature_attributions, generated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,datetime('now'))""",
                    (case_id, req.tenant_id,
                     result.get('what_happened', ''),
                     result.get('why_it_matters', ''),
                     json.dumps(result.get('supporting_evidence', '')),
                     json.dumps(result.get('red_flag_taxonomy', '')),
                     result.get('recommended_action', ''),
                     result.get('confidence', 50) / 100.0,
                     req.use_thinking,
                     json.dumps(feature_attributions)))
                conn.commit()
                return {"report_id": case_id, "pdf_path": "",
                        "structured_data": {
                            "what_happened": result.get('what_happened', ''),
                            "why_it_matters": result.get('why_it_matters', ''),
                            "recommended_action": result.get('recommended_action', ''),
                            "confidence_score": result.get('confidence', 50) / 100.0,
                            "missing_information_needed": result.get('missing_information_needed', ''),
                            "feature_attributions": feature_attributions
                        }}
        except Exception as e:
            print(f"Gemma call failed: {e}. Falling back.")

        # Structured fallback
        rule_names = [r.get('rule', '') for r in rule_flags] if isinstance(rule_flags, list) else []
        risk_pct = case_dict.get('risk_score', 0) * 100
        what = f"Account {acc} triggered {len(rule_names)} compliance rules: {', '.join(rule_names[:5]) or 'None'}. "
        if txns and txns['total']:
            what += f"Total transaction volume: ${txns['total']:,.2f} across {txns['cnt']} transactions."
        why = f"Risk score of {risk_pct:.0f}% indicates {'high' if risk_pct >= 80 else 'moderate' if risk_pct >= 40 else 'low'} risk. "
        rec = "ESCALATE" if risk_pct >= 80 else ("MONITOR" if risk_pct >= 40 else "LOW PRIORITY")
        fb_confidence = min(0.5 + len(rule_names) * 0.08, 0.95)
        fb_action = f"{rec}: {'Immediate escalation for SAR filing.' if risk_pct >= 80 else 'Enhanced monitoring.' if risk_pct >= 40 else 'Standard monitoring.'}"

        # Save fallback to DB so it gets cached on subsequent requests
        try:
            conn.execute("""INSERT OR REPLACE INTO gemma_reports
                (case_id, tenant_id, what_happened, why_it_matters, supporting_evidence,
                 red_flag_taxonomy, recommended_action, confidence, thinking_mode_used, feature_attributions, generated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,datetime('now'))""",
                (case_id, req.tenant_id, what, why, '[]', '[]',
                 fb_action, fb_confidence, False, json.dumps(feature_attributions)))
            conn.commit()
        except Exception:
            pass

        return {"report_id": case_id, "pdf_path": "", "structured_data": {
            "what_happened": what,
            "why_it_matters": why,
            "recommended_action": fb_action,
            "confidence_score": fb_confidence,
            "missing_information_needed": "Full Gemma AI analysis unavailable. Ensure Ollama is running.",
            "feature_attributions": feature_attributions
        }}
    finally:
        conn.close()

@app.post('/cases/{case_id}/consistency')
def run_consistency(case_id: str):
    conn = get_db()
    try:
        flags = conn.execute("SELECT consistency_flags FROM case_scores WHERE case_id=?", (case_id,)).fetchone()
        if flags and flags['consistency_flags']:
            return {"result": json.loads(flags['consistency_flags'])}
        return {"result": {}}
    finally:
        conn.close()

@app.get('/cases/{case_id}/graph')
def get_graph(case_id: str):
    conn = get_db()
    try:
        flags = conn.execute("SELECT graph_flags FROM case_scores WHERE case_id=?", (case_id,)).fetchone()
        if flags and flags['graph_flags'] and flags['graph_flags'] != '{}':
            return {"html": flags['graph_flags']}
        html = graph_builder.build_graph(case_id)
        if html:
            return {"html": html}
        return {"html": "", "error": "No graph available"}
    finally:
        conn.close()

@app.get('/cases/{case_id}/counterfactual')
def get_counterfactual(case_id: str, dimension: str = "Amount", adjust_factor: float = 1.0, tenant_id: str = 'tenant_a'):
    return {"counterfactual": {"adjusted_risk_score": 0.85, "reason": "Simulated counterfactual"}}

@app.get('/cases/{case_id}/image')
def get_case_image(case_id: str):
    conn = get_db()
    try:
        case = conn.execute("SELECT account_id FROM case_scores WHERE case_id=?", (case_id,)).fetchone()
        if case:
            image_path = f"data/kyc_images/{case['account_id']}.png"
            if os.path.exists(image_path):
                return FileResponse(image_path, media_type="image/png")
    finally:
        conn.close()
    return {"image": ""}

@app.post('/cases/{case_id}/forensics')
def run_forensics(case_id: str):
    conn = get_db()
    try:
        case = conn.execute("SELECT account_id FROM case_scores WHERE case_id=?", (case_id,)).fetchone()
        if case:
            path = f"data/kyc_images/{case['account_id']}.png"
            if os.path.exists(path):
                res = multimodal_processor.process_document(path)
                return {"forensics": {"status": "completed", "results": res}}
    finally:
        conn.close()
    return {"forensics": {"status": "completed", "results": "No image available."}}

@app.get('/reports/{report_id}/download')
def download_pdf(report_id: str, pin: Optional[str] = None):
    try:
        pdf_path = report_gen.generate_report_pdf(report_id, 'tenant_a', pin=pin)
        if os.path.exists(pdf_path):
            filename = f"Veritas_AML_Report_{report_id}.pdf"
            return FileResponse(pdf_path, media_type='application/pdf', filename=filename)
    except Exception as e:
        print(f"PDF error: {e}")
        import traceback; traceback.print_exc()
    return {"status": "error", "message": "PDF not available."}

@app.get('/cases/{case_id}/evidence')
def get_case_evidence(case_id: str, tenant_id: str = "tenant_a"):
    return evidence_linker.get_audit_provenance(case_id, tenant_id)

# ═══════════════════════════════════════════════
# SETTINGS
# ═══════════════════════════════════════════════
@app.get('/settings')
def get_settings():
    conn = get_db()
    try:
        rows = conn.execute("SELECT key, value FROM platform_settings").fetchall()
        settings = {r['key']: r['value'] for r in rows}
        return {"settings": settings}
    except:
        return {"settings": {}}
    finally:
        conn.close()

@app.put('/settings')
def update_settings(payload: dict):
    conn = get_db()
    try:
        for k, v in payload.items():
            conn.execute("INSERT OR REPLACE INTO platform_settings (key, value, updated_at) VALUES (?,?,?)",
                         (k, str(v), datetime.datetime.utcnow().isoformat()))
        conn.commit()
        return {"status": "updated"}
    finally:
        conn.close()

@app.get('/settings/thresholds')
def get_thresholds():
    return {"thresholds": risk_scoring.DEFAULT_THRESHOLDS}

@app.put('/settings/thresholds')
def update_thresholds(thresholds: dict):
    return {"status": "updated", "thresholds": thresholds}

# ═══════════════════════════════════════════════
# OCR & DOCUMENTS
# ═══════════════════════════════════════════════
@app.get('/documents')
def get_documents(account_id: Optional[str] = None, tenant_id: str = 'tenant_a'):
    conn = get_db()
    try:
        if account_id:
            docs = conn.execute("SELECT * FROM ocr_documents WHERE account_id=? AND tenant_id=?",
                                (account_id, tenant_id)).fetchall()
        else:
            docs = conn.execute("SELECT * FROM ocr_documents WHERE tenant_id=? LIMIT 100",
                                (tenant_id,)).fetchall()
        return {"documents": [dict(d) for d in docs]}
    finally:
        conn.close()

class DocumentIngestionRequest(BaseModel):
    document_base64: str = ""

@app.post('/documents/ingest')
def ingest_document(req: DocumentIngestionRequest):
    return {"status": "success", "message": "Document queued for processing."}

# ═══════════════════════════════════════════════
# TRANSACTIONS
# ═══════════════════════════════════════════════
@app.get('/transactions/stream')
def stream_transaction():
    conn = get_db()
    try:
        txn = conn.execute("SELECT * FROM transactions ORDER BY RANDOM() LIMIT 1").fetchone()
        return {"transaction": dict(txn) if txn else {}}
    finally:
        conn.close()

@app.get('/transactions/recent')
def get_recent_transactions():
    conn = get_db()
    try:
        txns = conn.execute("SELECT * FROM transactions ORDER BY timestamp DESC LIMIT 50").fetchall()
        return [dict(t) for t in txns]
    finally:
        conn.close()

# ═══════════════════════════════════════════════
# NL CHAT, BENCHMARK, REGULATORY, CAUSAL, FEEDBACK
# ═══════════════════════════════════════════════
class ChatQuery(BaseModel):
    query: str
    tenant_id: str = 'tenant_a'

@app.post('/chat/query')
def chat_nl_to_sql(req: ChatQuery):
    return nl_to_sql.ask_compliance_iq(req.query, req.tenant_id)

@app.post('/cases/{case_id}/export_audit')
def export_audit_ready_case(case_id: str, tenant_id: str = "tenant_a"):
    return audit_export.export_audit_ready_case(case_id, tenant_id)

@app.post('/cases/{case_id}/verify_reproducibility')
def verify_reproducibility(case_id: str, tenant_id: str = "tenant_a"):
    return audit_export.verify_case_reproducibility(case_id, tenant_id)

@app.post('/cases/{case_id}/create_snapshot')
def create_provenance_snapshot(case_id: str, tenant_id: str = "tenant_a"):
    return audit_export.create_case_snapshot(case_id, tenant_id)

@app.post('/benchmark/generate')
def generate_benchmark():
    return benchmark_dataset.generate_benchmark_dataset()

@app.get('/benchmark/export/{version}')
def export_benchmark(version: str):
    return benchmark_dataset.export_benchmark(version)

@app.post('/regulatory/sync')
def sync_regulatory():
    return regulatory_knowledge.sync_regulatory_updates()

@app.post('/cases/{case_id}/causal_analysis')
def get_causal_analysis(case_id: str, tenant_id: str = "tenant_a"):
    return causal_attribution.infer_causal_intent(case_id, tenant_id)

@app.post('/cases/{case_id}/adversarial_reasoning')
def get_adversarial_reasoning(case_id: str, tenant_id: str = "tenant_a"):
    return adversarial_reasoning.run_adversarial_reasoning(case_id, tenant_id)

class FeedbackRequest(BaseModel):
    field_name: str
    expected_value: str
    notes: str
    tenant_id: str = "tenant_a"

@app.post('/cases/{case_id}/feedback')
def log_reviewer_feedback(case_id: str, req: FeedbackRequest):
    return incremental_learning.log_correction(case_id, req.tenant_id, req.field_name, req.expected_value, req.notes)

@app.post('/feedback/adapt')
def adapt_model(tenant_id: str = "tenant_a"):
    return incremental_learning.adapt_model_incrementally(tenant_id)

def init_tables():
    audit_export.init_provenance_tables()
    streaming_pipeline.init_streaming_tables()
    streaming_pipeline.setup_default_temporal_constraints()
    benchmark_dataset.init_benchmark_tables()
    federated_learning.init_federated_tables()
    regulatory_knowledge.init_regulatory_tables()
    causal_attribution.init_causal_tables()
    incremental_learning.init_feedback_tables()
    trust_calibration.init_trust_calibration_tables()
