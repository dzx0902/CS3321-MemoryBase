import { useState, useEffect, useCallback } from 'react';
import { forgetRequestsApi } from '../../api/client';
import { DEMO_USER_ID, DEMO_WORKSPACE_ID } from '../../api/constants';
import { useToast } from '../../components/Toast';

const TARGET_TYPES = ['memory_item', 'source_document', 'wiki_page', 'entity'];
const REQUEST_STATUSES = ['', 'pending', 'approved', 'rejected', 'done'];

export default function ForgetRequests() {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [filters, setFilters] = useState({ workspace_id: DEMO_WORKSPACE_ID, status: '', target_type: '' });
  const [showCreate, setShowCreate] = useState(false);
  const toast = useToast();
  const pageSize = 15;

  const fetchRequests = useCallback(async () => {
    setLoading(true);
    try {
      const data = await forgetRequestsApi.list({
        page,
        page_size: pageSize,
        workspace_id: filters.workspace_id || undefined,
        status: filters.status || undefined,
        target_type: filters.target_type || undefined,
      });
      setRequests(data.items || []);
      setTotal(data.total || 0);
    } catch (err) {
      toast.error(err.message || 'Failed to load forget requests');
    } finally {
      setLoading(false);
    }
  }, [page, filters, toast]);

  useEffect(() => { fetchRequests(); }, [fetchRequests]);

  const totalPages = Math.ceil(total / pageSize);
  const updateFilter = (key, value) => { setFilters((f) => ({ ...f, [key]: value })); setPage(1); };

  async function handleUpdate(request, newStatus) {
    try {
      await forgetRequestsApi.update(
        request.request_id,
        { workspace_id: request.workspace_id },
        { status: newStatus, reviewed_by_user_id: DEMO_USER_ID },
      );
      toast.success(`Request ${newStatus}`);
      fetchRequests();
    } catch (err) {
      toast.error(err.message || 'Failed to update request');
    }
  }

  return (
    <div>
      <div className="section-header">
        <h1><span className="icon">⌫</span> Forget Requests</h1>
        <button className="btn btn--primary" onClick={() => setShowCreate(!showCreate)}>
          {showCreate ? 'Cancel' : '+ New Request'}
        </button>
      </div>

      {showCreate && (
        <ForgetRequestCreateForm
          workspaceId={filters.workspace_id}
          onSuccess={() => { setShowCreate(false); fetchRequests(); }}
        />
      )}

      <div className="filter-bar">
        <input className="input" placeholder="Workspace..." value={filters.workspace_id}
          onChange={(e) => updateFilter('workspace_id', e.target.value)} style={{ minWidth: 160 }} />
        <select className="select" value={filters.status}
          onChange={(e) => updateFilter('status', e.target.value)} style={{ minWidth: 120 }}>
          <option value="">All Statuses</option>
          {REQUEST_STATUSES.filter(Boolean).map((status) => <option key={status} value={status}>{status}</option>)}
        </select>
        <select className="select" value={filters.target_type}
          onChange={(e) => updateFilter('target_type', e.target.value)} style={{ minWidth: 150 }}>
          <option value="">All Targets</option>
          {TARGET_TYPES.map((type) => <option key={type} value={type}>{type}</option>)}
        </select>
      </div>

      {loading ? (
        <div className="loading"><div className="spinner" />Loading forget requests...</div>
      ) : requests.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state__icon">⌫</div>
          <div className="empty-state__title">No forget requests</div>
        </div>
      ) : (
        <>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Target</th>
                  <th>Status</th>
                  <th>Requester</th>
                  <th>Reason</th>
                  <th>Requested</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {requests.map((request) => (
                  <tr key={request.request_id}>
                    <td>
                      <span className="badge badge--default">{request.target_type || '-'}</span>
                      <span className="text-mono" style={{ marginLeft: 6, fontSize: '0.75rem' }}>{request.target_id || '-'}</span>
                    </td>
                    <td>
                      <span className={`badge ${request.status === 'approved' || request.status === 'done' ? 'badge--success' : request.status === 'rejected' ? 'badge--danger' : 'badge--info'}`}>
                        {request.status || '-'}
                      </span>
                    </td>
                    <td className="text-muted">{request.requester_user_id || '-'}</td>
                    <td className="text-muted" style={{ maxWidth: 250, fontSize: '0.8rem' }}>
                      {request.reason || '-'}
                    </td>
                    <td className="text-muted">{request.requested_at ? new Date(request.requested_at).toLocaleString() : '-'}</td>
                    <td>
                      {request.status === 'pending' && (
                        <div style={{ display: 'flex', gap: 4 }}>
                          <button className="btn btn--sm" style={{ borderColor: 'var(--success)', color: 'var(--success)' }}
                            onClick={() => handleUpdate(request, 'approved')}>Approve</button>
                          <button className="btn btn--sm" style={{ borderColor: 'var(--danger)', color: 'var(--danger)' }}
                            onClick={() => handleUpdate(request, 'rejected')}>Reject</button>
                        </div>
                      )}
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

function ForgetRequestCreateForm({ workspaceId, onSuccess }) {
  const toast = useToast();
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({
    workspace_id: workspaceId || DEMO_WORKSPACE_ID,
    target_type: 'memory_item',
    target_id: '',
    reason: '',
    requester_user_id: DEMO_USER_ID,
  });

  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await forgetRequestsApi.create({
        workspace_id: form.workspace_id,
        target_type: form.target_type,
        target_id: form.target_id,
        reason: form.reason,
        requester_user_id: form.requester_user_id || null,
      });
      toast.success('Forget request created');
      onSuccess();
    } catch (err) {
      toast.error(err.message || 'Failed to create request');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="card" style={{ marginBottom: 20 }}>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 20px' }}>
        <div className="form-group">
          <label>Workspace</label>
          <input className="input" value={form.workspace_id}
            onChange={(e) => setForm((f) => ({ ...f, workspace_id: e.target.value }))} required />
        </div>
        <div className="form-group">
          <label>Target Type</label>
          <select className="select" value={form.target_type}
            onChange={(e) => setForm((f) => ({ ...f, target_type: e.target.value }))}>
            {TARGET_TYPES.map((type) => <option key={type} value={type}>{type}</option>)}
          </select>
        </div>
        <div className="form-group">
          <label>Target ID</label>
          <input className="input" value={form.target_id}
            onChange={(e) => setForm((f) => ({ ...f, target_id: e.target.value }))} required />
        </div>
        <div className="form-group">
          <label>Requester User ID</label>
          <input className="input" value={form.requester_user_id}
            onChange={(e) => setForm((f) => ({ ...f, requester_user_id: e.target.value }))} />
        </div>
      </div>
      <div className="form-group">
        <label>Reason</label>
        <textarea className="textarea" rows={2} value={form.reason}
          onChange={(e) => setForm((f) => ({ ...f, reason: e.target.value }))} required />
      </div>
      <button type="submit" className="btn btn--primary" disabled={submitting}>
        {submitting ? 'Creating...' : 'Submit Forget Request'}
      </button>
    </form>
  );
}
