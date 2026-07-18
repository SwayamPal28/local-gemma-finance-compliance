const API_BASE = import.meta.env.VITE_API_BASE || `http://${window.location.hostname}:8000`;
const TENANT_ID = 'tenant_a';

export async function fetchCases() {
  const r = await fetch(`${API_BASE}/cases?tenant_id=${TENANT_ID}`);
  if (!r.ok) throw new Error('Failed to fetch cases');
  return r.json();
}

export async function fetchCaseDetails(caseId) {
  const r = await fetch(`${API_BASE}/cases/${caseId}?tenant_id=${TENANT_ID}`);
  if (!r.ok) throw new Error('Failed to fetch case details');
  return r.json();
}

export async function fetchJourney(caseId) {
  const r = await fetch(`${API_BASE}/cases/${caseId}/journey`);
  if (!r.ok) throw new Error('Failed to fetch journey');
  return r.json();
}

export async function generateReport(caseId) {
  const r = await fetch(`${API_BASE}/cases/${caseId}/report`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tenant_id: TENANT_ID, use_thinking: false })
  });
  if (!r.ok) throw new Error('Failed to generate report');
  return r.json();
}

export async function fetchGraph(caseId) {
  const r = await fetch(`${API_BASE}/cases/${caseId}/graph`);
  if (!r.ok) throw new Error('Failed to fetch graph');
  return r.json();
}

export async function updateDisposition(caseId, action, reason, confidence = 80, timeMs = 5000) {
  const r = await fetch(`${API_BASE}/cases/${caseId}/disposition`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action, reason, tenant_id: TENANT_ID, reviewer_id: 'analyst_01', reviewer_confidence: confidence, time_to_decision_ms: timeMs })
  });
  if (!r.ok) throw new Error('Failed to update disposition');
  return r.json();
}

export async function exportAuditCase(caseId) {
  const r = await fetch(`${API_BASE}/cases/${caseId}/export_audit?tenant_id=${TENANT_ID}`, { method: 'POST' });
  if (!r.ok) throw new Error('Failed to export');
  return r.json();
}

export async function fetchAuditLogs(search = '', action = '') {
  let url = `${API_BASE}/audit?tenant_id=${TENANT_ID}&limit=500`;
  if (search) url += `&search=${encodeURIComponent(search)}`;
  if (action) url += `&action=${encodeURIComponent(action)}`;
  const r = await fetch(url);
  if (!r.ok) throw new Error('Failed to fetch audit logs');
  return r.json();
}

export async function fetchAuditTimeline(caseId) {
  const r = await fetch(`${API_BASE}/audit/timeline/${caseId}`);
  if (!r.ok) throw new Error('Failed to fetch timeline');
  return r.json();
}

export async function fetchStreamingStats() {
  const r = await fetch(`${API_BASE}/streaming/stats?tenant_id=${TENANT_ID}`);
  if (!r.ok) throw new Error('Failed to fetch streaming stats');
  return r.json();
}

export async function fetchFederatedStatus() {
  const r = await fetch(`${API_BASE}/federated/status?tenant_id=${TENANT_ID}`);
  if (!r.ok) throw new Error('Failed to fetch federated status');
  return r.json();
}

export async function fetchJourneyReplay(caseId) {
  const r = await fetch(`${API_BASE}/cases/${caseId}/journey_replay`);
  if (!r.ok) throw new Error('Failed to fetch journey replay');
  return r.json();
}

export async function fetchTrustDashboard() {
  const r = await fetch(`${API_BASE}/trust/dashboard?tenant_id=${TENANT_ID}`);
  if (!r.ok) throw new Error('Failed to fetch trust dashboard');
  return r.json();
}

export async function fetchKyc(caseId) {
  const r = await fetch(`${API_BASE}/cases/${caseId}/kyc?tenant_id=${TENANT_ID}`);
  if (!r.ok) throw new Error('Failed to fetch KYC');
  return r.json();
}

export async function fetchSettings() {
  const r = await fetch(`${API_BASE}/settings`);
  if (!r.ok) throw new Error('Failed to fetch settings');
  return r.json();
}

export async function updateSettings(settings) {
  const r = await fetch(`${API_BASE}/settings`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings)
  });
  if (!r.ok) throw new Error('Failed to update settings');
  return r.json();
}

export async function runAdversarialReasoning(caseId) {
  const r = await fetch(`${API_BASE}/cases/${caseId}/adversarial_reasoning`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  });
  if (!r.ok) throw new Error('Failed to run adversarial reasoning');
  return r.json();
}

export async function sendChatMessage(caseId, message, history) {
  const r = await fetch(`${API_BASE}/cases/${caseId}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tenant_id: TENANT_ID, message, history })
  });
  if (!r.ok) throw new Error('Failed to send chat message');
  return r.json();
}
