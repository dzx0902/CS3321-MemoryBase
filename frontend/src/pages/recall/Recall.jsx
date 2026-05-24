import { useState } from 'react';
import { recallApi } from '../../api/client';
import { DEMO_WORKSPACE_ID } from '../../api/constants';
import { useToast } from '../../components/Toast';

const MEMORY_TYPES = ['', 'episodic', 'semantic', 'profile', 'procedural', 'decision', 'preference', 'task', 'risk'];
const ACCESS_LEVELS = ['', 'public', 'project', 'team', 'private'];

export default function Recall() {
  const toast = useToast();
  const [form, setForm] = useState({
    workspace_id: DEMO_WORKSPACE_ID,
    query_text: '',
    memory_type: '',
    access_level: '',
    status: 'active',
    limit: 10,
  });
  const [searching, setSearching] = useState(false);
  const [results, setResults] = useState(null);

  function updateField(key, value) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!form.query_text.trim()) {
      toast.error('Please enter a query');
      return;
    }
    setSearching(true);
    setResults(null);
    try {
      const data = await recallApi.search({
        workspace_id: form.workspace_id,
        query_text: form.query_text,
        memory_type: form.memory_type || undefined,
        access_level: form.access_level || undefined,
        status: form.status || undefined,
        limit: Number(form.limit),
      });
      setResults(data);
    } catch (err) {
      toast.error(err.message || 'Recall failed');
    } finally {
      setSearching(false);
    }
  }

  return (
    <div>
      <div className="section-header">
        <h1><span className="icon">◎</span> Semantic Recall</h1>
      </div>

      <form onSubmit={handleSubmit} className="card" style={{ marginBottom: 24 }}>
        <div className="form-group">
          <label>Query Text</label>
          <textarea className="textarea" rows={3} value={form.query_text}
            onChange={(e) => updateField('query_text', e.target.value)}
            placeholder="Enter your search query... (supports PostgreSQL full-text search + ILIKE)" />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '0 16px' }}>
          <div className="form-group">
            <label>Workspace</label>
            <input className="input" value={form.workspace_id}
              onChange={(e) => updateField('workspace_id', e.target.value)} />
          </div>
          <div className="form-group">
            <label>Memory Type</label>
            <select className="select" value={form.memory_type}
              onChange={(e) => updateField('memory_type', e.target.value)}>
              <option value="">Any</option>
              {MEMORY_TYPES.filter(Boolean).map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Access Level</label>
            <select className="select" value={form.access_level}
              onChange={(e) => updateField('access_level', e.target.value)}>
              <option value="">Any</option>
              {ACCESS_LEVELS.filter(Boolean).map((a) => <option key={a} value={a}>{a}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Result Limit</label>
            <input className="input" type="number" min="1" max="50" value={form.limit}
              onChange={(e) => updateField('limit', e.target.value)} />
          </div>
        </div>

        <button type="submit" className="btn btn--primary" disabled={searching} style={{ marginTop: 8 }}>
          {searching ? 'Searching...' : '◎ Search'}
        </button>
      </form>

      {searching && <div className="loading"><div className="spinner" />Searching memories...</div>}

      {results && !searching && (
        <>
          <div className="section-header" style={{ marginTop: 8 }}>
            <h3 style={{ fontFamily: 'system-ui, sans-serif', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
              {results.memories?.length || 0} results found
            </h3>
          </div>

          {(!results.memories || results.memories.length === 0) ? (
            <div className="empty-state">
              <div className="empty-state__icon">◎</div>
              <div className="empty-state__title">No results</div>
              <p className="text-muted">Try adjusting your query or filters.</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              {results.memories.map((m, i) => (
                <div key={m.memory_id || i} className="card" style={{ padding: '18px 22px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                    <span className="badge badge--accent">{m.memory_type || '—'}</span>
                    <strong style={{ fontSize: '1.05rem' }}>{m.summary || m.canonical_text || 'Untitled'}</strong>
                    {m.importance != null && (
                      <span className="badge badge--default">importance: {m.importance}</span>
                    )}
                  </div>

                  {m.canonical_text && (
                    <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: 8 }}>
                      {m.canonical_text.length > 300 ? m.canonical_text.slice(0, 300) + '...' : m.canonical_text}
                    </p>
                  )}

                  {m.evidence && m.evidence.length > 0 && (
                    <div style={{ marginTop: 8 }}>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                        Evidence ({m.evidence.length})
                      </div>
                      {m.evidence.map((ev, j) => (
                        <div key={j} style={{
                          padding: '8px 12px', background: 'var(--bg-secondary)',
                          borderRadius: 'var(--radius-sm)', marginBottom: 4, fontSize: '0.82rem',
                          border: '1px solid var(--border)',
                        }}>
                          <span className="badge badge--default" style={{ marginRight: 8, fontSize: '0.68rem' }}>
                            {ev.evidence_role || ev.role || '—'}
                          </span>
                          <span style={{ color: 'var(--text-secondary)' }}>
                            {ev.chunk_text ? (ev.chunk_text.length > 150 ? ev.chunk_text.slice(0, 150) + '...' : ev.chunk_text) : ev.notes || '—'}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
