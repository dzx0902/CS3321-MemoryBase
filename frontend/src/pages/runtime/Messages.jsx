import { useCallback, useEffect, useState } from 'react';
import { observeApi, sessionsApi } from '../../api/client';
import { DEMO_AGENT_ID, DEMO_USER_ID, DEMO_WORKSPACE_ID } from '../../api/constants';
import { useToast } from '../../components/Toast';

const ROLES = ['user', 'assistant', 'system', 'tool'];
const SENDER_TYPES = ['user', 'agent', 'system'];

export default function Messages() {
  const toast = useToast();
  const [workspaceId, setWorkspaceId] = useState(DEMO_WORKSPACE_ID);
  const [sessions, setSessions] = useState([]);
  const [sessionId, setSessionId] = useState('');
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [posting, setPosting] = useState(false);
  const [form, setForm] = useState({
    sender_type: 'user',
    sender_id: DEMO_USER_ID,
    role: 'user',
    content: '',
  });

  const loadSessions = useCallback(async () => {
    try {
      const data = await sessionsApi.list({ workspace_id: workspaceId, page_size: 50 });
      const items = data.items || [];
      setSessions(items);
      const selectedExists = items.some((item) => item.session_id === sessionId);
      if (!selectedExists) setSessionId(items[0]?.session_id || '');
    } catch (err) {
      toast.error(err.message || 'Failed to load sessions');
    }
  }, [sessionId, toast, workspaceId]);

  const loadMessages = useCallback(async () => {
    if (!sessionId) {
      setMessages([]);
      return;
    }
    setLoading(true);
    try {
      const data = await sessionsApi.messages(sessionId, { workspace_id: workspaceId, limit: 100 });
      setMessages(data.items || data.messages || []);
    } catch (err) {
      toast.error(err.message || 'Failed to load messages');
    } finally {
      setLoading(false);
    }
  }, [sessionId, toast, workspaceId]);

  useEffect(() => {
    setSessionId('');
    setMessages([]);
  }, [workspaceId]);

  useEffect(() => { loadSessions(); }, [loadSessions]);
  useEffect(() => { loadMessages(); }, [loadMessages]);

  function updateForm(key, value) {
    setForm((f) => {
      const next = { ...f, [key]: value };
      if (key === 'sender_type') {
        next.role = value === 'agent' ? 'assistant' : value;
        next.sender_id = value === 'agent' ? DEMO_AGENT_ID : value === 'user' ? DEMO_USER_ID : '';
      }
      return next;
    });
  }

  async function sendMessage(e) {
    e.preventDefault();
    if (!sessionId) {
      toast.error('Select a session first');
      return;
    }
    if (!form.content.trim()) {
      toast.error('Message content is required');
      return;
    }
    setPosting(true);
    try {
      await observeApi.create({
        session_id: sessionId,
        sender_type: form.sender_type,
        sender_id: form.sender_id || undefined,
        role: form.role,
        content: form.content,
      });
      setForm((f) => ({ ...f, content: '' }));
      toast.success('Message recorded');
      await loadMessages();
    } catch (err) {
      toast.error(err.message || 'Failed to record message');
    } finally {
      setPosting(false);
    }
  }

  return (
    <div>
      <div className="section-header">
        <h1><span className="icon">✉</span> Runtime Messages</h1>
        <button className="btn" onClick={loadMessages} disabled={loading}>Refresh</button>
      </div>

      <form className="card" onSubmit={sendMessage} style={{ marginBottom: 20 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '0 16px' }}>
          <div className="form-group">
            <label>Workspace ID</label>
            <input className="input" value={workspaceId} onChange={(e) => setWorkspaceId(e.target.value)} />
          </div>
          <div className="form-group">
            <label>Session</label>
            <select className="select" value={sessionId} onChange={(e) => setSessionId(e.target.value)}>
              <option value="">Select session...</option>
              {sessions.map((session) => (
                <option key={session.session_id} value={session.session_id}>
                  {session.title || session.session_id}
                </option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label>Sender Type</label>
            <select className="select" value={form.sender_type} onChange={(e) => updateForm('sender_type', e.target.value)}>
              {SENDER_TYPES.map((type) => <option key={type} value={type}>{type}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Role</label>
            <select className="select" value={form.role} onChange={(e) => updateForm('role', e.target.value)}>
              {ROLES.map((role) => <option key={role} value={role}>{role}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Sender ID</label>
            <input className="input" value={form.sender_id} onChange={(e) => updateForm('sender_id', e.target.value)} />
          </div>
        </div>

        <div className="form-group">
          <label>Content</label>
          <textarea className="textarea" rows={4} value={form.content}
            onChange={(e) => updateForm('content', e.target.value)}
            placeholder="Record a user, assistant, system, or tool message..." />
        </div>

        <button className="btn btn--primary" type="submit" disabled={posting}>
          {posting ? 'Recording...' : 'Record Message'}
        </button>
      </form>

      {loading ? (
        <div className="loading"><div className="spinner" />Loading messages...</div>
      ) : messages.length === 0 ? (
        <div className="empty-state"><div className="empty-state__title">No messages</div></div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {messages.map((message) => (
            <div key={message.message_id} className="card" style={{ padding: '14px 18px' }}>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 8 }}>
                <span className="badge badge--accent">{message.role || '—'}</span>
                <span className="badge badge--default">{message.sender_type || '—'}</span>
                <span className="text-muted" style={{ fontSize: '0.75rem' }}>
                  {message.created_at ? new Date(message.created_at).toLocaleString() : '—'}
                </span>
              </div>
              <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>{message.content}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
