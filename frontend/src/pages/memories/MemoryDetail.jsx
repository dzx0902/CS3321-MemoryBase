import { useState, useEffect } from 'react';
import { useParams, Link, useNavigate, useSearchParams } from 'react-router-dom';
import { memoriesApi } from '../../api/client';
import { useToast } from '../../components/Toast';

export default function MemoryDetail() {
  const { memoryId } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const workspaceId = searchParams.get('workspace_id');
  const [memory, setMemory] = useState(null);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(false);
  const toast = useToast();

  useEffect(() => {
    async function load() {
      if (!workspaceId) {
        toast.error('Missing workspace_id in URL');
        setLoading(false);
        return;
      }
      try {
        const data = await memoriesApi.detail(memoryId, { workspace_id: workspaceId });
        setMemory(data);
      } catch (err) {
        toast.error(err.message || 'Failed to load memory');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [memoryId, workspaceId, toast]);

  async function handleDelete() {
    if (!window.confirm('Archive this memory? This performs a soft delete.')) return;
    setDeleting(true);
    try {
      await memoriesApi.remove(memoryId, { workspace_id: workspaceId });
      toast.success('Memory archived');
      navigate('/memories');
    } catch (err) {
      toast.error(err.message || 'Failed to delete');
      setDeleting(false);
    }
  }

  if (loading) return <div className="loading"><div className="spinner" />Loading memory...</div>;
  if (!memory) return <div className="empty-state"><div className="empty-state__title">Memory not found</div></div>;

  const statusBadge = {
    active: 'badge--success', archived: 'badge--default', forgotten: 'badge--danger',
    superseded: 'badge--info', conflicted: 'badge--danger',
  }[memory.status] || 'badge--default';

  return (
    <div>
      <div className="section-header">
        <h1><span className="icon">◈</span> {memory.summary || memory.canonical_text || 'Untitled'}</h1>
        <div style={{ display: 'flex', gap: 8 }}>
          <Link to="/memories" className="btn">← Back</Link>
          <Link to={`/memories/${memoryId}/edit?workspace_id=${workspaceId}`} className="btn">Edit</Link>
          <button className="btn btn--danger" onClick={handleDelete} disabled={deleting}>
            {deleting ? 'Archiving...' : 'Archive'}
          </button>
        </div>
      </div>

      <div className="detail-grid">
        <div className="detail-item">
          <div className="detail-item__label">Memory ID</div>
          <div className="detail-item__value text-mono">{memory.memory_id}</div>
        </div>
        <div className="detail-item">
          <div className="detail-item__label">Type</div>
          <div className="detail-item__value"><span className="badge badge--accent">{memory.memory_type}</span></div>
        </div>
        <div className="detail-item">
          <div className="detail-item__label">Status</div>
          <div className="detail-item__value"><span className={`badge ${statusBadge}`}>{memory.status}</span></div>
        </div>
        <div className="detail-item">
          <div className="detail-item__label">Access Level</div>
          <div className="detail-item__value"><span className="badge badge--info">{memory.access_level || '—'}</span></div>
        </div>
        <div className="detail-item">
          <div className="detail-item__label">Importance</div>
          <div className="detail-item__value">{memory.importance ?? '—'}</div>
        </div>
        <div className="detail-item">
          <div className="detail-item__label">Confidence</div>
          <div className="detail-item__value">{memory.confidence != null ? Number(memory.confidence).toFixed(2) : '—'}</div>
        </div>
        <div className="detail-item">
          <div className="detail-item__label">Workspace</div>
          <div className="detail-item__value text-mono">{memory.workspace_id || '—'}</div>
        </div>
        <div className="detail-item">
          <div className="detail-item__label">Created</div>
          <div className="detail-item__value">{memory.created_at ? new Date(memory.created_at).toLocaleString() : '—'}</div>
        </div>
        <div className="detail-item">
          <div className="detail-item__label">Updated</div>
          <div className="detail-item__value">{memory.updated_at ? new Date(memory.updated_at).toLocaleString() : '—'}</div>
        </div>
      </div>

      {memory.canonical_text && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card__header"><h3 className="card__title">Content</h3></div>
          <div className="markdown-body" style={{ whiteSpace: 'pre-wrap' }}>{memory.canonical_text}</div>
        </div>
      )}

      {memory.evidence && memory.evidence.length > 0 && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card__header">
            <h3 className="card__title">Evidence ({memory.evidence.length})</h3>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {memory.evidence.map((ev, i) => (
              <div key={ev.evidence_id || i} style={{
                background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)',
                padding: '12px 16px', border: '1px solid var(--border)',
              }}>
                <div style={{ display: 'flex', gap: 8, marginBottom: 4, alignItems: 'center' }}>
                  <span className="badge badge--default">{ev.evidence_role || ev.role || '—'}</span>
                  {ev.source_title && <span className="text-muted" style={{ fontSize: '0.78rem' }}>Source: {ev.source_title}</span>}
                </div>
                {ev.chunk_text && (
                  <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.82rem', color: 'var(--text-primary)', lineHeight: 1.5, fontFamily: 'inherit' }}>
                    {ev.chunk_text}
                  </pre>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {memory.revisions && memory.revisions.length > 0 && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card__header">
            <h3 className="card__title">Revisions ({memory.revisions.length})</h3>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {memory.revisions.map((rev, i) => (
              <div key={rev.revision_id || i} style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '8px 12px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)',
              }}>
                <div>
                  <span className="badge badge--info">v{rev.revision_no || rev.version || '?'}</span>
                  <span style={{ marginLeft: 8, fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                    {rev.revision_reason || rev.reason || '—'}
                  </span>
                </div>
                <span className="text-muted" style={{ fontSize: '0.75rem' }}>
                  {rev.created_at ? new Date(rev.created_at).toLocaleString() : '—'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {memory.entities && memory.entities.length > 0 && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card__header">
            <h3 className="card__title">Entities ({memory.entities.length})</h3>
          </div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {memory.entities.map((e, i) => (
              <span key={i} className="badge badge--accent">{e.canonical_name || e.entity_name || e.name || e.entity_id}</span>
            ))}
          </div>
        </div>
      )}

      {memory.scenes && memory.scenes.length > 0 && (
        <div className="card">
          <div className="card__header">
            <h3 className="card__title">Scenes ({memory.scenes.length})</h3>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {memory.scenes.map((sc, i) => (
              <div key={i} style={{ fontSize: '0.85rem' }}>
                <span className="text-muted">{sc.title || sc.scene_label || sc.label || sc.scene_name || `Scene ${i + 1}`}</span>
                {sc.scene_description && <p style={{ marginTop: 2 }}>{sc.scene_description}</p>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
