import { useCallback, useEffect, useState } from 'react';
import { sessionsApi } from '../../api/client';
import { DEMO_AGENT_ID, DEMO_USER_ID, DEMO_WORKSPACE_ID } from '../../api/constants';
import { useToast } from '../../components/Toast';

const CHANNELS = ['chat', 'meeting', 'import', 'manual', 'cli'];

export default function Sessions() {
  const toast = useToast();
  const [workspaceId, setWorkspaceId] = useState(DEMO_WORKSPACE_ID);
  const [agentId, setAgentId] = useState(DEMO_AGENT_ID);
  const [sessions, setSessions] = useState([]);
  const [selectedSessionId, setSelectedSessionId] = useState('');
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ title: 'Web runtime session', channel: 'chat' });

  const loadSessions = useCallback(async () => {
    setLoading(true);
    try {
      const data = await sessionsApi.list({
        workspace_id: workspaceId,
        agent_id: agentId || undefined,
        page_size: 20,
      });
      const items = data.items || [];
      setSessions(items);
      const selectedExists = items.some((item) => item.session_id === selectedSessionId);
      if (!selectedExists) setSelectedSessionId(items[0]?.session_id || '');
    } catch (err) {
      toast.error(err.message || 'Failed to load sessions');
    } finally {
      setLoading(false);
    }
  }, [agentId, selectedSessionId, toast, workspaceId]);

  const loadMessages = useCallback(async () => {
    if (!selectedSessionId) {
      setMessages([]);
      return;
    }
    setLoadingMessages(true);
    try {
      const data = await sessionsApi.messages(selectedSessionId, { workspace_id: workspaceId, limit: 50 });
      setMessages(data.items || data.messages || []);
    } catch (err) {
      toast.error(err.message || 'Failed to load messages');
    } finally {
      setLoadingMessages(false);
    }
  }, [selectedSessionId, toast, workspaceId]);

  useEffect(() => {
    setSelectedSessionId('');
    setMessages([]);
  }, [agentId, workspaceId]);

  useEffect(() => { loadSessions(); }, [loadSessions]);
  useEffect(() => { loadMessages(); }, [loadMessages]);

  async function createSession(e) {
    e.preventDefault();
    setCreating(true);
    try {
      const created = await sessionsApi.create({
        workspace_id: workspaceId,
        agent_id: agentId || undefined,
        started_by_user_id: DEMO_USER_ID,
        title: form.title,
        channel: form.channel,
      });
      toast.success('Session created');
      setSelectedSessionId(created.session_id);
      setSessions((items) => {
        const exists = items.some((item) => item.session_id === created.session_id);
        return exists ? items : [created, ...items];
      });
    } catch (err) {
      toast.error(err.message || 'Failed to create session');
    } finally {
      setCreating(false);
    }
  }

  return (
    <div>
      <div className="section-header">
        <h1><span className="icon">◉</span> Runtime Sessions</h1>
        <button className="btn" onClick={loadSessions} disabled={loading}>Refresh</button>
      </div>

      <form className="card" onSubmit={createSession} style={{ marginBottom: 20 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '0 16px' }}>
          <div className="form-group">
            <label>Workspace ID</label>
            <input className="input" value={workspaceId} onChange={(e) => setWorkspaceId(e.target.value)} />
          </div>
          <div className="form-group">
            <label>Agent ID</label>
            <input className="input" value={agentId} onChange={(e) => setAgentId(e.target.value)} />
          </div>
          <div className="form-group">
            <label>Title</label>
            <input className="input" value={form.title}
              onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))} />
          </div>
          <div className="form-group">
            <label>Channel</label>
            <select className="select" value={form.channel}
              onChange={(e) => setForm((f) => ({ ...f, channel: e.target.value }))}>
              {CHANNELS.map((channel) => <option key={channel} value={channel}>{channel}</option>)}
            </select>
          </div>
        </div>
        <button className="btn btn--primary" type="submit" disabled={creating}>
          {creating ? 'Creating...' : '+ New Session'}
        </button>
      </form>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(320px, 0.9fr) minmax(360px, 1.1fr)', gap: 20 }}>
        <div className="card">
          <div className="card__header">
            <h3 className="card__title">Sessions</h3>
            <span className="badge badge--default">{sessions.length}</span>
          </div>
          {loading ? (
            <div className="loading"><div className="spinner" />Loading sessions...</div>
          ) : sessions.length === 0 ? (
            <div className="empty-state"><div className="empty-state__title">No sessions</div></div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {sessions.map((session) => (
                <button
                  key={session.session_id}
                  type="button"
                  className={`btn ${selectedSessionId === session.session_id ? 'btn--primary' : ''}`}
                  onClick={() => setSelectedSessionId(session.session_id)}
                  style={{ justifyContent: 'flex-start', textAlign: 'left' }}
                >
                  <span>
                    <strong>{session.title || 'Untitled session'}</strong>
                    <span className="text-muted" style={{ display: 'block', fontSize: '0.75rem' }}>
                      {session.channel || 'chat'} · {session.started_at ? new Date(session.started_at).toLocaleString() : '—'}
                    </span>
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="card">
          <div className="card__header">
            <h3 className="card__title">Messages</h3>
            <span className="badge badge--info">{messages.length}</span>
          </div>
          {loadingMessages ? (
            <div className="loading"><div className="spinner" />Loading messages...</div>
          ) : messages.length === 0 ? (
            <div className="empty-state"><div className="empty-state__title">No messages</div></div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {messages.map((message) => (
                <div key={message.message_id} style={{
                  padding: '12px 14px',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--bg-elevated)',
                }}>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 6 }}>
                    <span className="badge badge--accent">{message.role || message.sender_type}</span>
                    <span className="text-muted" style={{ fontSize: '0.75rem' }}>
                      {message.created_at ? new Date(message.created_at).toLocaleString() : '—'}
                    </span>
                  </div>
                  <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.55 }}>{message.content}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
