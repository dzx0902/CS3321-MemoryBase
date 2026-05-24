import { useState, useEffect, useCallback } from 'react';
import { timelineApi } from '../../api/client';
import { DEMO_WORKSPACE_ID } from '../../api/constants';
import { useToast } from '../../components/Toast';

const EVENT_TYPES = ['meeting', 'proposal', 'decision', 'revision', 'conflict', 'resolution'];

export default function Timeline() {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [workspaceId, setWorkspaceId] = useState(DEMO_WORKSPACE_ID);
  const [showCreate, setShowCreate] = useState(false);
  const toast = useToast();
  const pageSize = 20;

  const fetchTimeline = useCallback(async () => {
    setLoading(true);
    try {
      const data = await timelineApi.list({
        page,
        page_size: pageSize,
        workspace_id: workspaceId || undefined,
      });
      setEntries(data.items || []);
      setTotal(data.total || 0);
    } catch (err) {
      toast.error(err.message || 'Failed to load timeline');
    } finally {
      setLoading(false);
    }
  }, [page, workspaceId, toast]);

  useEffect(() => { fetchTimeline(); }, [fetchTimeline]);

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div>
      <div className="section-header">
        <h1><span className="icon">↗</span> Timeline</h1>
        <button className="btn btn--primary" onClick={() => setShowCreate(!showCreate)}>
          {showCreate ? 'Cancel' : '+ Add Entry'}
        </button>
      </div>

      {showCreate && (
        <TimelineCreateForm
          workspaceId={workspaceId}
          onSuccess={() => { setShowCreate(false); fetchTimeline(); }}
        />
      )}

      <div className="filter-bar">
        <input className="input" placeholder="Workspace ID..." value={workspaceId}
          onChange={(e) => { setWorkspaceId(e.target.value); setPage(1); }} style={{ minWidth: 200 }} />
      </div>

      {loading ? (
        <div className="loading"><div className="spinner" />Loading timeline...</div>
      ) : entries.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state__icon">↗</div>
          <div className="empty-state__title">No timeline entries</div>
        </div>
      ) : (
        <>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Event</th>
                  <th>Type</th>
                  <th>Workspace</th>
                  <th>Linked Item</th>
                  <th>Timestamp</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((entry) => (
                  <tr key={entry.timeline_id}>
                    <td style={{ maxWidth: 400 }}>
                      <div style={{ fontWeight: 500 }}>{entry.title || '-'}</div>
                      {entry.description && <div className="text-muted" style={{ fontSize: '0.8rem', marginTop: 2 }}>{entry.description}</div>}
                    </td>
                    <td><span className="badge badge--accent">{entry.event_type || '-'}</span></td>
                    <td className="text-mono text-muted">{entry.workspace_id || '-'}</td>
                    <td className="text-muted">{entry.memory_id || entry.doc_id || '-'}</td>
                    <td className="text-muted">{entry.event_time ? new Date(entry.event_time).toLocaleString() : '-'}</td>
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

function TimelineCreateForm({ workspaceId, onSuccess }) {
  const toast = useToast();
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({
    workspace_id: workspaceId || DEMO_WORKSPACE_ID,
    event_type: 'decision',
    title: '',
    description: '',
    importance: 3,
    event_time: new Date().toISOString().slice(0, 16),
  });

  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await timelineApi.create({
        workspace_id: form.workspace_id,
        event_type: form.event_type,
        title: form.title,
        description: form.description || null,
        importance: Number(form.importance),
        event_time: new Date(form.event_time).toISOString(),
      });
      toast.success('Timeline entry created');
      onSuccess();
    } catch (err) {
      toast.error(err.message || 'Failed to create entry');
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
          <label>Event Type</label>
          <select className="select" value={form.event_type}
            onChange={(e) => setForm((f) => ({ ...f, event_type: e.target.value }))}>
            {EVENT_TYPES.map((type) => <option key={type} value={type}>{type}</option>)}
          </select>
        </div>
        <div className="form-group">
          <label>Title</label>
          <input className="input" value={form.title}
            onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))} required />
        </div>
        <div className="form-group">
          <label>Importance (1-5)</label>
          <input className="input" type="number" min="1" max="5" value={form.importance}
            onChange={(e) => setForm((f) => ({ ...f, importance: e.target.value }))} />
        </div>
        <div className="form-group">
          <label>Event Time</label>
          <input className="input" type="datetime-local" value={form.event_time}
            onChange={(e) => setForm((f) => ({ ...f, event_time: e.target.value }))} />
        </div>
      </div>
      <div className="form-group">
        <label>Description</label>
        <textarea className="textarea" rows={2} value={form.description}
          onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} />
      </div>
      <button type="submit" className="btn btn--primary" disabled={submitting}>
        {submitting ? 'Creating...' : 'Create Entry'}
      </button>
    </form>
  );
}
