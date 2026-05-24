import { useState, useEffect, useCallback } from 'react';
import { auditApi } from '../../api/client';
import { useToast } from '../../components/Toast';

const ACTION_TYPES = ['', 'create', 'update', 'delete', 'read', 'export', 'approve', 'reject', 'forget', 'resolve'];
const ACTOR_TYPES = ['', 'user', 'agent', 'system'];

function auditDetails(entry) {
  const detail = entry.diff_json || entry.after_json || entry.before_json;
  if (!detail) return '';
  return JSON.stringify(detail);
}

export default function Audit() {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [filters, setFilters] = useState({
    workspace_id: '', actor_type: '', action_type: '', target_id: '',
    start_time: '', end_time: '',
  });
  const toast = useToast();
  const pageSize = 20;

  const fetchAudit = useCallback(async () => {
    setLoading(true);
    try {
      const data = await auditApi.list({
        page, page_size: pageSize,
        workspace_id: filters.workspace_id || undefined,
        actor_type: filters.actor_type || undefined,
        action_type: filters.action_type || undefined,
        target_id: filters.target_id || undefined,
        start_time: filters.start_time || undefined,
        end_time: filters.end_time || undefined,
        include_diff: true,
      });
      setEntries(data.items || []);
      setTotal(data.total || 0);
    } catch (err) {
      toast.error(err.message || 'Failed to load audit log');
    } finally {
      setLoading(false);
    }
  }, [page, filters, toast]);

  useEffect(() => { fetchAudit(); }, [fetchAudit]);

  const totalPages = Math.ceil(total / pageSize);
  const updateFilter = (key, value) => { setFilters((f) => ({ ...f, [key]: value })); setPage(1); };

  return (
    <div>
      <div className="section-header">
        <h1><span className="icon">A</span> Audit Log</h1>
      </div>

      <div className="filter-bar">
        <input className="input" placeholder="Workspace..." value={filters.workspace_id}
          onChange={(e) => updateFilter('workspace_id', e.target.value)} style={{ minWidth: 150 }} />
        <select className="select" value={filters.actor_type}
          onChange={(e) => updateFilter('actor_type', e.target.value)} style={{ minWidth: 120 }}>
          <option value="">All Actors</option>
          {ACTOR_TYPES.filter(Boolean).map((a) => <option key={a} value={a}>{a}</option>)}
        </select>
        <select className="select" value={filters.action_type}
          onChange={(e) => updateFilter('action_type', e.target.value)} style={{ minWidth: 120 }}>
          <option value="">All Actions</option>
          {ACTION_TYPES.filter(Boolean).map((a) => <option key={a} value={a}>{a}</option>)}
        </select>
        <input className="input" placeholder="Target ID..." value={filters.target_id}
          onChange={(e) => updateFilter('target_id', e.target.value)} style={{ minWidth: 140 }} />
        <input className="input" type="datetime-local" value={filters.start_time}
          onChange={(e) => updateFilter('start_time', e.target.value)} style={{ minWidth: 170 }} title="Start time" />
        <input className="input" type="datetime-local" value={filters.end_time}
          onChange={(e) => updateFilter('end_time', e.target.value)} style={{ minWidth: 170 }} title="End time" />
      </div>

      {loading ? (
        <div className="loading"><div className="spinner" />Loading audit log...</div>
      ) : entries.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state__icon">A</div>
          <div className="empty-state__title">No audit entries</div>
        </div>
      ) : (
        <>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Action</th>
                  <th>Actor</th>
                  <th>Target</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((e, i) => (
                  <tr key={e.audit_id || i}>
                    <td className="text-muted" style={{ whiteSpace: 'nowrap' }}>
                      {e.created_at ? new Date(e.created_at).toLocaleString() : '-'}
                    </td>
                    <td><span className={`badge ${e.action_type === 'delete' || e.action_type === 'forget' ? 'badge--danger' : e.action_type === 'create' ? 'badge--success' : 'badge--default'}`}>{e.action_type || '-'}</span></td>
                    <td>
                      <span className="badge badge--info">{e.actor_type || '-'}</span>
                      <span className="text-mono" style={{ marginLeft: 6, fontSize: '0.75rem' }}>{e.actor_id || '-'}</span>
                    </td>
                    <td>
                      <span className="text-muted" style={{ fontSize: '0.75rem' }}>{e.target_type || '-'}</span>
                      <span className="text-mono" style={{ marginLeft: 6, fontSize: '0.72rem' }}>{e.target_id || '-'}</span>
                    </td>
                    <td className="text-muted" style={{ maxWidth: 300, fontSize: '0.8rem' }}>
                      {auditDetails(e) || '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="pagination">
              <button disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button>
              <span className="text-muted" style={{ padding: '0 12px', fontSize: '0.82rem' }}>
                Page {page} of {totalPages}
              </span>
              <button disabled={page >= totalPages} onClick={() => setPage(page + 1)}>Next</button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
