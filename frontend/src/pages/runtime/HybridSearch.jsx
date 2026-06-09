import { useState } from 'react';
import { searchApi } from '../../api/client';
import { DEMO_AGENT_ID, DEMO_WORKSPACE_ID } from '../../api/constants';
import { useToast } from '../../components/Toast';

const SCOPES = ['all', 'chunks', 'memories', 'sources'];
const RESULT_TYPES = ['chunk', 'memory', 'source'];

export default function HybridSearch() {
  const toast = useToast();
  const [searching, setSearching] = useState(false);
  const [response, setResponse] = useState(null);
  const [typeFilter, setTypeFilter] = useState('all');
  const [form, setForm] = useState({
    workspace_id: DEMO_WORKSPACE_ID,
    agent_id: DEMO_AGENT_ID,
    query_text: 'project preference',
    scope: 'all',
    limit: 10,
  });

  function updateField(key, value) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  async function handleSearch(e) {
    e.preventDefault();
    if (!form.query_text.trim()) {
      toast.error('Query text is required');
      return;
    }
    setSearching(true);
    setResponse(null);
    setTypeFilter('all');
    try {
      const data = await searchApi.search({
        workspace_id: form.workspace_id,
        agent_id: form.agent_id || undefined,
        query_text: form.query_text,
        scope: form.scope,
        limit: Number(form.limit),
      });
      setResponse(data);
    } catch (err) {
      toast.error(err.message || 'Hybrid search failed');
    } finally {
      setSearching(false);
    }
  }

  return (
    <div>
      <div className="section-header">
        <h1><span className="icon">⌕</span> Hybrid Search</h1>
      </div>

      <form className="card" onSubmit={handleSearch} style={{ marginBottom: 24 }}>
        <div className="form-group">
          <label>Query Text</label>
          <textarea className="textarea" rows={3} value={form.query_text}
            onChange={(e) => updateField('query_text', e.target.value)}
            placeholder="Search chunks, memories, and sources with RRF fusion..." />
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0 16px' }}>
          <div className="form-group">
            <label>Workspace ID</label>
            <input className="input" value={form.workspace_id} onChange={(e) => updateField('workspace_id', e.target.value)} />
          </div>
          <div className="form-group">
            <label>Agent ID</label>
            <input className="input" value={form.agent_id} onChange={(e) => updateField('agent_id', e.target.value)} />
          </div>
          <div className="form-group">
            <label>Scope</label>
            <select className="select" value={form.scope} onChange={(e) => updateField('scope', e.target.value)}>
              {SCOPES.map((scope) => <option key={scope} value={scope}>{scope}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Limit</label>
            <input className="input" type="number" min="1" max="50" value={form.limit}
              onChange={(e) => updateField('limit', e.target.value)} />
          </div>
        </div>
        <button className="btn btn--primary" disabled={searching} type="submit">
          {searching ? 'Searching...' : 'Run Hybrid Search'}
        </button>
      </form>

      {searching && <div className="loading"><div className="spinner" />Searching...</div>}

      {response && !searching && (() => {
        const allItems = response.items || [];
        const visibleItems = typeFilter === 'all'
          ? allItems
          : allItems.filter((item) => item.result_type === typeFilter);
        const typeCounts = RESULT_TYPES.reduce((acc, type) => {
          acc[type] = allItems.filter((item) => item.result_type === type).length;
          return acc;
        }, {});
        return (
          <>
          <div className="section-header" style={{ marginTop: 8 }}>
            <h3 style={{ fontFamily: 'system-ui, sans-serif', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
              {response.result_count || 0} results · tokenized: <span className="text-mono">{response.tokenized_query || '—'}</span>
            </h3>
          </div>

          {allItems.length > 0 && (
            <div style={{ display: 'flex', gap: 8, marginBottom: 14, flexWrap: 'wrap' }}>
              <button type="button" className={`btn btn--sm ${typeFilter === 'all' ? 'btn--primary' : ''}`}
                onClick={() => setTypeFilter('all')}>
                All ({allItems.length})
              </button>
              {RESULT_TYPES.map((type) => (
                <button key={type} type="button"
                  className={`btn btn--sm ${typeFilter === type ? 'btn--primary' : ''}`}
                  disabled={typeCounts[type] === 0}
                  onClick={() => setTypeFilter(type)}>
                  {type} ({typeCounts[type]})
                </button>
              ))}
            </div>
          )}

          {visibleItems.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state__icon">⌕</div>
              <div className="empty-state__title">No results</div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              {visibleItems.map((item) => (
                <div key={`${item.result_type}-${item.result_id}`} className="card" style={{ padding: '16px 20px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, flexWrap: 'wrap' }}>
                    <span className="badge badge--accent">{item.result_type}</span>
                    <span className="badge badge--info">score {Number(item.score || 0).toFixed(4)}</span>
                    {(item.strategies || []).map((strategy) => (
                      <span key={strategy} className="badge badge--default">{strategy}</span>
                    ))}
                  </div>
                  <p style={{ lineHeight: 1.65, color: 'var(--text-secondary)', marginBottom: 10 }}>
                    {item.snippet || '—'}
                  </p>
                  <div className="text-muted" style={{ display: 'flex', gap: 12, flexWrap: 'wrap', fontSize: '0.76rem' }}>
                    <span>{item.source_title || item.source_path || 'No source title'}</span>
                    {item.start_line != null && <span>Lines {item.start_line}-{item.end_line ?? item.start_line}</span>}
                    <span className="text-mono">{item.result_id}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
          </>
        );
      })()}
    </div>
  );
}
