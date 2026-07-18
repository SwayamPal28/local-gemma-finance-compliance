import React, { useState, useEffect, useRef, useCallback } from 'react';
import './App.css';
import { fetchCases, fetchCaseDetails, fetchJourney, generateReport, fetchGraph, updateDisposition, exportAuditCase, fetchAuditLogs, fetchStreamingStats, fetchFederatedStatus, fetchJourneyReplay, fetchTrustDashboard, fetchKyc, fetchSettings, updateSettings, runAdversarialReasoning, sendChatMessage } from './api';

const AUTH_BASE = import.meta.env.VITE_API_BASE || `http://${window.location.hostname}:8000`;

function LoginPage({ onLogin }) {
  const [mode, setMode] = useState('login'); // 'login' | 'register' | 'otp' | 'setup2fa'
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [otp, setOtp] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [otpUsername, setOtpUsername] = useState('');
  const [setup2fa, setSetup2fa] = useState(null); // { qr_code, manual_code }
  const [enable2fa, setEnable2fa] = useState(false);
  const [registerSuccess, setRegisterSuccess] = useState(null);

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const r = await fetch(`${AUTH_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || 'Login failed');
      if (data.status === 'otp_required') {
        setOtpUsername(data.username);
        setMode('otp');
      } else {
        onLogin(data.user);
      }
    } catch (err) {
      setError(err.message);
    }
    setLoading(false);
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const r = await fetch(`${AUTH_BASE}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password, full_name: fullName })
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || 'Registration failed');
      setRegisterSuccess(data.user);
      if (enable2fa) {
        // Setup 2FA
        const r2 = await fetch(`${AUTH_BASE}/auth/setup-2fa`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username })
        });
        const data2 = await r2.json();
        if (r2.ok) {
          setSetup2fa(data2);
          setMode('setup2fa');
        } else {
          onLogin(data.user);
        }
      } else {
        onLogin(data.user);
      }
    } catch (err) {
      setError(err.message);
    }
    setLoading(false);
  };

  const handleVerifyOtp = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const r = await fetch(`${AUTH_BASE}/auth/verify-otp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: otpUsername, otp })
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || 'Invalid OTP');
      onLogin(data.user);
    } catch (err) {
      setError(err.message);
    }
    setLoading(false);
  };

  const handleEnable2fa = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const r = await fetch(`${AUTH_BASE}/auth/enable-2fa`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, otp })
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || 'Invalid OTP');
      onLogin(registerSuccess);
    } catch (err) {
      setError(err.message);
    }
    setLoading(false);
  };

  const cardStyle = {
    background: 'var(--bg-secondary)',
    border: '1px solid var(--border-color)',
    borderRadius: '12px',
    padding: '2.5rem',
    width: '420px',
    maxWidth: '90vw',
    boxShadow: '0 20px 60px rgba(0,0,0,0.4)',
  };

  const inputStyle = {
    width: '100%',
    padding: '0.85rem 1rem',
    borderRadius: '6px',
    border: '1px solid var(--border-color)',
    background: 'var(--bg-tertiary)',
    color: 'var(--text-primary)',
    fontSize: '0.95rem',
    outline: 'none',
    boxSizing: 'border-box',
  };

  const labelStyle = {
    display: 'block',
    marginBottom: '0.4rem',
    fontSize: '0.85rem',
    color: 'var(--text-secondary)',
    fontWeight: 500,
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-primary)', padding: '2rem' }}>
      <div style={cardStyle}>
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="var(--accent-primary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginBottom: '0.75rem' }}>
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
          </svg>
          <h1 style={{ margin: 0, color: 'var(--text-primary)', fontSize: '1.5rem' }}>Veritas AML</h1>
          <p style={{ margin: '0.25rem 0 0', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>Financial Compliance & Risk Triage</p>
        </div>

        {error && (
          <div style={{ padding: '0.75rem 1rem', background: 'rgba(239,68,68,0.1)', border: '1px solid var(--danger)', borderRadius: '6px', color: 'var(--danger)', marginBottom: '1.25rem', fontSize: '0.9rem' }}>
            {error}
          </div>
        )}

        {mode === 'login' && (
          <form onSubmit={handleLogin}>
            <div style={{ marginBottom: '1.25rem' }}>
              <label style={labelStyle}>Username</label>
              <input type="text" value={username} onChange={e => setUsername(e.target.value)} placeholder="Enter username" style={inputStyle} required />
            </div>
            <div style={{ marginBottom: '1.5rem' }}>
              <label style={labelStyle}>Password</label>
              <input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="Enter password" style={inputStyle} required />
            </div>
            <button className="btn btn-primary" type="submit" disabled={loading} style={{ width: '100%', padding: '0.85rem', fontSize: '1rem' }}>
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
            <p style={{ textAlign: 'center', marginTop: '1.25rem', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
              Don't have an account?{' '}
              <a href="#" onClick={(e) => { e.preventDefault(); setMode('register'); setError(''); }} style={{ color: 'var(--accent-primary)' }}>Register</a>
            </p>
          </form>
        )}

        {mode === 'register' && (
          <form onSubmit={handleRegister}>
            <div style={{ marginBottom: '1rem' }}>
              <label style={labelStyle}>Full Name</label>
              <input type="text" value={fullName} onChange={e => setFullName(e.target.value)} placeholder="Enter full name" style={inputStyle} />
            </div>
            <div style={{ marginBottom: '1rem' }}>
              <label style={labelStyle}>Username</label>
              <input type="text" value={username} onChange={e => setUsername(e.target.value)} placeholder="Choose a username" style={inputStyle} required />
            </div>
            <div style={{ marginBottom: '1rem' }}>
              <label style={labelStyle}>Password</label>
              <input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="Choose a password" style={inputStyle} required />
            </div>
            <div style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <input type="checkbox" id="enable2fa" checked={enable2fa} onChange={e => setEnable2fa(e.target.checked)} style={{ width: '18px', height: '18px', accentColor: 'var(--accent-primary)' }} />
              <label htmlFor="enable2fa" style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', cursor: 'pointer' }}>
                Enable Two-Factor Authentication (Google Authenticator)
              </label>
            </div>
            <button className="btn btn-primary" type="submit" disabled={loading} style={{ width: '100%', padding: '0.85rem', fontSize: '1rem' }}>
              {loading ? 'Creating account...' : 'Create Account'}
            </button>
            <p style={{ textAlign: 'center', marginTop: '1.25rem', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
              Already have an account?{' '}
              <a href="#" onClick={(e) => { e.preventDefault(); setMode('login'); setError(''); }} style={{ color: 'var(--accent-primary)' }}>Sign In</a>
            </p>
          </form>
        )}

        {mode === 'otp' && (
          <form onSubmit={handleVerifyOtp}>
            <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
              <div style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>🔐</div>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                Two-factor authentication is enabled for <strong style={{ color: 'var(--text-primary)' }}>{otpUsername}</strong>. Enter the 6-digit code from your Google Authenticator app.
              </p>
            </div>
            <div style={{ marginBottom: '1.5rem' }}>
              <label style={labelStyle}>One-Time Password</label>
              <input type="text" value={otp} onChange={e => setOtp(e.target.value)} placeholder="Enter 6-digit OTP" style={{ ...inputStyle, textAlign: 'center', fontSize: '1.5rem', letterSpacing: '0.5rem' }} maxLength={6} required autoFocus />
            </div>
            <button className="btn btn-primary" type="submit" disabled={loading} style={{ width: '100%', padding: '0.85rem', fontSize: '1rem' }}>
              {loading ? 'Verifying...' : 'Verify OTP'}
            </button>
            <p style={{ textAlign: 'center', marginTop: '1rem' }}>
              <a href="#" onClick={(e) => { e.preventDefault(); setMode('login'); setError(''); setOtp(''); }} style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>Back to login</a>
            </p>
          </form>
        )}

        {mode === 'setup2fa' && setup2fa && (
          <form onSubmit={handleEnable2fa}>
            <div style={{ textAlign: 'center', marginBottom: '1.25rem' }}>
              <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>📱</div>
              <h3 style={{ margin: 0, color: 'var(--text-primary)' }}>Set Up Two-Factor Authentication</h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginTop: '0.5rem' }}>
                Scan this QR code with Google Authenticator, then enter the 6-digit code to verify.
              </p>
            </div>
            <div style={{ textAlign: 'center', marginBottom: '1rem' }}>
              <img src={setup2fa.qr_code} alt="2FA QR Code" style={{ width: '200px', height: '200px', borderRadius: '8px', border: '2px solid var(--border-color)' }} />
            </div>
            <div style={{ textAlign: 'center', marginBottom: '1.25rem' }}>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', margin: '0 0 0.25rem' }}>Or enter this code manually:</p>
              <code style={{ background: 'var(--bg-tertiary)', padding: '0.5rem 1rem', borderRadius: '4px', fontSize: '0.9rem', color: 'var(--accent-primary)', letterSpacing: '0.1rem', border: '1px solid var(--border-color)' }}>{setup2fa.manual_code}</code>
            </div>
            <div style={{ marginBottom: '1.25rem' }}>
              <label style={labelStyle}>Verification Code</label>
              <input type="text" value={otp} onChange={e => setOtp(e.target.value)} placeholder="Enter 6-digit code" style={{ ...inputStyle, textAlign: 'center', fontSize: '1.5rem', letterSpacing: '0.5rem' }} maxLength={6} required autoFocus />
            </div>
            <button className="btn btn-primary" type="submit" disabled={loading} style={{ width: '100%', padding: '0.85rem', fontSize: '1rem' }}>
              {loading ? 'Verifying...' : 'Verify & Enable 2FA'}
            </button>
            <p style={{ textAlign: 'center', marginTop: '1rem' }}>
              <a href="#" onClick={(e) => { e.preventDefault(); if(registerSuccess) onLogin(registerSuccess); }} style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>Skip for now</a>
            </p>
          </form>
        )}
      </div>
    </div>
  );
}

function Badge({ riskScore }) {
  if (riskScore >= 0.8) return <span className="badge high">High Risk</span>;
  if (riskScore >= 0.4) return <span className="badge medium">Medium Risk</span>;
  return <span className="badge low">Low Risk</span>;
}

function getRuleCount(c) {
  try {
    const flags = typeof c.rule_flags === 'string' ? JSON.parse(c.rule_flags) : (c.rule_flags || []);
    if (Array.isArray(flags)) return flags.length;
    if (typeof flags === 'object') return Object.keys(flags).length;
  } catch(e) {}
  return 0;
}

function ChatAssistant({ caseId }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSend = async () => {
    if (!input.trim()) return;
    const userMsg = { sender: 'user', text: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      // Pass the previous messages as history for context
      const res = await sendChatMessage(caseId, userMsg.text, messages);
      setMessages(prev => [...prev, { sender: 'assistant', text: res.response }]);
    } catch (err) {
      console.error(err);
      setMessages(prev => [...prev, { sender: 'assistant', text: 'Error connecting to AI assistant.' }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ flex: 1, overflowY: 'auto', padding: '1rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {messages.length === 0 && (
          <div style={{ textAlign: 'center', color: 'var(--text-secondary)', marginTop: '2rem' }}>
            Ask the AI Copilot about this case...
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} style={{ alignSelf: m.sender === 'user' ? 'flex-end' : 'flex-start', maxWidth: '85%', background: m.sender === 'user' ? 'var(--accent-primary)' : 'var(--bg-tertiary)', color: m.sender === 'user' ? '#fff' : 'var(--text-primary)', padding: '0.75rem 1rem', borderRadius: '8px', border: m.sender === 'user' ? 'none' : '1px solid var(--border-color)', lineHeight: 1.4, whiteSpace: 'pre-wrap' }}>
            {m.text}
          </div>
        ))}
        {loading && (
          <div style={{ alignSelf: 'flex-start', padding: '0.75rem 1rem', color: 'var(--text-tertiary)' }}>
            AI Copilot is thinking...
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      <div style={{ padding: '1rem', borderTop: '1px solid var(--border-color)', display: 'flex', gap: '0.5rem' }}>
        <input 
          type="text" 
          value={input} 
          onChange={(e) => setInput(e.target.value)} 
          onKeyDown={(e) => e.key === 'Enter' && handleSend()} 
          placeholder="Type your question..." 
          style={{ flex: 1, padding: '0.75rem', borderRadius: '4px', border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--text-primary)' }} 
        />
        <button className="btn btn-primary" onClick={handleSend} disabled={loading}>
          Send
        </button>
      </div>
    </div>
  );
}

function CaseList({ onSelectCase }) {
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sortOrder, setSortOrder] = useState('none');

  useEffect(() => {
    fetchCases()
      .then(data => { setCases(data); setLoading(false); })
      .catch(err => { console.error(err); setLoading(false); });
  }, []);

  if (loading) return <div>Loading cases...</div>;

  const sortedCases = [...cases].sort((a, b) => {
    if (sortOrder === 'high-to-low') return b.risk_score - a.risk_score;
    if (sortOrder === 'low-to-high') return a.risk_score - b.risk_score;
    if (sortOrder === 'rules-high-to-low') return getRuleCount(b) - getRuleCount(a);
    if (sortOrder === 'rules-low-to-high') return getRuleCount(a) - getRuleCount(b);
    if (sortOrder === 'txn-high-to-low') return (b.txn_count || 0) - (a.txn_count || 0);
    if (sortOrder === 'txn-low-to-high') return (a.txn_count || 0) - (b.txn_count || 0);
    return 0;
  });

  return (
    <div>
      <div style={{ marginBottom: '1rem', display: 'flex', gap: '1rem', alignItems: 'center' }}>
        <label style={{ color: 'var(--text-secondary)' }}>Sort by:</label>
        <select value={sortOrder} onChange={(e) => setSortOrder(e.target.value)}
          style={{ padding: '0.5rem', borderRadius: '4px', background: 'var(--bg-secondary)', color: 'var(--text-primary)', border: '1px solid var(--border-color)' }}>
          <option value="none">Default (ROI)</option>
          <option value="high-to-low">Risk: High to Low</option>
          <option value="low-to-high">Risk: Low to High</option>
          <option value="rules-high-to-low">Rules: Most to Least</option>
          <option value="rules-low-to-high">Rules: Least to Most</option>
          <option value="txn-high-to-low">Transactions: Most to Least</option>
          <option value="txn-low-to-high">Transactions: Least to Most</option>
        </select>
      </div>
      <div className="case-list-grid">
        {sortedCases.map((c) => (
          <div key={c.case_id} className="glass-panel case-card" onClick={() => onSelectCase(c.case_id)}>
          <div className="case-info">
            <div className="case-id">{c.case_id}</div>
            <div className="case-meta">Account: {c.account_id} • ROI: ${c.expected_roi?.toFixed(2)}</div>
            <div className="case-meta" style={{marginTop: '4px'}}>
              <span className={`badge ${c.status === 'ESCALATED' ? 'high' : c.status === 'MONITORING' ? 'medium' : ''}`}
                style={c.status === 'NEW' ? {background: 'var(--bg-tertiary)', color: 'var(--text-secondary)'} : {}}>
                {c.status}
              </span>
            </div>
          </div>
          <div className="case-stats">
            <div className="stat-item"><span className="stat-label">Txns</span><span className="stat-value">{c.txn_count || 0}</span></div>
            <div className="stat-item"><span className="stat-label">Rules</span><span className="stat-value">{getRuleCount(c)}</span></div>
            <div className="stat-item"><span className="stat-label">Risk Score</span><span className="stat-value">{(c.risk_score * 100).toFixed(0)}%</span></div>
            <Badge riskScore={c.risk_score} />
          </div>
        </div>
      ))}
    </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════
   JOURNEY REPLAY (preserved from previous implementation)
   ═══════════════════════════════════════════════════════ */
function JourneyReplayView({ caseId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [filter, setFilter] = useState('all');
  const [infoTab, setInfoTab] = useState('live');
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersRef = useRef([]);
  const timerRef = useRef(null);

  useEffect(() => {
    fetchJourneyReplay(caseId).then(d => { setData(d); setLoading(false); }).catch(() => setLoading(false));
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [caseId]);

  useEffect(() => {
    if (!data || !mapRef.current || mapInstanceRef.current) return;
    const L = window.L; if (!L) return;
    const map = L.map(mapRef.current, { center: [20, 0], zoom: 2, zoomControl: true, attributionControl: false });
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', { maxZoom: 19 }).addTo(map);
    mapInstanceRef.current = map;
    return () => { if (mapInstanceRef.current) { mapInstanceRef.current.remove(); mapInstanceRef.current = null; } };
  }, [data]);

  useEffect(() => {
    if (!data || !mapInstanceRef.current) return;
    const L = window.L; if (!L) return;
    const map = mapInstanceRef.current;
    const events = getFilteredEvents();
    const event = events[currentIdx];
    if (!event || !event.lat || !event.lon) return;
    markersRef.current.forEach(m => map.removeLayer(m));
    markersRef.current = [];
    const riskColor = event.is_high_risk ? '#ef4444' : (event.is_vpn ? '#f59e0b' : '#10b981');
    const marker = L.circleMarker([event.lat, event.lon], { radius: 10, fillColor: riskColor, fillOpacity: 0.9, color: '#fff', weight: 2 }).addTo(map);
    marker.bindPopup(`<div style="font-family:Inter;font-size:12px;min-width:200px"><b>${event.login_city || ''}, ${event.country || ''}</b><br/>$${(event.amount||0).toLocaleString()}<br/>${event.txn_type||event.type}</div>`).openPopup();
    markersRef.current.push(marker);
    if (currentIdx > 0) {
      const prev = events[currentIdx - 1];
      if (prev?.lat && prev?.lon && (prev.lat !== event.lat || prev.lon !== event.lon)) {
        const pm = L.circleMarker([prev.lat, prev.lon], { radius: 6, fillColor: '#6366f1', fillOpacity: 0.5, color: '#6366f1', weight: 1 }).addTo(map);
        markersRef.current.push(pm);
        const path = L.polyline([[prev.lat, prev.lon], [event.lat, event.lon]], { color: riskColor, weight: 2, opacity: 0.7, dashArray: '8, 4' }).addTo(map);
        markersRef.current.push(path);
      }
    }
    map.flyTo([event.lat, event.lon], 5, { duration: 1.5 });
  }, [currentIdx, data, filter]);

  useEffect(() => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (isPlaying && data) {
      const events = getFilteredEvents();
      timerRef.current = setInterval(() => {
        setCurrentIdx(prev => { if (prev >= events.length - 1) { setIsPlaying(false); return prev; } return prev + 1; });
      }, 2000 / speed);
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [isPlaying, speed, data, filter]);

  const getFilteredEvents = useCallback(() => {
    if (!data) return [];
    let events = data.events || [];
    if (filter === 'transactions') events = events.filter(e => e.type === 'TRANSACTION');
    else if (filter === 'large') events = events.filter(e => e.amount > 50000);
    else if (filter === 'international') events = events.filter(e => e.receiver_country && e.country && e.receiver_country !== e.country);
    else if (filter === 'vpn') events = events.filter(e => e.is_vpn);
    else if (filter === 'high-risk') events = events.filter(e => e.is_high_risk);
    return events;
  }, [data, filter]);

  if (loading) return <div style={{padding:'2rem'}}>Loading Journey Replay...</div>;
  if (!data) return <div style={{padding:'2rem'}}>No journey data available.</div>;

  const events = getFilteredEvents();
  const ev = events[currentIdx] || {};
  const summary = data.summary || {};

  return (
    <div>
      <div className="replay-layout">
        <div className="replay-timeline-panel">
          <div className="replay-controls">
            <button onClick={() => { setCurrentIdx(0); setIsPlaying(false); }}>⏮</button>
            <button onClick={() => setCurrentIdx(Math.max(0, currentIdx - 1))}>⏪</button>
            <button onClick={() => setIsPlaying(!isPlaying)} className={isPlaying ? 'active' : ''}>{isPlaying ? '⏸' : '▶'}</button>
            <button onClick={() => setCurrentIdx(Math.min(events.length - 1, currentIdx + 1))}>⏩</button>
            <select value={speed} onChange={e => setSpeed(Number(e.target.value))}>
              <option value={0.5}>0.5×</option><option value={1}>1×</option><option value={2}>2×</option><option value={5}>5×</option>
            </select>
          </div>
          <div className="replay-progress">
            <input type="range" min={0} max={Math.max(events.length - 1, 0)} value={currentIdx} onChange={e => { setCurrentIdx(Number(e.target.value)); setIsPlaying(false); }} />
            <div className="replay-progress-text"><span>Event {currentIdx + 1} / {events.length}</span></div>
          </div>
          <div className="replay-filters">
            {['all','transactions','large','international','vpn','high-risk'].map(f => (
              <span key={f} className={`filter-pill ${filter === f ? 'active' : ''}`} onClick={() => { setFilter(f); setCurrentIdx(0); }}>
                {f === 'all' ? 'All' : f === 'transactions' ? 'Txns' : f === 'large' ? '>$50K' : f === 'international' ? 'Intl' : f === 'vpn' ? 'VPN' : 'High Risk'}
              </span>
            ))}
          </div>
          <div className="replay-events-list">
            {events.map((e, idx) => (
              <div key={idx} className={`replay-event ${idx === currentIdx ? 'active' : ''} ${e.is_high_risk ? 'high-risk' : ''}`}
                onClick={() => { setCurrentIdx(idx); setIsPlaying(false); }}>
                <div className="replay-event-time">{e.timestamp ? new Date(e.timestamp).toLocaleString() : ''}</div>
                <div className="replay-event-title">{e.type === 'ACCOUNT_OPENING' ? '🏦 Opened' : `💸 $${(e.amount||0).toLocaleString()}`}{e.is_vpn && ' 🔒'}{e.is_high_risk && ' ⚠️'}</div>
                <div className="replay-event-detail">{e.login_city || ''}</div>
                {idx === currentIdx && e.ai_observation && <div className="replay-event-ai">🤖 {e.ai_observation}</div>}
              </div>
            ))}
          </div>
        </div>
        <div className="replay-map-panel"><div ref={mapRef} style={{ height: '100%', width: '100%' }} /></div>
        <div className="replay-info-panel">
          <div style={{ display: 'flex', gap: '0.25rem', marginBottom: '0.5rem' }}>
            {['live','devices','network','summary'].map(t => (
              <button key={t} className={`filter-pill ${infoTab === t ? 'active' : ''}`} onClick={() => setInfoTab(t)} style={{ flex: 1, textAlign: 'center' }}>
                {t === 'live' ? '📍' : t === 'devices' ? '📱' : t === 'network' ? '🌐' : '📊'}
              </button>
            ))}
          </div>
          {infoTab === 'live' && (<>
            <div className="info-section"><div className="info-section-title">Customer</div>
              <div className="info-row"><span className="info-row-label">Name</span><span className="info-row-value">{summary.customer_name}</span></div>
              <div className="info-row"><span className="info-row-label">Risk</span><span className={`info-row-value ${summary.overall_risk_rating === 'High' ? 'danger' : 'success'}`}>{summary.overall_risk_rating}</span></div>
            </div>
            <div className="info-section"><div className="info-section-title">Event</div>
              <div className="info-row"><span className="info-row-label">Amount</span><span className="info-row-value">${(ev.amount||0).toLocaleString()}</span></div>
              <div className="info-row"><span className="info-row-label">City</span><span className="info-row-value">{ev.login_city||'-'}</span></div>
              <div className="info-row"><span className="info-row-label">Device</span><span className="info-row-value">{ev.device_id?.substring(0,15)||'-'}</span></div>
              <div className="info-row"><span className="info-row-label">IP</span><span className="info-row-value">{ev.ip_address||'-'}</span></div>
              <div className="info-row"><span className="info-row-label">VPN</span><span className={`info-row-value ${ev.is_vpn ? 'danger' : 'success'}`}>{ev.is_vpn ? '⚠ YES' : '✓ No'}</span></div>
            </div>
            {ev.ai_observation && <div className="info-section"><div className="info-section-title">🤖 AI</div><div style={{fontSize:'0.78rem',color:'var(--warning)',lineHeight:1.4}}>{ev.ai_observation}</div></div>}
          </>)}
          {infoTab === 'devices' && <div className="info-section"><div className="info-section-title">Devices ({data.devices?.length||0})</div>
            {(data.devices||[]).map((d,i)=>(<div key={i} className="device-card"><div className="device-card-header"><span className="device-card-name">{d.device_type} • {d.device_id?.substring(0,15)}</span><span className={`badge ${d.risk}`}>{d.risk}</span></div><div className="info-row"><span className="info-row-label">Browser</span><span className="info-row-value">{d.browser}</span></div><div className="info-row"><span className="info-row-label">Txns</span><span className="info-row-value">{d.txn_count}</span></div></div>))}
          </div>}
          {infoTab === 'network' && <div className="info-section"><div className="info-section-title">Networks ({data.networks?.length||0})</div>
            {(data.networks||[]).map((n,i)=>(<div key={i} className="device-card"><div className="device-card-header"><span className="device-card-name">{n.ip_address}</span>{n.is_vpn && <span className="badge high">VPN</span>}</div><div className="info-row"><span className="info-row-label">ISP</span><span className="info-row-value">{n.isp}</span></div><div className="info-row"><span className="info-row-label">City</span><span className="info-row-value">{n.city}</span></div></div>))}
          </div>}
          {infoTab === 'summary' && <div className="info-section"><div className="info-section-title">Summary</div>
            <div className="info-row"><span className="info-row-label">Total Txns</span><span className="info-row-value">{summary.total_transactions}</span></div>
            <div className="info-row"><span className="info-row-label">Countries</span><span className="info-row-value">{summary.countries_visited?.length||0}</span></div>
            <div className="info-row"><span className="info-row-label">Amount</span><span className="info-row-value">${(summary.total_amount_transferred||0).toLocaleString()}</span></div>
            <div className="info-row"><span className="info-row-label">VPN Sessions</span><span className={`info-row-value ${summary.vpn_sessions>0?'danger':'success'}`}>{summary.vpn_sessions}</span></div>
          </div>}
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════
   CASE DETAILS (with full KYC tab + review workflow)
   ═══════════════════════════════════════════════════════ */
function CaseDetails({ caseId, onBack }) {
  const [details, setDetails] = useState(null);
  const [journey, setJourney] = useState(null);
  const [report, setReport] = useState(null);
  const [graphHtml, setGraphHtml] = useState(null);
  const [loadingReport, setLoadingReport] = useState(false);
  const [dispositionReason, setDispositionReason] = useState("");
  const [reviewerConfidence, setReviewerConfidence] = useState(80);
  const [activeTab, setActiveTab] = useState('investigation');
  const [rightTab, setRightTab] = useState('journey');
  const [kycData, setKycData] = useState(null);
  const reviewStartRef = useRef(Date.now());

  useEffect(() => {
    fetchCaseDetails(caseId).then(data => setDetails(data));
    fetchJourney(caseId).then(data => setJourney(data)).catch(() => {});
    fetchGraph(caseId).then(data => setGraphHtml(data.html)).catch(() => {});
    fetchKyc(caseId).then(data => setKycData(data)).catch(() => {});
    reviewStartRef.current = Date.now();
  }, [caseId]);

  const handleGenerateReport = async () => {
    setLoadingReport(true);
    try { const res = await generateReport(caseId); setReport(res.structured_data); } catch (err) { console.error(err); }
    setLoadingReport(false);
  };

  const handleDisposition = async (action) => {
    if (!dispositionReason) return alert("Please provide reasoning for the audit trail.");
    const timeMs = Date.now() - reviewStartRef.current;
    try {
      await updateDisposition(caseId, action, dispositionReason, reviewerConfidence, timeMs);
      alert(`Case ${action} successfully. Audit log and trust metrics updated.`);
      onBack();
    } catch (e) { console.error(e); }
  };

  const handleExport = () => {
    const pin = prompt('Set a 4-digit PIN to protect the PDF report (leave blank for no PIN):');
    if (pin !== null && pin !== '' && (pin.length < 4 || !/^\d+$/.test(pin))) {
      alert('PIN must be at least 4 digits (numbers only).');
      return;
    }
    const base = import.meta.env.VITE_API_BASE || `http://${window.location.hostname}:8000`;
    const url = pin ? `${base}/reports/${caseId}/download?pin=${encodeURIComponent(pin)}` : `${base}/reports/${caseId}/download`;
    window.open(url, '_blank');
  };

  if (!details) return <div>Loading case details...</div>;
  const c = details.case;
  let rulesArray = [];
  try {
    const rf = c.rule_flags ? JSON.parse(c.rule_flags) : [];
    rulesArray = Array.isArray(rf) ? rf : Object.entries(rf).map(([rule, info]) => ({ rule, ...info }));
  } catch(e) {}

  return (
    <div>
      <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',flexWrap:'wrap',gap:'1rem'}}>
        <button className="back-btn" onClick={onBack}>← Back to Cases</button>
        <div style={{display:'flex',gap:'0.5rem',alignItems:'center',flexWrap:'wrap'}}>
          <input type="text" placeholder="Reviewer notes..." style={{padding:'0.5rem',background:'var(--bg-tertiary)',color:'var(--text-primary)',border:'1px solid var(--border-color)',borderRadius:'4px',minWidth:'200px'}}
            value={dispositionReason} onChange={e => setDispositionReason(e.target.value)} />
          <select value={reviewerConfidence} onChange={e => setReviewerConfidence(Number(e.target.value))}
            style={{padding:'0.5rem',background:'var(--bg-tertiary)',color:'var(--text-primary)',border:'1px solid var(--border-color)',borderRadius:'4px'}}>
            <option value={90}>90% Conf</option><option value={80}>80% Conf</option><option value={70}>70% Conf</option>
            <option value={60}>60% Conf</option><option value={50}>50% Conf</option>
          </select>
          <button className="btn btn-primary" onClick={() => handleDisposition("ESCALATED")}>🚨 Escalate</button>
          <button className="btn btn-secondary" onClick={() => handleDisposition("MONITORING")}>👁 Monitor</button>
          <button className="btn btn-secondary" onClick={() => handleDisposition("REQUEST_DOCS")}>📄 Request Docs</button>
          <button className="btn btn-secondary" style={{color:'var(--danger)'}} onClick={() => handleDisposition("CLOSED")}>✓ Close</button>
        </div>
      </div>

      <div className="details-header">
        <div>
          <h1>{c.case_id}</h1>
          <p style={{color:'var(--text-tertiary)',marginTop:'0.25rem'}}>Account: {c.account_id} • Queue: {c.assigned_queue} • Status: <span className={`badge ${c.status==='ESCALATED'?'high':c.status==='MONITORING'?'medium':''}`}>{c.status}</span></p>
        </div>
        <div style={{display:'flex',gap:'1rem',alignItems:'center'}}>
          <button className="btn btn-secondary" onClick={handleExport}>📥 Export</button>
          <div className="stat-item" style={{alignItems:'center'}}><span className="stat-label">Anomaly</span><span className="stat-value" style={{fontSize:'1.5rem'}}>{c.anomaly_score?.toFixed(3)}</span></div>
          <div className="stat-item" style={{alignItems:'center'}}><span className="stat-label">Risk</span><span className="stat-value" style={{fontSize:'1.5rem'}}>{(c.risk_score * 100).toFixed(1)}%</span></div>
          <Badge riskScore={c.risk_score} />
        </div>
      </div>

      <div className="tab-bar">
        <button className={`tab-btn ${activeTab === 'investigation' ? 'active' : ''}`} onClick={() => setActiveTab('investigation')}>🔍 Investigation</button>
        <button className={`tab-btn ${activeTab === 'kyc' ? 'active' : ''}`} onClick={() => setActiveTab('kyc')}>📋 KYC & Documents</button>
        <button className={`tab-btn ${activeTab === 'replay' ? 'active' : ''}`} onClick={() => setActiveTab('replay')}>🌍 Journey Replay</button>
        <button className={`tab-btn ${activeTab === 'adversarial' ? 'active' : ''}`} onClick={() => setActiveTab('adversarial')}>⚖️ Adversarial Forensics</button>
        <button className={`tab-btn ${activeTab === 'history' ? 'active' : ''}`} onClick={() => setActiveTab('history')}>📜 Review History</button>
      </div>

      {activeTab === 'investigation' && (
        <div className="details-grid">
          <div className="left-col" style={{display:'flex',flexDirection:'column',gap:'2rem'}}>
            <div className="glass-panel details-panel">
              <h3 className="panel-header">Rule Violations & Red-Flag Taxonomy</h3>
              <div className="rules-list">
                {rulesArray.length > 0 ? rulesArray.map((info, idx) => (
                  <div key={idx} className="rule-item">
                    <div style={{fontWeight:600,color:'var(--text-primary)'}}>{(info.rule||'').replace(/_/g,' ').toUpperCase()}</div>
                    <div style={{fontSize:'0.9rem',color:'var(--text-secondary)'}}>Severity: {info.severity||'High'} • {info.reason}</div>
                  </div>
                )) : <div style={{color:'var(--text-tertiary)'}}>No rules flagged.</div>}
              </div>
            </div>
            <div className="glass-panel details-panel">
              <h3 className="panel-header">Transaction Graph</h3>
              {graphHtml ? <iframe style={{width:'100%',height:'400px',background:'#12121a',border:'none',borderRadius:'8px'}} srcDoc={graphHtml} title="Graph" /> : <div>Loading graph...</div>}
            </div>
            <div className="glass-panel details-panel">
              <h3 className="panel-header">AI Compliance Report</h3>
              {!report && !details.report ? (
                <div>
                  <p style={{color:'var(--text-secondary)',marginBottom:'1rem'}}>Generate an AI investigation report using Gemma.</p>
                  <button className="btn btn-primary" onClick={handleGenerateReport} disabled={loadingReport}>
                    {loadingReport ? '⏳ Generating...' : '🤖 Generate AI Report'}
                  </button>
                </div>
              ) : (
                <div className="report-content">
                  <strong>Confidence:</strong> <span style={{color:'var(--accent-primary)',fontSize:'1.2rem'}}>{(((report||details.report).confidence_score||0)*100).toFixed(0)}%</span><br/><br/>
                  <strong>What Happened:</strong><br/>{(report||details.report).what_happened}<br/><br/>
                  <strong>Why it Matters:</strong><br/>{(report||details.report).why_it_matters}<br/><br/>
                  <strong>Recommended Action:</strong><br/>{(report||details.report).recommended_action}<br/><br/>
                  <strong>Missing Info:</strong><br/><span style={{color:'var(--text-tertiary)'}}>{(report||details.report).missing_information_needed||'None.'}</span>

                  {(report||details.report).feature_attributions && Object.keys((report||details.report).feature_attributions).length > 0 && (
                    <div style={{marginTop:'1.5rem',borderTop:'1px solid var(--border-color)',paddingTop:'1.5rem'}}>
                      <strong style={{display:'block',marginBottom:'0.75rem',color:'var(--accent-primary)'}}>⚖️ Explainable AI (XAI) Feature Attribution:</strong>
                      <div style={{display:'flex',flexDirection:'column',gap:'0.75rem'}}>
                        {Object.entries((report||details.report).feature_attributions).map(([rule, val]) => (
                          <div key={rule}>
                            <div style={{display:'flex',justifyContent:'space-between',fontSize:'0.85rem',marginBottom:'0.25rem'}}>
                              <span style={{fontWeight:500,color:'var(--text-secondary)'}}>{rule.replace(/_/g,' ').toUpperCase()}</span>
                              <span style={{fontWeight:600,color:'var(--text-primary)'}}>{Number(val).toFixed(2)}</span>
                            </div>
                            <div style={{width:'100%',background:'var(--bg-tertiary)',height:'8px',borderRadius:'4px',overflow:'hidden',border:'1px solid var(--border-color)'}}>
                              <div style={{width:`${Math.min(100, Number(val) * 100)}%`,background:'var(--accent-primary)',height:'100%',borderRadius:'4px'}} />
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
          <div className="right-col">
            <div className="glass-panel details-panel" style={{height:'100%', display:'flex', flexDirection:'column'}}>
              <div style={{ display: 'flex', borderBottom: '1px solid var(--border-color)' }}>
                <button 
                  className={`tab-btn ${rightTab === 'journey' ? 'active' : ''}`} 
                  onClick={() => setRightTab('journey')}
                  style={{ flex: 1, padding: '1rem', borderBottom: rightTab === 'journey' ? '2px solid var(--accent-primary)' : 'none', background: 'transparent', color: rightTab === 'journey' ? 'var(--text-primary)' : 'var(--text-secondary)' }}
                >
                  Transaction Journey
                </button>
                <button 
                  className={`tab-btn ${rightTab === 'chat' ? 'active' : ''}`} 
                  onClick={() => setRightTab('chat')}
                  style={{ flex: 1, padding: '1rem', borderBottom: rightTab === 'chat' ? '2px solid var(--accent-primary)' : 'none', background: 'transparent', color: rightTab === 'chat' ? 'var(--text-primary)' : 'var(--text-secondary)' }}
                >
                  AI Copilot
                </button>
              </div>

              <div style={{ flex: 1, overflow: 'hidden' }}>
                {rightTab === 'journey' ? (
                  <div style={{ height: '100%', overflowY: 'auto' }}>
                    {journey ? (
                      <div className="journey-timeline">
                        {journey.events.map((ev, idx) => (
                          <div key={idx} className={`journey-item ${ev.is_high_risk ? 'high-risk' : ''}`}>
                            <div className="journey-time">{new Date(ev.timestamp).toLocaleString()}</div>
                            <div className="journey-type">{ev.type} {ev.amount ? ` - $${ev.amount.toFixed(2)}` : ''}</div>
                            <div className="journey-desc">{ev.details}</div>
                          </div>
                        ))}
                      </div>
                    ) : <div style={{padding:'1rem'}}>Loading journey...</div>}
                  </div>
                ) : (
                  <ChatAssistant caseId={caseId} />
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'kyc' && kycData && (
        <div style={{marginTop:'1rem',display:'flex',flexDirection:'column',gap:'1.5rem'}}>
          {kycData.sanctions_check && kycData.sanctions_check.has_match && (
            <div className="glass-panel" style={{
              borderLeft: '4px solid var(--danger)',
              padding: '1.5rem',
              background: 'rgba(239, 68, 68, 0.05)',
              borderRadius: '6px'
            }}>
              <h3 style={{ margin: 0, color: 'var(--danger)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                ⚠️ Specially Designated National (SDN) Sanctions Flag
              </h3>
              <p style={{ margin: '0.5rem 0', fontSize: '0.95rem', color: 'var(--text-secondary)' }}>
                Fuzzy match detected customer name <strong style={{color:'var(--text-primary)'}}>"{kycData.kyc?.name}"</strong> against sanctioned entity 
                <strong style={{color:'var(--text-primary)'}}> "{kycData.sanctions_check.matched_sdn}"</strong> (Similarity Score: <strong>{(kycData.sanctions_check.similarity_score * 100).toFixed(0)}%</strong>).
              </p>
              
              <div style={{
                margin: '1rem 0',
                padding: '1rem',
                background: 'rgba(255, 255, 255, 0.03)',
                borderRadius: '4px',
                border: '1px solid var(--border-color)',
                fontSize: '0.9rem'
              }}>
                <div style={{display:'grid',gridTemplateColumns:'150px 1fr',gap:'0.25rem'}}>
                  <span style={{color:'var(--text-tertiary)'}}>SDN ID:</span>
                  <span style={{fontWeight:600}}>{kycData.sanctions_check.sdn_number}</span>
                  <span style={{color:'var(--text-tertiary)'}}>SDN Jurisdiction:</span>
                  <span>{kycData.sanctions_check.sdn_country}</span>
                  <span style={{color:'var(--text-tertiary)'}}>Reason List:</span>
                  <span style={{color:'var(--text-secondary)'}}>{kycData.sanctions_check.sdn_reason}</span>
                </div>
              </div>

              <div style={{ fontSize: '0.9rem', borderTop: '1px solid var(--border-color)', paddingTop: '0.75rem' }}>
                <strong style={{ color: 'var(--danger)' }}>🤖 Google Gemma Verification Assessment:</strong>
                <p style={{ margin: '0.25rem 0 0 0', fontStyle: 'italic', color: 'var(--text-secondary)', lineHeight: '1.4' }}>
                  "{kycData.sanctions_check.gemma_assessment}"
                </p>
                <div style={{ marginTop: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Recommended Immediate Action:</span>
                  <span className={`badge ${kycData.sanctions_check.recommended_action === 'BLOCK' ? 'high' : 'medium'}`}>
                    {kycData.sanctions_check.recommended_action}
                  </span>
                </div>
              </div>
            </div>
          )}

          <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:'1.5rem'}}>
          <div className="glass-panel details-panel">
            <h3 className="panel-header">KYC Profile</h3>
            <div style={{display:'grid',gap:'0.5rem'}}>
              <div className="info-row"><span className="info-row-label">Name</span><span className="info-row-value">{kycData.kyc?.name||'-'}</span></div>
              <div className="info-row"><span className="info-row-label">Date of Birth</span><span className="info-row-value">{kycData.kyc?.dob||'-'}</span></div>
              <div className="info-row"><span className="info-row-label">Address</span><span className="info-row-value">{kycData.kyc?.address||'-'}</span></div>
              <div className="info-row"><span className="info-row-label">ID Number</span><span className="info-row-value">{kycData.kyc?.id_number||'-'}</span></div>
              <div className="info-row"><span className="info-row-label">Employer</span><span className="info-row-value">{kycData.kyc?.employer||'-'}</span></div>
              <div className="info-row"><span className="info-row-label">Purpose</span><span className="info-row-value">{kycData.kyc?.declared_purpose||'-'}</span></div>
              <div className="info-row"><span className="info-row-label">Declared Income</span><span className="info-row-value">${(kycData.kyc?.declared_income||0).toLocaleString()}</span></div>
              <div className="info-row"><span className="info-row-label">OCR Confidence</span><span className="info-row-value">{((kycData.kyc?.ocr_confidence||0)*100).toFixed(0)}%</span></div>
            </div>
          </div>
          <div className="glass-panel details-panel">
            <h3 className="panel-header">Verification Status</h3>
            <div style={{display:'grid',gap:'0.75rem'}}>
              <div className="info-row"><span className="info-row-label">KYC Status</span><span className={`info-row-value ${kycData.verification_status==='VERIFIED'?'success':kycData.verification_status==='PARTIAL'?'warning':'danger'}`}>{kycData.verification_status}</span></div>
              <div className="info-row"><span className="info-row-label">KYC Risk</span><span className={`info-row-value ${kycData.kyc_risk==='HIGH'?'danger':kycData.kyc_risk==='MEDIUM'?'warning':'success'}`}>{kycData.kyc_risk}</span></div>
              <div className="info-row"><span className="info-row-label">Documents Found</span><span className="info-row-value">{kycData.total_documents}</span></div>
              <div className="info-row"><span className="info-row-label">Types</span><span className="info-row-value">{kycData.document_types_found?.join(', ')||'None'}</span></div>
              {kycData.missing_documents?.length > 0 && (
                <div className="info-row"><span className="info-row-label" style={{color:'var(--danger)'}}>Missing</span><span className="info-row-value danger">{kycData.missing_documents.join(', ')}</span></div>
              )}
            </div>
          </div>
          <div className="glass-panel details-panel" style={{gridColumn:'span 2'}}>
            <h3 className="panel-header">OCR Documents ({kycData.documents?.length||0})</h3>
            <div style={{maxHeight:'400px',overflow:'auto'}}>
              <table style={{width:'100%',textAlign:'left',borderCollapse:'collapse'}}>
                <thead><tr style={{borderBottom:'1px solid var(--border-color)'}}>
                  <th style={{padding:'0.5rem'}}>Doc ID</th><th style={{padding:'0.5rem'}}>Type</th><th style={{padding:'0.5rem'}}>File</th>
                  <th style={{padding:'0.5rem'}}>Confidence</th><th style={{padding:'0.5rem'}}>Preview</th>
                </tr></thead>
                <tbody>
                  {(kycData.documents||[]).map((d,i)=>(
                    <tr key={i} style={{borderBottom:'1px solid var(--border-color)',color:'var(--text-secondary)'}}>
                      <td style={{padding:'0.5rem'}}>{d.doc_id}</td>
                      <td style={{padding:'0.5rem'}}><span className={`badge ${d.doc_type==='INVOICE'?'medium':'low'}`}>{d.doc_type}</span></td>
                      <td style={{padding:'0.5rem'}}>{d.file_name}</td>
                      <td style={{padding:'0.5rem'}}>{((d.confidence||0)*100).toFixed(0)}%</td>
                      <td style={{padding:'0.5rem',maxWidth:'300px',overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{(d.extracted_text||'').substring(0,80)}...</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
      )}

      {activeTab === 'replay' && <JourneyReplayView caseId={caseId} />}

      {activeTab === 'adversarial' && <AdversarialView caseId={caseId} />}

      {activeTab === 'history' && (
        <div className="glass-panel details-panel" style={{marginTop:'1rem'}}>
          <h3 className="panel-header">Review History</h3>
          {(details.review_history||[]).length === 0 ? <p style={{color:'var(--text-tertiary)'}}>No review actions yet.</p> : (
            <table style={{width:'100%',textAlign:'left',borderCollapse:'collapse'}}>
              <thead><tr style={{borderBottom:'1px solid var(--border-color)'}}>
                <th style={{padding:'0.5rem'}}>Time</th><th style={{padding:'0.5rem'}}>Reviewer</th><th style={{padding:'0.5rem'}}>Action</th>
                <th style={{padding:'0.5rem'}}>AI Rec</th><th style={{padding:'0.5rem'}}>Followed AI</th><th style={{padding:'0.5rem'}}>Confidence</th><th style={{padding:'0.5rem'}}>Notes</th>
              </tr></thead>
              <tbody>
                {(details.review_history||[]).map((h,i)=>(
                  <tr key={i} style={{borderBottom:'1px solid var(--border-color)',color:'var(--text-secondary)'}}>
                    <td style={{padding:'0.5rem'}}>{h.timestamp ? new Date(h.timestamp).toLocaleString() : '-'}</td>
                    <td style={{padding:'0.5rem'}}>{h.reviewer_id}</td>
                    <td style={{padding:'0.5rem'}}><span className={`badge ${h.action==='ESCALATED'?'high':h.action==='CLOSED'?'low':'medium'}`}>{h.action}</span></td>
                    <td style={{padding:'0.5rem'}}>{h.ai_recommendation}</td>
                    <td style={{padding:'0.5rem'}}>{h.followed_ai ? '✓ Yes' : '✗ No'}</td>
                    <td style={{padding:'0.5rem'}}>{h.reviewer_confidence}%</td>
                    <td style={{padding:'0.5rem'}}>{h.notes}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════
   AUDIT LOGS VIEW
   ═══════════════════════════════════════════════════════ */
function AuditLogsView() {
  const [logs, setLogs] = useState([]);
  const [search, setSearch] = useState('');
  const [filterAction, setFilterAction] = useState('');

  const loadLogs = () => fetchAuditLogs(search, filterAction).then(data => setLogs(data.events || []));
  useEffect(() => { loadLogs(); }, []);

  const handleSearch = () => loadLogs();
  const handleExport = () => {
    const blob = new Blob([JSON.stringify(logs, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = 'audit_export.json'; a.click();
  };

  return (
    <div className="glass-panel" style={{padding:'2rem'}}>
      <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:'1.5rem',flexWrap:'wrap',gap:'1rem'}}>
        <h2 style={{margin:0}}>Audit Trail ({logs.length} events)</h2>
        <div style={{display:'flex',gap:'0.5rem',alignItems:'center'}}>
          <input type="text" placeholder="Search logs..." value={search} onChange={e=>setSearch(e.target.value)} onKeyDown={e=>e.key==='Enter'&&handleSearch()}
            style={{padding:'0.5rem',background:'var(--bg-tertiary)',color:'var(--text-primary)',border:'1px solid var(--border-color)',borderRadius:'4px'}} />
          <select value={filterAction} onChange={e=>{setFilterAction(e.target.value);setTimeout(loadLogs,100);}}
            style={{padding:'0.5rem',background:'var(--bg-tertiary)',color:'var(--text-primary)',border:'1px solid var(--border-color)',borderRadius:'4px'}}>
            <option value="">All Actions</option>
            <option value="ESCALATED">Escalated</option>
            <option value="MONITORING">Monitoring</option>
            <option value="CLOSED">Closed</option>
            <option value="REQUEST_DOCS">Request Docs</option>
          </select>
          <button className="btn btn-secondary" onClick={handleSearch}>🔍</button>
          <button className="btn btn-secondary" onClick={handleExport}>📥 Export</button>
        </div>
      </div>
      <div style={{maxHeight:'70vh',overflow:'auto'}}>
        <table style={{width:'100%',textAlign:'left',borderCollapse:'collapse'}}>
          <thead><tr style={{borderBottom:'2px solid var(--border-color)',position:'sticky',top:0,background:'var(--bg-secondary)'}}>
            <th style={{padding:'0.75rem'}}>Timestamp</th>
            <th style={{padding:'0.75rem'}}>Case ID</th>
            <th style={{padding:'0.75rem'}}>Reviewer</th>
            <th style={{padding:'0.75rem'}}>Action</th>
            <th style={{padding:'0.75rem'}}>Old → New</th>
            <th style={{padding:'0.75rem'}}>AI Rec</th>
            <th style={{padding:'0.75rem'}}>Risk</th>
            <th style={{padding:'0.75rem'}}>Notes</th>
          </tr></thead>
          <tbody>
            {logs.map((l, i) => (
              <tr key={i} style={{borderBottom:'1px solid var(--border-color)',color:'var(--text-secondary)'}}>
                <td style={{padding:'0.5rem',fontSize:'0.85rem'}}>{l.event_time ? new Date(l.event_time).toLocaleString() : '-'}</td>
                <td style={{padding:'0.5rem',fontFamily:'monospace',fontSize:'0.8rem'}}>{l.case_id}</td>
                <td style={{padding:'0.5rem'}}>{l.reviewer_id||'-'}</td>
                <td style={{padding:'0.5rem'}}><span className={`badge ${l.reviewer_action?.includes('ESCALATED')?'high':l.reviewer_action?.includes('CLOSED')?'low':'medium'}`}>{l.reviewer_action}</span></td>
                <td style={{padding:'0.5rem',fontSize:'0.85rem'}}>{l.old_status||'—'} → {l.new_status||'—'}</td>
                <td style={{padding:'0.5rem',fontSize:'0.85rem'}}>{l.ai_recommendation||'-'}</td>
                <td style={{padding:'0.5rem'}}>{l.risk_score ? `${(l.risk_score*100).toFixed(0)}%` : '-'}</td>
                <td style={{padding:'0.5rem',maxWidth:'200px',overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{l.notes||'-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════
   STREAMING MONITOR VIEW
   ═══════════════════════════════════════════════════════ */
function StreamingMonitorView() {
  const [stats, setStats] = useState(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    fetchStreamingStats().then(setStats);
    const interval = setInterval(() => {
      fetchStreamingStats().then(setStats);
      setTick(t => t + 1);
    }, 8000);
    return () => clearInterval(interval);
  }, []);

  if (!stats) return <div>Loading streaming data...</div>;

  const counters = [
    { label: 'Total Transactions', value: stats.total_transactions?.toLocaleString(), icon: '💰', color: 'var(--accent-primary)' },
    { label: 'Total Cases', value: stats.total_cases, icon: '📁', color: 'var(--text-secondary)' },
    { label: 'High Risk Alerts', value: stats.high_risk_alerts, icon: '🚨', color: 'var(--danger)' },
    { label: 'Under Investigation', value: stats.under_investigation, icon: '🔍', color: 'var(--warning)' },
    { label: 'Escalated', value: stats.escalated_cases, icon: '⬆️', color: '#ef4444' },
    { label: 'New Cases', value: stats.new_cases, icon: '🆕', color: 'var(--accent-primary)' },
    { label: 'Closed', value: stats.closed_cases, icon: '✅', color: 'var(--success)' },
  ];

  return (
    <div style={{display:'flex',flexDirection:'column',gap:'1.5rem'}}>
      {/* Counter Cards */}
      <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit, minmax(180px, 1fr))',gap:'1rem'}}>
        {counters.map((c, i) => (
          <div key={i} className="glass-panel" style={{padding:'1.25rem',textAlign:'center'}}>
            <div style={{fontSize:'2rem',marginBottom:'0.5rem'}}>{c.icon}</div>
            <div style={{fontSize:'2rem',fontWeight:700,color:c.color}}>{c.value}</div>
            <div style={{fontSize:'0.85rem',color:'var(--text-tertiary)',marginTop:'0.25rem'}}>{c.label}</div>
          </div>
        ))}
      </div>

      {/* Risk Distribution */}
      <div className="glass-panel" style={{padding:'1.5rem'}}>
        <h3 style={{marginBottom:'1rem'}}>Risk Distribution</h3>
        <div style={{display:'flex',gap:'2rem',alignItems:'end'}}>
          {stats.risk_distribution && Object.entries(stats.risk_distribution).map(([level, count]) => (
            <div key={level} style={{flex:1,textAlign:'center'}}>
              <div style={{background: level==='high'?'var(--danger)':level==='medium'?'var(--warning)':'var(--success)',
                height: `${Math.max(20, Math.min(200, count / (stats.total_cases || 1) * 300))}px`,
                borderRadius:'8px 8px 0 0',transition:'height 0.5s ease',marginBottom:'0.5rem'}} />
              <div style={{fontWeight:700,fontSize:'1.2rem'}}>{count}</div>
              <div style={{fontSize:'0.8rem',color:'var(--text-tertiary)',textTransform:'capitalize'}}>{level}</div>
            </div>
          ))}
        </div>
      </div>

      <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:'1.5rem'}}>
        {/* Live Event Feed */}
        <div className="glass-panel" style={{padding:'1.5rem'}}>
          <h3 style={{marginBottom:'1rem'}}>🔴 Live Activity Feed <span style={{fontSize:'0.7rem',color:'var(--success)',animation:'pulse 2s infinite'}}>● LIVE</span></h3>
          <div style={{maxHeight:'400px',overflow:'auto'}}>
            {(stats.recent_activity||[]).map((a, i) => (
              <div key={i} style={{padding:'0.75rem',borderBottom:'1px solid var(--border-color)',display:'flex',justifyContent:'space-between',alignItems:'center'}}>
                <div>
                  <div style={{fontSize:'0.85rem',fontWeight:600,color:'var(--text-primary)'}}>{a.reviewer_action}</div>
                  <div style={{fontSize:'0.75rem',color:'var(--text-tertiary)'}}>{a.case_id} • {a.reviewer_id || 'System'}</div>
                </div>
                <div style={{fontSize:'0.7rem',color:'var(--text-tertiary)'}}>{a.event_time ? new Date(a.event_time).toLocaleTimeString() : ''}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Status Distribution */}
        <div className="glass-panel" style={{padding:'1.5rem'}}>
          <h3 style={{marginBottom:'1rem'}}>Case Status Overview</h3>
          <div style={{display:'grid',gap:'0.75rem'}}>
            {stats.status_distribution && Object.entries(stats.status_distribution).map(([status, count]) => (
              <div key={status} style={{display:'flex',alignItems:'center',gap:'1rem'}}>
                <span className={`badge ${status==='ESCALATED'?'high':status==='MONITORING'?'medium':status==='CLOSED'?'low':''}`} style={{minWidth:'120px',textAlign:'center'}}>{status}</span>
                <div style={{flex:1,background:'var(--bg-tertiary)',borderRadius:'4px',height:'24px',overflow:'hidden'}}>
                  <div style={{width:`${(count/(stats.total_cases||1))*100}%`,height:'100%',background:status==='ESCALATED'?'var(--danger)':status==='MONITORING'?'var(--warning)':'var(--accent-primary)',borderRadius:'4px',transition:'width 0.5s ease'}} />
                </div>
                <span style={{fontWeight:700,minWidth:'40px'}}>{count}</span>
              </div>
            ))}
          </div>
          <div style={{marginTop:'1.5rem',padding:'1rem',background:'var(--bg-tertiary)',borderRadius:'8px',display:'flex',justifyContent:'space-between'}}>
            <div><span style={{fontSize:'0.8rem',color:'var(--text-tertiary)'}}>AI Status</span><br/><span style={{fontWeight:700,color:'var(--success)'}}>{stats.ai_analysis_status}</span></div>
            <div><span style={{fontSize:'0.8rem',color:'var(--text-tertiary)'}}>Doc Arrivals</span><br/><span style={{fontWeight:700}}>{stats.total_documents_arrived}</span></div>
            <div><span style={{fontSize:'0.8rem',color:'var(--text-tertiary)'}}>Late</span><br/><span style={{fontWeight:700,color:'var(--danger)'}}>{stats.late_arrivals}</span></div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════
   TRUST CALIBRATION VIEW
   ═══════════════════════════════════════════════════════ */
function isDecisionEqual(aiRec, userDec) {
  if (!aiRec || !userDec) return false;
  const a = aiRec.toUpperCase();
  const u = userDec.toUpperCase();
  const getBase = (s) => {
    if (s.endsWith('ING')) return s.slice(0, -3);
    if (s.endsWith('ED')) return s.slice(0, -2);
    if (s.endsWith('ES')) return s.slice(0, -2);
    if (s.endsWith('S') && !s.endsWith('CS')) return s.slice(0, -1);
    return s;
  };
  return getBase(a) === getBase(u) || a.includes(u) || u.includes(a);
}

function TrustCalibrationView() {
  const [data, setData] = useState(null);
  useEffect(() => { fetchTrustDashboard().then(setData); }, []);
  if (!data) return <div>Loading trust calibration...</div>;
  const d = data.dashboard || {};

  return (
    <div style={{display:'flex',flexDirection:'column',gap:'1.5rem'}}>
      {/* Top Metrics */}
      <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit, minmax(200px, 1fr))',gap:'1rem'}}>
        {[
          { label: 'Trust Score', value: `${((d.trust_score||0)*100).toFixed(0)}%`, color: d.trust_score > 0.7 ? 'var(--success)' : 'var(--warning)' },
          { label: 'AI Reliance Rate', value: `${((d.ai_reliance_rate||0)*100).toFixed(0)}%`, color: d.ai_reliance_rate > 0.95 ? 'var(--danger)' : 'var(--accent-primary)' },
          { label: 'Avg Decision Time', value: `${((d.avg_decision_time_ms||0)/1000).toFixed(1)}s`, color: 'var(--text-primary)' },
          { label: 'Cognitive Load', value: `${((d.avg_cognitive_load||0)*100).toFixed(0)}%`, color: d.avg_cognitive_load > 0.7 ? 'var(--danger)' : 'var(--success)' },
          { label: 'Total Reviews', value: d.total_interactions || 0, color: 'var(--accent-primary)' },
          { label: 'AI Agreements', value: d.ai_agreement_count || 0, color: 'var(--success)' },
        ].map((m, i) => (
          <div key={i} className="glass-panel" style={{padding:'1.25rem',textAlign:'center'}}>
            <div style={{fontSize:'2rem',fontWeight:700,color:m.color}}>{m.value}</div>
            <div style={{fontSize:'0.85rem',color:'var(--text-tertiary)',marginTop:'0.25rem'}}>{m.label}</div>
          </div>
        ))}
      </div>

      <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:'1.5rem'}}>
        {/* Reviewer Performance */}
        <div className="glass-panel" style={{padding:'1.5rem'}}>
          <h3 style={{marginBottom:'1rem'}}>Reviewer Performance</h3>
          {(d.reviewer_performance||[]).length === 0 ? <p style={{color:'var(--text-tertiary)'}}>No reviewer data yet. Complete case reviews to populate metrics.</p> : (
            <table style={{width:'100%',borderCollapse:'collapse'}}>
              <thead><tr style={{borderBottom:'1px solid var(--border-color)'}}>
                <th style={{padding:'0.5rem',textAlign:'left'}}>Reviewer</th>
                <th style={{padding:'0.5rem'}}>Reviews</th>
                <th style={{padding:'0.5rem'}}>AI Agree</th>
                <th style={{padding:'0.5rem'}}>Avg Time</th>
                <th style={{padding:'0.5rem'}}>Confidence</th>
              </tr></thead>
              <tbody>
                {(d.reviewer_performance||[]).map((r,i)=>(
                  <tr key={i} style={{borderBottom:'1px solid var(--border-color)',color:'var(--text-secondary)'}}>
                    <td style={{padding:'0.5rem',fontWeight:600}}>{r.reviewer_id}</td>
                    <td style={{padding:'0.5rem',textAlign:'center'}}>{r.total_reviews}</td>
                    <td style={{padding:'0.5rem',textAlign:'center'}}><span className={`badge ${r.ai_agreement_rate>0.95?'high':r.ai_agreement_rate>0.7?'medium':'low'}`}>{(r.ai_agreement_rate*100).toFixed(0)}%</span></td>
                    <td style={{padding:'0.5rem',textAlign:'center'}}>{(r.avg_decision_time_ms/1000).toFixed(1)}s</td>
                    <td style={{padding:'0.5rem',textAlign:'center'}}>{r.avg_confidence?.toFixed(0)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Recent Interactions */}
        <div className="glass-panel" style={{padding:'1.5rem'}}>
          <h3 style={{marginBottom:'1rem'}}>A/B Test Interactions</h3>
          <div style={{maxHeight:'400px',overflow:'auto'}}>
            {(d.recent_interactions||[]).length === 0 ? <p style={{color:'var(--text-tertiary)'}}>No A/B test data yet.</p> : (
              (d.recent_interactions||[]).map((r,i)=>(
                <div key={i} style={{padding:'0.75rem',borderBottom:'1px solid var(--border-color)'}}>
                  <div style={{display:'flex',justifyContent:'space-between'}}>
                    <span style={{fontWeight:600,fontSize:'0.85rem'}}>{r.case_id}</span>
                    <span style={{fontSize:'0.7rem',color:'var(--text-tertiary)'}}>{r.timestamp ? new Date(r.timestamp).toLocaleString() : ''}</span>
                  </div>
                  <div style={{fontSize:'0.8rem',color:'var(--text-secondary)',marginTop:'0.25rem'}}>
                    AI: {r.ai_recommendation} → User: {r.user_decision}
                    {isDecisionEqual(r.ai_recommendation, r.user_decision) ? <span style={{color:'var(--success)',marginLeft:'0.5rem'}}>✓ Agreed</span> : <span style={{color:'var(--warning)',marginLeft:'0.5rem'}}>✗ Disagreed</span>}
                  </div>
                  <div style={{fontSize:'0.75rem',color:'var(--text-tertiary)'}}>Time: {(r.time_to_decision_ms/1000).toFixed(1)}s • Load: {(r.cognitive_load_score*100).toFixed(0)}%</div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════
   FEDERATED NETWORK VIEW
   ═══════════════════════════════════════════════════════ */
function FederatedNetworkView() {
  const [fed, setFed] = useState(null);
  useEffect(() => { fetchFederatedStatus().then(setFed); }, []);
  if (!fed) return <div>Loading federated network...</div>;

  const tenantColors = { 'tenant_a': '#6366f1', 'corporate_b': '#10b981', 'bank_c': '#f59e0b', 'fintech_d': '#ef4444' };

  return (
    <div style={{display:'flex',flexDirection:'column',gap:'1.5rem'}}>
      {/* Tenant Cards */}
      <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit, minmax(250px, 1fr))',gap:'1rem'}}>
        {(fed.tenants||[]).map((t,i) => (
          <div key={i} className="glass-panel" style={{padding:'1.5rem',borderLeft:`4px solid ${tenantColors[t.tenant_id]||'var(--accent-primary)'}`}}>
            <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:'1rem'}}>
              <h3 style={{margin:0}}>{t.name}</h3>
              <span className={`badge ${t.status==='active'?'low':'medium'}`}>{t.status}</span>
            </div>
            <div className="info-row"><span className="info-row-label">Tenant ID</span><span className="info-row-value" style={{fontFamily:'monospace'}}>{t.tenant_id}</span></div>
            <div className="info-row"><span className="info-row-label">Cases</span><span className="info-row-value">{t.case_count?.toLocaleString()}</span></div>
            <div className="info-row"><span className="info-row-label">Transactions</span><span className="info-row-value">{t.txn_count?.toLocaleString()}</span></div>
            <div className="info-row"><span className="info-row-label">Anomaly Threshold</span><span className="info-row-value">{t.anomaly_threshold?.toFixed(4)||'-'}</span></div>
            <div className="info-row"><span className="info-row-label">Model Updated</span><span className="info-row-value">{t.model_last_updated ? new Date(t.model_last_updated).toLocaleDateString() : '-'}</span></div>
          </div>
        ))}
      </div>

      {/* Shared Intelligence */}
      <div className="glass-panel" style={{padding:'1.5rem'}}>
        <h3 style={{marginBottom:'1rem'}}>🔒 Shared Fraud Intelligence (Privacy-Preserving)</h3>
        <p style={{color:'var(--text-tertiary)',marginBottom:'1rem',fontSize:'0.85rem'}}>Anonymous fraud patterns shared across tenants. No private customer data is exposed.</p>
        <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit, minmax(300px, 1fr))',gap:'1rem'}}>
          {fed.pattern_summary && Object.entries(fed.pattern_summary).map(([cat, info]) => (
            <div key={cat} style={{background:'var(--bg-tertiary)',padding:'1rem',borderRadius:'8px'}}>
              <div style={{display:'flex',justifyContent:'space-between',marginBottom:'0.75rem'}}>
                <span style={{fontWeight:700}}>{cat}</span>
                <span className="badge medium">{info.count} indicators</span>
              </div>
              <div style={{fontSize:'0.8rem',color:'var(--text-secondary)'}}>Avg Confidence: {(info.avg_confidence*100).toFixed(0)}%</div>
              {(info.indicators||[]).map((ind, j) => (
                <div key={j} style={{marginTop:'0.5rem',padding:'0.5rem',background:'var(--bg-secondary)',borderRadius:'4px',fontSize:'0.8rem'}}>
                  <div style={{display:'flex',justifyContent:'space-between'}}>
                    <span className={`badge ${ind.severity==='HIGH'?'high':'medium'}`} style={{fontSize:'0.65rem'}}>{ind.severity}</span>
                    <span style={{color:'var(--text-tertiary)',fontSize:'0.7rem'}}>{ind.contributor}</span>
                  </div>
                  <div style={{color:'var(--text-secondary)',marginTop:'0.25rem'}}>{ind.description}</div>
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════
   SETTINGS VIEW
   ═══════════════════════════════════════════════════════ */
function SettingsView() {
  const [settings, setSettings] = useState({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchSettings().then(data => setSettings(data.settings || {}));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try { await updateSettings(settings); alert('Settings saved successfully!'); } catch(e) { console.error(e); }
    setSaving(false);
  };

  const updateField = (key, val) => setSettings(prev => ({ ...prev, [key]: val }));

  return (
    <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:'1.5rem'}}>
      {/* General Settings */}
      <div className="glass-panel" style={{padding:'1.5rem'}}>
        <h3 style={{marginBottom:'1rem'}}>⚙️ General</h3>
        <div style={{display:'grid',gap:'1rem'}}>
          <div className="info-row"><span className="info-row-label">Dark Mode</span>
            <select value={settings.dark_mode||'true'} onChange={e=>updateField('dark_mode',e.target.value)}
              style={{padding:'0.4rem',background:'var(--bg-tertiary)',color:'var(--text-primary)',border:'1px solid var(--border-color)',borderRadius:'4px'}}>
              <option value="true">Enabled</option><option value="false">Disabled</option>
            </select>
          </div>
          <div className="info-row"><span className="info-row-label">Notifications</span>
            <select value={settings.notifications_enabled||'true'} onChange={e=>updateField('notifications_enabled',e.target.value)}
              style={{padding:'0.4rem',background:'var(--bg-tertiary)',color:'var(--text-primary)',border:'1px solid var(--border-color)',borderRadius:'4px'}}>
              <option value="true">Enabled</option><option value="false">Disabled</option>
            </select>
          </div>
          <div className="info-row"><span className="info-row-label">Default Reviewer</span>
            <input value={settings.default_reviewer||''} onChange={e=>updateField('default_reviewer',e.target.value)}
              style={{padding:'0.4rem',background:'var(--bg-tertiary)',color:'var(--text-primary)',border:'1px solid var(--border-color)',borderRadius:'4px',width:'140px'}} />
          </div>
        </div>
      </div>

      {/* Risk Thresholds */}
      <div className="glass-panel" style={{padding:'1.5rem'}}>
        <h3 style={{marginBottom:'1rem'}}>📊 Risk Thresholds</h3>
        <div style={{display:'grid',gap:'1rem'}}>
          <div className="info-row"><span className="info-row-label">High Risk ≥</span>
            <input type="number" step="0.05" min="0" max="1" value={settings.risk_threshold_high||0.8} onChange={e=>updateField('risk_threshold_high',e.target.value)}
              style={{padding:'0.4rem',background:'var(--bg-tertiary)',color:'var(--text-primary)',border:'1px solid var(--border-color)',borderRadius:'4px',width:'80px'}} />
          </div>
          <div className="info-row"><span className="info-row-label">Medium Risk ≥</span>
            <input type="number" step="0.05" min="0" max="1" value={settings.risk_threshold_medium||0.4} onChange={e=>updateField('risk_threshold_medium',e.target.value)}
              style={{padding:'0.4rem',background:'var(--bg-tertiary)',color:'var(--text-primary)',border:'1px solid var(--border-color)',borderRadius:'4px',width:'80px'}} />
          </div>
          <div className="info-row"><span className="info-row-label">Recovery Rate</span>
            <input type="number" step="0.05" min="0" max="1" value={settings.recovery_rate||0.65} onChange={e=>updateField('recovery_rate',e.target.value)}
              style={{padding:'0.4rem',background:'var(--bg-tertiary)',color:'var(--text-primary)',border:'1px solid var(--border-color)',borderRadius:'4px',width:'80px'}} />
          </div>
          <div className="info-row"><span className="info-row-label">Review Cost ($)</span>
            <input type="number" step="5" value={settings.review_cost||75} onChange={e=>updateField('review_cost',e.target.value)}
              style={{padding:'0.4rem',background:'var(--bg-tertiary)',color:'var(--text-primary)',border:'1px solid var(--border-color)',borderRadius:'4px',width:'80px'}} />
          </div>
        </div>
      </div>

      {/* Gemma / Ollama Config */}
      <div className="glass-panel" style={{padding:'1.5rem'}}>
        <h3 style={{marginBottom:'1rem'}}>🤖 Gemma & Ollama</h3>
        <div style={{display:'grid',gap:'1rem'}}>
          <div className="info-row"><span className="info-row-label">Model</span>
            <select value={settings.gemma_model||'gemma2:2b'} onChange={e=>updateField('gemma_model',e.target.value)}
              style={{padding:'0.4rem',background:'var(--bg-tertiary)',color:'var(--text-primary)',border:'1px solid var(--border-color)',borderRadius:'4px'}}>
              <option value="gemma2:2b">gemma2:2b (Recommended)</option>
              <option value="gemma3:4b">gemma3:4b</option>
              <option value="gemma3:12b">gemma3:12b</option>
              <option value="gemma3:27b">gemma3:27b</option>
              <option value="gemma4:e4b">gemma4:e4b</option>
            </select>
          </div>
          <div className="info-row"><span className="info-row-label">Ollama URL</span>
            <input value={settings.ollama_url||'http://localhost:11434'} onChange={e=>updateField('ollama_url',e.target.value)}
              style={{padding:'0.4rem',background:'var(--bg-tertiary)',color:'var(--text-primary)',border:'1px solid var(--border-color)',borderRadius:'4px',width:'200px'}} />
          </div>
          <div className="info-row"><span className="info-row-label">ROI Formula</span>
            <input value={settings.roi_formula||''} onChange={e=>updateField('roi_formula',e.target.value)}
              style={{padding:'0.4rem',background:'var(--bg-tertiary)',color:'var(--text-primary)',border:'1px solid var(--border-color)',borderRadius:'4px',width:'200px'}} />
          </div>
        </div>
      </div>

      {/* Tenant Management */}
      <div className="glass-panel" style={{padding:'1.5rem'}}>
        <h3 style={{marginBottom:'1rem'}}>🏢 Tenant Management</h3>
        <div style={{display:'grid',gap:'0.75rem'}}>
          {['tenant_a: Antigravity Financial Corp', 'corporate_b: Meridian Corporate Bank', 'bank_c: Atlas National Bank', 'fintech_d: NovaPay Fintech'].map((t,i) => (
            <div key={i} style={{padding:'0.75rem',background:'var(--bg-tertiary)',borderRadius:'6px',display:'flex',justifyContent:'space-between',alignItems:'center'}}>
              <span style={{fontSize:'0.9rem'}}>{t}</span>
              <span className="badge low">Active</span>
            </div>
          ))}
        </div>
      </div>

      {/* Save Button */}
      <div style={{gridColumn:'span 2',textAlign:'right'}}>
        <button className="btn btn-primary" onClick={handleSave} disabled={saving} style={{padding:'0.75rem 2rem'}}>
          {saving ? 'Saving...' : '💾 Save All Settings'}
        </button>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════
   MAIN APP
   ═══════════════════════════════════════════════════════ */
function App() {
  const [user, setUser] = useState(() => {
    try { const u = localStorage.getItem('veritas_user'); return u ? JSON.parse(u) : null; } catch { return null; }
  });
  const [currentView, setCurrentView] = useState('triage');
  const [selectedCaseId, setSelectedCaseId] = useState(null);

  const handleLogin = (userData) => {
    setUser(userData);
    localStorage.setItem('veritas_user', JSON.stringify(userData));
  };

  const handleLogout = () => {
    setUser(null);
    localStorage.removeItem('veritas_user');
  };

  if (!user) {
    return <LoginPage onLogin={handleLogin} />;
  }

  const navItems = [
    { key: 'triage', label: 'Triage Inbox', icon: '📋' },
    { key: 'streaming', label: 'Streaming Monitor', icon: '📡' },
    { key: 'trust', label: 'Trust Calibration', icon: '🎯' },
    { key: 'federated', label: 'Federated Network', icon: '🌐' },
    { key: 'audit', label: 'Audit Logs', icon: '📜' },
    { key: 'settings', label: 'Settings', icon: '⚙️' },
  ];

  const renderContent = () => {
    switch (currentView) {
      case 'triage':
        return selectedCaseId ? <CaseDetails caseId={selectedCaseId} onBack={() => setSelectedCaseId(null)} /> : <CaseList onSelectCase={setSelectedCaseId} />;
      case 'audit': return <AuditLogsView />;
      case 'streaming': return <StreamingMonitorView />;
      case 'federated': return <FederatedNetworkView />;
      case 'trust': return <TrustCalibrationView />;
      case 'settings': return <SettingsView />;
      default: return <div>Unknown view</div>;
    }
  };

  const headerTitle = currentView === 'triage' && selectedCaseId ? 'Case Investigation' :
    currentView === 'triage' ? 'Triage Inbox' :
    currentView === 'streaming' ? 'Streaming Monitor' :
    currentView === 'trust' ? 'Trust Calibration' :
    currentView === 'federated' ? 'Federated Network' :
    currentView === 'audit' ? 'Audit Trail' :
    currentView === 'settings' ? 'Platform Settings' : 'Dashboard';

  return (
    <div className="app-container">
      <aside className="sidebar">
        <h2>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
          </svg>
          Veritas AML
        </h2>
        <ul className="sidebar-nav">
          {navItems.map(item => (
            <li key={item.key}>
              <a href="#" className={currentView === item.key ? 'active' : ''}
                onClick={() => { setCurrentView(item.key); setSelectedCaseId(null); }}>
                {item.icon} {item.label}
              </a>
            </li>
          ))}
        </ul>
        <div style={{ marginTop: 'auto', padding: '1rem', borderTop: '1px solid var(--border-color)' }}>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
            👤 {user.full_name || user.username}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)', marginBottom: '0.75rem' }}>
            Role: {user.role || 'analyst'}
          </div>
          <button onClick={handleLogout} style={{ width: '100%', padding: '0.5rem', background: 'transparent', border: '1px solid var(--border-color)', borderRadius: '4px', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '0.85rem' }}>
            🚪 Logout
          </button>
        </div>
      </aside>
      <main className="main-content">
        <header className="header"><h1>{headerTitle}</h1></header>
        {renderContent()}
      </main>
    </div>
  );
}

function AdversarialView({ caseId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleRunDebate = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await runAdversarialReasoning(caseId);
      if (res.error) throw new Error(res.error);
      setData(res);
    } catch (e) {
      setError(e.message || "Failed to execute adversarial debate.");
    }
    setLoading(false);
  };

  return (
    <div style={{ marginTop: '1rem', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div className="glass-panel" style={{ padding: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h3 style={{ margin: 0, color: 'var(--text-primary)' }}>Multi-Agent Adversarial Debate</h3>
          <p style={{ margin: '0.25rem 0 0 0', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
            Simulate a structured debate between an AI Prosecutor (arguing fraud) and an AI Defense (arguing innocence) to reach an unbiased verdict.
          </p>
        </div>
        <button className="btn btn-primary" onClick={handleRunDebate} disabled={loading}>
          {loading ? '⚖️ Simulating Debate...' : '⚖️ Run Debate'}
        </button>
      </div>

      {error && (
        <div style={{ color: 'var(--danger)', padding: '1rem', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid var(--danger)', borderRadius: '6px' }}>
          Error: {error}
        </div>
      )}

      {loading && (
        <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
          <div style={{
            margin: '0 auto 1rem auto',
            border: '4px solid var(--border-color)',
            borderTop: '4px solid var(--accent-primary)',
            borderRadius: '50%',
            width: '40px',
            height: '40px',
            animation: 'spin 1s linear infinite'
          }} />
          Simulating prosecution case, defense cross-examination, and judicial arbitration. Please wait...
        </div>
      )}

      {data && !loading && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.5rem' }}>
          {/* Left Column: Prosecutor */}
          <div className="glass-panel" style={{ borderLeft: '4px solid var(--danger)', padding: '1.5rem' }}>
            <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--danger)' }}>
              🚨 AI Prosecutor
            </h3>
            <div style={{ margin: '0.5rem 0', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
              Confidence Score of Guilt: <strong style={{ fontSize: '1.1rem', color: 'var(--text-primary)' }}>{data.prosecutor_confidence}%</strong>
            </div>
            <p style={{ color: 'var(--text-secondary)', lineHeight: '1.5' }}>{data.prosecutor_argument}</p>
            {data.prosecutor_points && data.prosecutor_points.length > 0 && (
              <div style={{ marginTop: '1rem' }}>
                <h4 style={{ margin: '0 0 0.5rem 0', fontSize: '0.95rem' }}>Key Suspicious Marks:</h4>
                <ul style={{ paddingLeft: '1.2rem', margin: 0, color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                  {data.prosecutor_points.map((pt, i) => (
                    <li key={i}>{pt}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Right Column: Defense */}
          <div className="glass-panel" style={{ borderLeft: '4px solid var(--success)', padding: '1.5rem' }}>
            <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--success)' }}>
              🛡️ AI Defense
            </h3>
            <div style={{ margin: '0.5rem 0', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
              Confidence Score of Innocence: <strong style={{ fontSize: '1.1rem', color: 'var(--text-primary)' }}>{data.defense_confidence}%</strong>
            </div>
            <p style={{ color: 'var(--text-secondary)', lineHeight: '1.5' }}>{data.defense_argument}</p>
            {data.defense_points && data.defense_points.length > 0 && (
              <div style={{ marginTop: '1rem' }}>
                <h4 style={{ margin: '0 0 0.5rem 0', fontSize: '0.95rem' }}>Mitigating Explanations:</h4>
                <ul style={{ paddingLeft: '1.2rem', margin: 0, color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                  {data.defense_points.map((pt, i) => (
                    <li key={i}>{pt}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Full-width: Judicial Arbitration */}
          <div className="glass-panel" style={{ gridColumn: 'span 2', borderLeft: '4px solid var(--accent-primary)', padding: '2rem' }}>
            <h3 style={{ margin: 0, color: 'var(--accent-primary)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
              <span>⚖️ Arbiter Verdict & Consensus</span>
              <span className={`badge ${data.recommended_action === 'ESCALATE' ? 'high' : 'medium'}`} style={{ fontSize: '0.9rem' }}>
                {data.recommended_action}
              </span>
            </h3>
            <div style={{ margin: '0.5rem 0 1.5rem 0', fontSize: '0.95rem', color: 'var(--text-secondary)' }}>
              Verdict Certainty Confidence: <strong style={{ fontSize: '1.2rem', color: 'var(--text-primary)' }}>{(data.arbiter_confidence * 100).toFixed(0)}%</strong>
            </div>
            
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.5rem', marginBottom: '1.5rem' }}>
              <div>
                <h4 style={{ margin: '0 0 0.25rem 0', fontSize: '0.95rem', color: 'var(--text-primary)' }}>Prosecutor Summary</h4>
                <p style={{ margin: 0, fontSize: '0.9rem', color: 'var(--text-secondary)' }}>{data.prosecutor_summary}</p>
              </div>
              <div>
                <h4 style={{ margin: '0 0 0.25rem 0', fontSize: '0.95rem', color: 'var(--text-primary)' }}>Defense Summary</h4>
                <p style={{ margin: 0, fontSize: '0.9rem', color: 'var(--text-secondary)' }}>{data.defense_summary}</p>
              </div>
            </div>

            <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '1.5rem' }}>
              <h4 style={{ margin: '0 0 0.5rem 0', fontSize: '1rem', color: 'var(--text-primary)' }}>Impartial Gavel Verdict</h4>
              <p style={{ margin: 0, color: 'var(--text-secondary)', lineHeight: '1.6' }}>{data.arbiter_verdict}</p>
            </div>

            {data.critical_missing_data && (
              <div style={{ marginTop: '1.5rem', background: 'rgba(255, 255, 255, 0.03)', padding: '1rem', borderRadius: '6px', border: '1px dashed var(--border-color)' }}>
                <h4 style={{ margin: '0 0 0.25rem 0', fontSize: '0.95rem', color: 'var(--accent-primary)' }}>📋 Critical Missing Investigation Data Needed</h4>
                <p style={{ margin: 0, fontSize: '0.9rem', color: 'var(--text-secondary)' }}>{data.critical_missing_data}</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
