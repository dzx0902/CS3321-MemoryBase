import { useState, useEffect, useCallback } from 'react';
import { conflictsApi } from '../../api/client';
import { DEMO_WORKSPACE_ID } from '../../api/constants';
import { useToast } from '../../components/Toast';

export default function Conflicts() {
  const [conflicts, setConflicts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [workspaceId, setWorkspaceId] = useState(DEMO_WORKSPACE_ID);
  const toast = useToast();
  const pageSize = 15;

  const fetchConflicts = useCallback(async () => {
    setLoading(true);
    try {
      const data = await conflictsApi.list({
        page, page_size: pageSize,
        workspace_id: workspaceId || undefined,
      });
      setConflicts(data.items || []);
      setTotal(data.total || 0);
    } catch (err) {
      toast.error(err.message || 'Failed to load conflicts');
    } finally {
      setLoading(false);
    }
  }, [page, workspaceId, toast]);

  useEffect(() => { fetchConflicts(); }, [fetchConflicts]);

  const totalPages = Math.ceil(total / pageSize);

  async function handleStatusChange(conflictId, newStatus) {
    try {
      await conflictsApi.update(conflictId, { workspace_id: workspaceId }, { status: newStatus });
      toast.success(`Conflict ${newStatus}`);
      fetchConflicts();
    } catch (err) {
      toast.error(err.message || 'Failed to update conflict');
    }
  }

  return (
    <div>
      <div className="section-header">
        <h1><span className="icon">⚠</span> Conflicts</h1>
      </div>

      <div className="filter-bar">
        <input className="input" placeholder="Workspace ID..." value={workspaceId}
          onChange={(e) => { setWorkspaceId(e.target.value); setPage(1); }} style={{ minWidth: 200 }} />
      </div>

      {loading ? (
        <div className="loading"><div className="spinner" />Loading conflicts...</div>
      ) : conflicts.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state__icon">⚠</div>
          <div className="empty-state__title">No conflicts detected</div>
          <p className="text-muted">Memory conflicts will appear here when detected by the system.</p>
        </div>
      ) : (
        <>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {conflicts.map((c) => (
              <div key={c.conflict_id} className="card" style={{ padding: '18px 22px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
                  <div>
                    <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 4 }}>
                      <span className={`badge ${c.status === 'open' ? 'badge--danger' : c.status === 'resolved' ? 'badge--success' : 'badge--default'}`}>
                        {c.status || '—'}
                      </span>
                      <span className="text-mono" style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                        {c.conflict_id}
                      </span>
                    </div>
                    <div style={{ fontWeight: 500 }}>{c.conflict_type || 'Untitled conflict'}</div>
                  </div>
                  <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                    {c.status === 'open' && (
                      <>
                        <button className="btn btn--sm" style={{ borderColor: 'var(--success)', color: 'var(--success)' }}
                          onClick={() => handleStatusChange(c.conflict_id, 'resolved')}>Resolve</button>
                        <button className="btn btn--sm" style={{ borderColor: 'var(--text-muted)', color: 'var(--text-muted)' }}
                          onClick={() => handleStatusChange(c.conflict_id, 'ignored')}>Ignore</button>
                      </>
                    )}
                    {c.status !== 'open' && (
                      <button className="btn btn--sm" style={{ borderColor: 'var(--danger)', color: 'var(--danger)' }}
                        onClick={() => handleStatusChange(c.conflict_id, 'open')}>Reopen</button>
                    )}
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 8, fontSize: '0.8rem' }}>
                  {c.left_memory_id && (
                    <div className="detail-item">
                      <div className="detail-item__label">Memory A</div>
                      <div className="detail-item__value text-mono">{c.left_memory_id}</div>
                    </div>
                  )}
                  {c.right_memory_id && (
                    <div className="detail-item">
                      <div className="detail-item__label">Memory B</div>
                      <div className="detail-item__value text-mono">{c.right_memory_id}</div>
                    </div>
                  )}
                  {c.workspace_id && (
                    <div className="detail-item">
                      <div className="detail-item__label">Workspace</div>
                      <div className="detail-item__value">{c.workspace_id}</div>
                    </div>
                  )}
                  {c.created_at && (
                    <div className="detail-item">
                      <div className="detail-item__label">Detected</div>
                      <div className="detail-item__value">{new Date(c.created_at).toLocaleString()}</div>
                    </div>
                  )}
                </div>
              </div>
            ))}
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
