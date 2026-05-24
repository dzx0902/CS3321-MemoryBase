import { useState, useEffect, useCallback } from 'react';
import { policiesApi } from '../../api/client';
import { DEMO_WORKSPACE_ID } from '../../api/constants';
import { useToast } from '../../components/Toast';

const EFFECTS = ['allow', 'deny'];
const PRINCIPAL_TYPES = ['user', 'agent', 'role'];
const RESOURCE_TYPES = ['memory_item', 'source_document', 'wiki_page', 'workspace'];
const RESOURCE_SCOPES = ['public', 'project', 'team', 'private', 'all'];

export default function Policies() {
  const [policies, setPolicies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [workspaceId, setWorkspaceId] = useState(DEMO_WORKSPACE_ID);
  const [showCreate, setShowCreate] = useState(false);
  const toast = useToast();
  const pageSize = 15;

  const fetchPolicies = useCallback(async () => {
    setLoading(true);
    try {
      const data = await policiesApi.list({
        page,
        page_size: pageSize,
        workspace_id: workspaceId || undefined,
      });
      setPolicies(data.items || []);
      setTotal(data.total || 0);
    } catch (err) {
      toast.error(err.message || 'Failed to load policies');
    } finally {
      setLoading(false);
    }
  }, [page, workspaceId, toast]);

  useEffect(() => { fetchPolicies(); }, [fetchPolicies]);

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div>
      <div className="section-header">
        <h1><span className="icon">▣</span> Access Policies</h1>
        <button className="btn btn--primary" onClick={() => setShowCreate(!showCreate)}>
          {showCreate ? 'Cancel' : '+ New Policy'}
        </button>
      </div>

      {showCreate && (
        <PolicyCreateForm
          workspaceId={workspaceId}
          onSuccess={() => { setShowCreate(false); fetchPolicies(); }}
        />
      )}

      <div className="filter-bar">
        <input className="input" placeholder="Workspace ID..." value={workspaceId}
          onChange={(e) => { setWorkspaceId(e.target.value); setPage(1); }} style={{ minWidth: 200 }} />
      </div>

      {loading ? (
        <div className="loading"><div className="spinner" />Loading policies...</div>
      ) : policies.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state__icon">▣</div>
          <div className="empty-state__title">No policies found</div>
        </div>
      ) : (
        <>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Principal</th>
                  <th>Resource</th>
                  <th>Effect</th>
                  <th>Scope</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {policies.map((p) => (
                  <tr key={p.policy_id}>
                    <td>
                      <span className="badge badge--info">{p.principal_type || '-'}</span>
                      <span className="text-mono" style={{ marginLeft: 6, fontSize: '0.75rem' }}>{p.principal_id || 'all'}</span>
                    </td>
                    <td>
                      <span className="text-muted" style={{ fontSize: '0.75rem' }}>{p.resource_type || '-'}</span>
                    </td>
                    <td>
                      <span className={`badge ${p.effect === 'deny' ? 'badge--danger' : 'badge--success'}`}>
                        {p.effect || '-'}
                      </span>
                    </td>
                    <td><span className="badge badge--default">{p.resource_scope || '-'}</span></td>
                    <td className="text-muted">{p.created_at ? new Date(p.created_at).toLocaleString() : '-'}</td>
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

function PolicyCreateForm({ workspaceId, onSuccess }) {
  const toast = useToast();
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({
    workspace_id: workspaceId || DEMO_WORKSPACE_ID,
    principal_type: 'user',
    principal_id: '',
    resource_type: 'memory_item',
    effect: 'allow',
    resource_scope: 'project',
    predicate_json: '{}',
  });

  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await policiesApi.create({
        workspace_id: form.workspace_id,
        principal_type: form.principal_type,
        principal_id: form.principal_id || null,
        resource_type: form.resource_type,
        effect: form.effect,
        resource_scope: form.resource_scope,
        predicate_json: form.predicate_json ? JSON.parse(form.predicate_json) : {},
      });
      toast.success('Policy created');
      onSuccess();
    } catch (err) {
      toast.error(err.message || 'Failed to create policy');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="card" style={{ marginBottom: 20 }}>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0 20px' }}>
        <div className="form-group">
          <label>Workspace</label>
          <input className="input" value={form.workspace_id}
            onChange={(e) => setForm((f) => ({ ...f, workspace_id: e.target.value }))} required />
        </div>
        <div className="form-group">
          <label>Principal Type</label>
          <select className="select" value={form.principal_type}
            onChange={(e) => setForm((f) => ({ ...f, principal_type: e.target.value }))}>
            {PRINCIPAL_TYPES.map((type) => <option key={type} value={type}>{type}</option>)}
          </select>
        </div>
        <div className="form-group">
          <label>Principal ID</label>
          <input className="input" value={form.principal_id}
            onChange={(e) => setForm((f) => ({ ...f, principal_id: e.target.value }))} />
        </div>
        <div className="form-group">
          <label>Resource Type</label>
          <select className="select" value={form.resource_type}
            onChange={(e) => setForm((f) => ({ ...f, resource_type: e.target.value }))}>
            {RESOURCE_TYPES.map((type) => <option key={type} value={type}>{type}</option>)}
          </select>
        </div>
        <div className="form-group">
          <label>Effect</label>
          <select className="select" value={form.effect}
            onChange={(e) => setForm((f) => ({ ...f, effect: e.target.value }))}>
            {EFFECTS.map((effect) => <option key={effect} value={effect}>{effect}</option>)}
          </select>
        </div>
        <div className="form-group">
          <label>Scope</label>
          <select className="select" value={form.resource_scope}
            onChange={(e) => setForm((f) => ({ ...f, resource_scope: e.target.value }))}>
            {RESOURCE_SCOPES.map((scope) => <option key={scope} value={scope}>{scope}</option>)}
          </select>
        </div>
      </div>
      <div className="form-group">
        <label>Predicate JSON</label>
        <textarea className="textarea text-mono" rows={2} value={form.predicate_json}
          onChange={(e) => setForm((f) => ({ ...f, predicate_json: e.target.value }))} />
      </div>
      <button type="submit" className="btn btn--primary" disabled={submitting} style={{ marginTop: 8 }}>
        {submitting ? 'Creating...' : 'Create Policy'}
      </button>
    </form>
  );
}
