import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { memoriesApi } from '../../api/client';
import { useToast } from '../../components/Toast';

const MEMORY_TYPES = ['', 'episodic', 'semantic', 'fact', 'profile', 'procedural', 'decision', 'preference', 'task', 'risk', 'constraint', 'policy', 'summary'];
const STATUS_OPTIONS = [
  { value: '', label: 'Active (default)' },
  { value: 'all', label: 'All Statuses' },
  { value: 'candidate', label: 'candidate' },
  { value: 'active', label: 'active' },
  { value: 'archived', label: 'archived' },
  { value: 'forgotten', label: 'forgotten' },
  { value: 'superseded', label: 'superseded' },
  { value: 'rejected', label: 'rejected' },
  { value: 'conflicted', label: 'conflicted' },
];

export default function MemoryList() {
  const [memories, setMemories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [filters, setFilters] = useState({ keyword: '', memory_type: '', status: '', workspace_id: '' });
  const pageSize = 15;
  const toast = useToast();

  const fetchMemories = useCallback(async () => {
    setLoading(true);
    try {
      const data = await memoriesApi.list({
        page, page_size: pageSize,
        keyword: filters.keyword || undefined,
        memory_type: filters.memory_type || undefined,
        status: filters.status || undefined,
        workspace_id: filters.workspace_id || undefined,
      });
      setMemories(data.items || []);
      setTotal(data.total || 0);
    } catch (err) {
      toast.error(err.message || 'Failed to load memories');
    } finally {
      setLoading(false);
    }
  }, [page, filters, toast]);

  useEffect(() => { fetchMemories(); }, [fetchMemories]);

  const totalPages = Math.ceil(total / pageSize);
  const updateFilter = (key, value) => { setFilters((f) => ({ ...f, [key]: value })); setPage(1); };
  const memoryHref = (memory) =>
    `/memories/${memory.memory_id}${memory.workspace_id ? `?workspace_id=${memory.workspace_id}` : ''}`;

  return (
    <div>
      <div className="section-header">
        <h1><span className="icon">◈</span> Memories</h1>
        <Link to="/memories/new" className="btn btn--primary">+ New Memory</Link>
      </div>

      <div className="filter-bar">
        <input className="input" placeholder="Keyword..." value={filters.keyword}
          onChange={(e) => updateFilter('keyword', e.target.value)} style={{ minWidth: 200 }} />
        <select className="select" value={filters.memory_type}
          onChange={(e) => updateFilter('memory_type', e.target.value)} style={{ minWidth: 150 }}>
          <option value="">All Types</option>
          {MEMORY_TYPES.filter(Boolean).map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        <select className="select" value={filters.status}
          onChange={(e) => updateFilter('status', e.target.value)} style={{ minWidth: 140 }}>
          {STATUS_OPTIONS.map((status) => <option key={status.label} value={status.value}>{status.label}</option>)}
        </select>
        <input className="input" placeholder="Workspace ID..." value={filters.workspace_id}
          onChange={(e) => updateFilter('workspace_id', e.target.value)} style={{ minWidth: 160 }} />
      </div>

      {loading ? (
        <div className="loading"><div className="spinner" />Loading memories...</div>
      ) : memories.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state__icon">◈</div>
          <div className="empty-state__title">No memories found</div>
          <p className="text-muted">Create your first memory to get started.</p>
          <Link to="/memories/new" className="btn btn--primary" style={{ marginTop: 16 }}>+ New Memory</Link>
        </div>
      ) : (
        <>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th>Confidence</th>
                  <th>Importance</th>
                  <th>Workspace</th>
                  <th>Updated</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {memories.map((m) => (
                  <tr key={m.memory_id}>
                    <td>
                      <Link to={memoryHref(m)} style={{ fontWeight: 500 }}>
                        {m.summary || m.canonical_text || 'Untitled'}
                      </Link>
                    </td>
                    <td><span className="badge badge--accent">{m.memory_type || '—'}</span></td>
                    <td>
                      <span className={`badge ${m.status === 'active' ? 'badge--success' : m.status === 'conflicted' ? 'badge--danger' : 'badge--default'}`}>
                        {m.status || '—'}
                      </span>
                    </td>
                    <td className="text-muted">{m.confidence != null ? Number(m.confidence).toFixed(2) : '—'}</td>
                    <td className="text-muted">{m.importance ?? '—'}</td>
                    <td className="text-mono text-muted" style={{ fontSize: '0.75rem' }}>{m.workspace_id || '—'}</td>
                    <td className="text-muted">{m.updated_at ? new Date(m.updated_at).toLocaleDateString() : '—'}</td>
                    <td>
                      <Link to={memoryHref(m)} className="btn btn--sm">View</Link>
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
