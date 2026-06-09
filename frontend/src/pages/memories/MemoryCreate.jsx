import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { memoriesApi, sourcesApi } from '../../api/client';
import { DEMO_WORKSPACE_ID } from '../../api/constants';
import { useToast } from '../../components/Toast';

const MEMORY_TYPES = ['episodic', 'semantic', 'profile', 'procedural', 'decision', 'preference', 'task', 'risk'];
const ACCESS_LEVELS = ['public', 'project', 'team', 'private'];
const emptyEvidence = () => ({ chunk_id: '', evidence_role: 'supports', note: '' });

export default function MemoryCreate() {
  const navigate = useNavigate();
  const toast = useToast();
  const [submitting, setSubmitting] = useState(false);
  const [sources, setSources] = useState([]);
  const [selectedDocId, setSelectedDocId] = useState('');
  const [chunks, setChunks] = useState([]);
  const [loadingSources, setLoadingSources] = useState(false);
  const [loadingChunks, setLoadingChunks] = useState(false);
  const [form, setForm] = useState({
    workspace_id: DEMO_WORKSPACE_ID,
    summary: '',
    memory_type: 'semantic',
    canonical_text: '',
    importance: 3,
    access_level: 'project',
    evidence: [],
  });

  const loadSources = useCallback(async () => {
    if (!form.workspace_id) return;
    setLoadingSources(true);
    try {
      const data = await sourcesApi.list({ workspace_id: form.workspace_id, page_size: 100 });
      const items = data.items || [];
      setSources(items);
      if (selectedDocId && !items.some((source) => source.doc_id === selectedDocId)) {
        setSelectedDocId('');
        setChunks([]);
      }
    } catch (err) {
      toast.error(err.message || 'Failed to load sources');
    } finally {
      setLoadingSources(false);
    }
  }, [form.workspace_id, selectedDocId, toast]);

  const loadChunks = useCallback(async () => {
    if (!form.workspace_id || !selectedDocId) {
      setChunks([]);
      return;
    }
    setLoadingChunks(true);
    try {
      const data = await sourcesApi.detail(selectedDocId, { workspace_id: form.workspace_id });
      setChunks(data.chunks || []);
    } catch (err) {
      toast.error(err.message || 'Failed to load chunks');
      setChunks([]);
    } finally {
      setLoadingChunks(false);
    }
  }, [form.workspace_id, selectedDocId, toast]);

  useEffect(() => { loadSources(); }, [loadSources]);
  useEffect(() => { loadChunks(); }, [loadChunks]);

  function updateField(key, value) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function addEvidence() {
    setForm((f) => ({ ...f, evidence: [...f.evidence, emptyEvidence()] }));
  }

  function updateEvidence(idx, key, value) {
    setForm((f) => {
      const ev = [...f.evidence];
      ev[idx] = { ...ev[idx], [key]: value };
      return { ...f, evidence: ev };
    });
  }

  function removeEvidence(idx) {
    setForm((f) => ({ ...f, evidence: f.evidence.filter((_, i) => i !== idx) }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitting(true);
    try {
      const body = {
        workspace_id: form.workspace_id,
        memory_type: form.memory_type,
        canonical_text: form.canonical_text,
        summary: form.summary || null,
        importance: Number(form.importance),
        access_level: form.access_level,
        evidence: form.evidence.filter((ev) => ev.chunk_id).map((ev) => ({
          chunk_id: ev.chunk_id,
          evidence_role: ev.evidence_role,
          note: ev.note || undefined,
        })),
      };
      const created = await memoriesApi.create(body);
      toast.success('Memory created successfully');
      navigate(`/memories/${created.memory_id}?workspace_id=${created.workspace_id}`);
    } catch (err) {
      toast.error(err.message || 'Failed to create memory');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div>
      <div className="section-header">
        <h1><span className="icon">+</span> Create Memory</h1>
      </div>

      <form onSubmit={handleSubmit} className="card">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 20px' }}>
          <div className="form-group">
            <label>Workspace ID</label>
            <input className="input" value={form.workspace_id}
              onChange={(e) => updateField('workspace_id', e.target.value)} required />
          </div>
          <div className="form-group">
            <label>Summary</label>
            <input className="input" value={form.summary}
              onChange={(e) => updateField('summary', e.target.value)} placeholder="Optional short summary..." />
          </div>
          <div className="form-group">
            <label>Type</label>
            <select className="select" value={form.memory_type}
              onChange={(e) => updateField('memory_type', e.target.value)}>
              {MEMORY_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Access Level</label>
            <select className="select" value={form.access_level}
              onChange={(e) => updateField('access_level', e.target.value)}>
              {ACCESS_LEVELS.map((a) => <option key={a} value={a}>{a}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Importance (1-5)</label>
            <input className="input" type="number" min="1" max="5" value={form.importance}
              onChange={(e) => updateField('importance', e.target.value)} />
          </div>
        </div>

        <div className="form-group">
          <label>Content</label>
          <textarea className="textarea" rows={6} value={form.canonical_text}
            onChange={(e) => updateField('canonical_text', e.target.value)} placeholder="Memory content (Markdown supported)..." required />
        </div>

        <div style={{ marginTop: 20, marginBottom: 12, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16 }}>
          <h4 style={{ fontFamily: 'Playfair Display, serif', fontSize: '1rem' }}>Evidence</h4>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
            <select
              className="select"
              value={selectedDocId}
              onChange={(e) => setSelectedDocId(e.target.value)}
              disabled={loadingSources}
              style={{ minWidth: 260 }}
            >
              <option value="">{loadingSources ? 'Loading sources...' : 'Select source document...'}</option>
              {sources.map((source) => (
                <option key={source.doc_id} value={source.doc_id}>
                  {source.title || source.source_path || source.doc_id}
                </option>
              ))}
            </select>
            <button type="button" className="btn btn--sm" onClick={addEvidence}>+ Add Evidence</button>
          </div>
        </div>

        {form.evidence.length === 0 && (
          <p className="text-muted" style={{ fontSize: '0.82rem', marginBottom: 12 }}>
            No evidence items. Select a source document, then link one of its chunks.
          </p>
        )}

        {form.evidence.map((ev, idx) => (
          <div key={idx} style={{
            display: 'flex', gap: 10, marginBottom: 10, alignItems: 'flex-end',
            padding: '12px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)',
          }}>
            <div className="form-group" style={{ flex: 2, marginBottom: 0 }}>
              <label>Chunk</label>
              <select
                className="select"
                value={ev.chunk_id}
                onChange={(e) => updateEvidence(idx, 'chunk_id', e.target.value)}
                disabled={!selectedDocId || loadingChunks}
              >
                <option value="">
                  {!selectedDocId ? 'Select source first...' : loadingChunks ? 'Loading chunks...' : 'Select chunk...'}
                </option>
                {chunks.map((chunk) => (
                  <option key={chunk.chunk_id} value={chunk.chunk_id}>
                    #{chunk.chunk_no} · {chunk.chunk_text ? chunk.chunk_text.slice(0, 80) : chunk.chunk_id}
                  </option>
                ))}
              </select>
            </div>
            <div className="form-group" style={{ flex: 1, marginBottom: 0 }}>
              <label>Role</label>
              <select className="select" value={ev.evidence_role}
                onChange={(e) => updateEvidence(idx, 'evidence_role', e.target.value)}>
                <option value="supports">supports</option>
                <option value="refutes">refutes</option>
                <option value="context">context</option>
                <option value="source">source</option>
              </select>
            </div>
            <div className="form-group" style={{ flex: 2, marginBottom: 0 }}>
              <label>Notes</label>
              <input className="input" value={ev.note} placeholder="Optional notes..."
                onChange={(e) => updateEvidence(idx, 'note', e.target.value)} />
            </div>
            <button type="button" className="btn btn--danger btn--sm"
              onClick={() => removeEvidence(idx)} style={{ marginBottom: 0, flexShrink: 0 }}>✕</button>
          </div>
        ))}

        <div style={{ marginTop: 24, display: 'flex', gap: 10 }}>
          <button type="submit" className="btn btn--primary" disabled={submitting}>
            {submitting ? 'Creating...' : 'Create Memory'}
          </button>
          <button type="button" className="btn" onClick={() => navigate('/memories')}>Cancel</button>
        </div>
      </form>
    </div>
  );
}
