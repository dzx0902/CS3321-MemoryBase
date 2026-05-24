import { useState, useEffect } from 'react';
import { useParams, Link, useSearchParams } from 'react-router-dom';
import { sourcesApi } from '../../api/client';
import { useToast } from '../../components/Toast';

export default function SourceDetail() {
  const { docId } = useParams();
  const [searchParams] = useSearchParams();
  const workspaceId = searchParams.get('workspace_id');
  const [source, setSource] = useState(null);
  const [loading, setLoading] = useState(true);
  const toast = useToast();

  useEffect(() => {
    async function load() {
      if (!workspaceId) {
        toast.error('Missing workspace_id in URL');
        setLoading(false);
        return;
      }
      try {
        const data = await sourcesApi.detail(docId, { workspace_id: workspaceId });
        setSource(data);
      } catch (err) {
        toast.error(err.message || 'Failed to load source');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [docId, workspaceId, toast]);

  if (loading) {
    return <div className="loading"><div className="spinner" />Loading source...</div>;
  }
  if (!source) {
    return <div className="empty-state"><div className="empty-state__title">Source not found</div></div>;
  }

  return (
    <div>
      <div className="section-header">
        <h1><span className="icon">▤</span> {source.title || 'Untitled'}</h1>
        <Link to="/sources" className="btn">← Back to Sources</Link>
      </div>

      <div className="detail-grid">
        <div className="detail-item">
          <div className="detail-item__label">Document ID</div>
          <div className="detail-item__value text-mono">{source.doc_id}</div>
        </div>
        <div className="detail-item">
          <div className="detail-item__label">Type</div>
          <div className="detail-item__value"><span className="badge badge--accent">{source.doc_type || '—'}</span></div>
        </div>
        <div className="detail-item">
          <div className="detail-item__label">Workspace</div>
          <div className="detail-item__value">{source.workspace_id || '—'}</div>
        </div>
        <div className="detail-item">
          <div className="detail-item__label">Source Path</div>
          <div className="detail-item__value text-mono">{source.source_path || '—'}</div>
        </div>
        <div className="detail-item">
          <div className="detail-item__label">Created</div>
          <div className="detail-item__value">{source.imported_at ? new Date(source.imported_at).toLocaleString() : '—'}</div>
        </div>
        <div className="detail-item">
          <div className="detail-item__label">Chunks</div>
          <div className="detail-item__value">{source.chunks?.length || 0}</div>
        </div>
      </div>

      {source.raw_text && (
        <div className="card" style={{ marginBottom: 24 }}>
          <div className="card__header">
            <h3 className="card__title">Raw Text</h3>
          </div>
          <pre className="markdown-body" style={{ whiteSpace: 'pre-wrap', fontSize: '0.85rem', maxHeight: 400, overflowY: 'auto' }}>
            {source.raw_text}
          </pre>
        </div>
      )}

      {source.chunks && source.chunks.length > 0 && (
        <div className="card">
          <div className="card__header">
            <h3 className="card__title">Chunks ({source.chunks.length})</h3>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {source.chunks.map((chunk) => (
              <div key={chunk.chunk_id} style={{
                background: 'var(--bg-secondary)',
                borderRadius: 'var(--radius-md)',
                padding: '14px 18px',
                border: '1px solid var(--border)',
              }}>
                <div style={{ display: 'flex', gap: 12, marginBottom: 6, alignItems: 'center' }}>
                  <span className="badge badge--info">Chunk {chunk.chunk_no}</span>
                  <span className="text-muted" style={{ fontSize: '0.75rem' }}>
                    Lines {chunk.start_line ?? '-'}-{chunk.end_line ?? '-'}
                  </span>
                  <span className="text-muted" style={{ fontSize: '0.75rem' }}>
                    {chunk.token_count} tokens
                  </span>
                </div>
                <pre style={{
                  whiteSpace: 'pre-wrap',
                  fontSize: '0.83rem',
                  color: 'var(--text-primary)',
                  lineHeight: 1.6,
                  fontFamily: 'inherit',
                }}>
                  {chunk.chunk_text}
                </pre>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
