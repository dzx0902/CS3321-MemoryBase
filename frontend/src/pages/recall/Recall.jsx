import { useState } from 'react';
import { qaApi, recallApi } from '../../api/client';
import { DEMO_WORKSPACE_ID } from '../../api/constants';
import { useToast } from '../../components/Toast';

const MEMORY_TYPES = ['', 'episodic', 'semantic', 'profile', 'procedural', 'decision', 'preference', 'task', 'risk'];
const ACCESS_LEVELS = ['', 'public', 'project', 'team', 'private'];
const RETRIEVAL_MODES = ['keyword', 'hybrid', 'vector'];

export default function Recall() {
  const toast = useToast();
  const [form, setForm] = useState({
    workspace_id: DEMO_WORKSPACE_ID,
    query_text: '',
    memory_type: '',
    access_level: '',
    status: 'active',
    retrieval_mode: 'keyword',
    limit: 10,
    max_tokens: 3000,
    max_answer_tokens: 800,
  });
  const [searching, setSearching] = useState(false);
  const [answering, setAnswering] = useState(false);
  const [results, setResults] = useState(null);
  const [contextPack, setContextPack] = useState(null);
  const [answer, setAnswer] = useState(null);

  function updateField(key, value) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  async function handleSubmit(e) {
    // Search, context pack, and QA share the same form so the demo can show the
    // same query moving from raw recall to agent-ready context to optional answer.
    e.preventDefault();
    if (!form.query_text.trim()) {
      toast.error('Please enter a query');
      return;
    }
    setSearching(true);
    setResults(null);
    setContextPack(null);
    setAnswer(null);
    try {
      const data = await recallApi.search({
        workspace_id: form.workspace_id,
        query_text: form.query_text,
        memory_type: form.memory_type || undefined,
        access_level: form.access_level || undefined,
        status: form.status || undefined,
        retrieval_mode: form.retrieval_mode,
        limit: Number(form.limit),
      });
      setResults(data);
    } catch (err) {
      toast.error(err.message || 'Recall failed');
    } finally {
      setSearching(false);
    }
  }

  async function handleContextPack() {
    if (!form.query_text.trim()) {
      toast.error('Please enter a query');
      return;
    }
    setSearching(true);
    setContextPack(null);
    setAnswer(null);
    try {
      const data = await recallApi.contextPack({
        workspace_id: form.workspace_id,
        query_text: form.query_text,
        memory_type: form.memory_type || undefined,
        access_level: form.access_level || undefined,
        status: form.status || undefined,
        retrieval_mode: form.retrieval_mode,
        limit: Number(form.limit),
        max_tokens: Number(form.max_tokens),
      });
      setContextPack(data);
    } catch (err) {
      toast.error(err.message || 'Context pack failed');
    } finally {
      setSearching(false);
    }
  }

  async function handleAnswer() {
    if (!form.query_text.trim()) {
      toast.error('Please enter a query');
      return;
    }
    setAnswering(true);
    setAnswer(null);
    try {
      const data = await qaApi.answer({
        workspace_id: form.workspace_id,
        query_text: form.query_text,
        memory_type: form.memory_type || undefined,
        access_level: form.access_level || undefined,
        status: form.status || undefined,
        retrieval_mode: form.retrieval_mode,
        limit: Number(form.limit),
        max_context_tokens: Number(form.max_tokens),
        max_answer_tokens: Number(form.max_answer_tokens),
      });
      setAnswer(data);
    } catch (err) {
      toast.error(err.message || 'Answer generation failed');
    } finally {
      setAnswering(false);
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
          <div className="form-group">
            <label>Retrieval Mode</label>
            <select className="select" value={form.retrieval_mode}
              onChange={(e) => updateField('retrieval_mode', e.target.value)}>
              {RETRIEVAL_MODES.map((mode) => <option key={mode} value={mode}>{mode}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Context Tokens</label>
            <input className="input" type="number" min="100" max="16000" value={form.max_tokens}
              onChange={(e) => updateField('max_tokens', e.target.value)} />
          </div>
          <div className="form-group">
            <label>Answer Tokens</label>
            <input className="input" type="number" min="1" max="4096" value={form.max_answer_tokens}
              onChange={(e) => updateField('max_answer_tokens', e.target.value)} />
          </div>
        </div>

        <div style={{ display: 'flex', gap: 10, marginTop: 8 }}>
          <button type="submit" className="btn btn--primary" disabled={searching}>
            {searching ? 'Searching...' : '◎ Search'}
          </button>
          <button type="button" className="btn btn--primary" disabled={answering} onClick={handleAnswer}>
            {answering ? 'Answering...' : 'Ask'}
          </button>
          <button type="button" className="btn" disabled={searching} onClick={handleContextPack}>
            Context Pack
          </button>
        </div>
      </form>

      {searching && <div className="loading"><div className="spinner" />Searching memories...</div>}
      {answering && <div className="loading"><div className="spinner" />Generating answer...</div>}

      {answer && !answering && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card__header">
            <h3 className="card__title">Answer</h3>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
              <span className="badge badge--accent">{answer.provider}</span>
              <span className="badge badge--default">{answer.model}</span>
              <span className="badge badge--info">{answer.result_count} memories</span>
            </div>
          </div>
          <div className="markdown-body" style={{ whiteSpace: 'pre-wrap', fontSize: '0.95rem' }}>
            {answer.answer}
          </div>
          {answer.selected_memories?.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Used Memories
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {answer.selected_memories.map((memory) => (
                  <span key={memory.ref} className="badge badge--default">
                    {memory.ref}: {memory.memory_type}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {contextPack && !searching && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card__header">
            <h3 className="card__title">Context Pack</h3>
            <span className="badge badge--info">{contextPack.token_count} tokens</span>
            {contextPack.recall_id && (
              <span className="text-mono text-muted" style={{ marginLeft: 8, fontSize: '0.72rem' }}>
                {contextPack.recall_id}
              </span>
            )}
          </div>
          <pre className="markdown-body" style={{ whiteSpace: 'pre-wrap', fontSize: '0.86rem', maxHeight: 520, overflowY: 'auto' }}>
            {contextPack.markdown}
          </pre>
        </div>
      )}

      {results && !searching && (
        <>
          {results.retrieval_info && (
            <div className="card" style={{ marginBottom: 16, padding: '14px 18px' }}>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 8 }}>
                <span className="badge badge--accent">
                  requested: {results.retrieval_info.requested_mode}
                </span>
                <span className="badge badge--default">
                  effective: {results.retrieval_info.effective_mode}
                </span>
                <span className="badge badge--info">
                  embedding: {results.retrieval_info.embedding_provider}/{results.retrieval_info.embedding_model}
                </span>
              </div>
              <div className="text-muted" style={{ fontSize: '0.82rem', lineHeight: 1.5 }}>
                vector memory candidates: {results.retrieval_info.vector_memory_candidates}, vector chunk candidates: {results.retrieval_info.vector_chunk_candidates}
                {results.retrieval_info.fallback_reason ? `; ${results.retrieval_info.fallback_reason}` : ''}
              </div>
            </div>
          )}

          <div className="section-header" style={{ marginTop: 8 }}>
            <h3 style={{ fontFamily: 'system-ui, sans-serif', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
              {results.memories?.length || 0} results found
              {results.recall_id && (
                <span className="text-mono text-muted" style={{ marginLeft: 12, fontSize: '0.75rem' }}>
                  recall_id: {results.recall_id}
                </span>
              )}
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
                          padding: '8px 12px', background: 'var(--bg-elevated)',
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
