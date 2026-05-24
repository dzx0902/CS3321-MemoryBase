import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { sourcesApi } from '../../api/client';
import { useToast } from '../../components/Toast';

export default function SourceList() {
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [keyword, setKeyword] = useState('');
  const [workspaceId, setWorkspaceId] = useState('');
  const pageSize = 15;
  const toast = useToast();

  const fetchSources = useCallback(async () => {
    setLoading(true);
    try {
      const data = await sourcesApi.list({ page, page_size: pageSize, keyword: keyword || undefined, workspace_id: workspaceId || undefined });
      setSources(data.items || []);
      setTotal(data.total || 0);
    } catch (err) {
      toast.error(err.message || 'Failed to load sources');
    } finally {
      setLoading(false);
    }
  }, [page, keyword, workspaceId, toast]);

  useEffect(() => { fetchSources(); }, [fetchSources]);

  const totalPages = Math.ceil(total / pageSize);
  const sourceHref = (source) =>
    `/sources/${source.doc_id}${source.workspace_id ? `?workspace_id=${source.workspace_id}` : ''}`;

  return (
    <div>
      <div className="section-header">
        <h1><span className="icon">▤</span> Sources</h1>
      </div>

      <div className="filter-bar">
        <input
          className="input"
          placeholder="Search keyword..."
          value={keyword}
          onChange={(e) => { setKeyword(e.target.value); setPage(1); }}
          style={{ minWidth: 220 }}
        />
        <input
          className="input"
          placeholder="Workspace ID..."
          value={workspaceId}
          onChange={(e) => { setWorkspaceId(e.target.value); setPage(1); }}
          style={{ minWidth: 180 }}
        />
      </div>

      {loading ? (
        <div className="loading"><div className="spinner" />Loading sources...</div>
      ) : sources.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state__icon">▤</div>
          <div className="empty-state__title">No sources found</div>
          <p className="text-muted">Import source documents via the API to see them here.</p>
        </div>
      ) : (
        <>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Type</th>
                  <th>Workspace</th>
                  <th>Created</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {sources.map((s) => (
                  <tr key={s.doc_id}>
                    <td>
                      <Link to={sourceHref(s)} style={{ fontWeight: 500 }}>
                        {s.title || 'Untitled'}
                      </Link>
                    </td>
                    <td><span className="badge badge--default">{s.doc_type || '—'}</span></td>
                    <td><span className="text-mono text-muted">{s.workspace_id || '—'}</span></td>
                    <td className="text-muted">{s.imported_at ? new Date(s.imported_at).toLocaleDateString() : '—'}</td>
                    <td>
                      <Link to={sourceHref(s)} className="btn btn--sm">
                        View
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="pagination">
              <button disabled={page <= 1} onClick={() => setPage(page - 1)}>← Previous</button>
              <span className="text-muted" style={{ padding: '0 12px', fontSize: '0.82rem' }}>
                Page {page} of {totalPages}
              </span>
              <button disabled={page >= totalPages} onClick={() => setPage(page + 1)}>Next →</button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
