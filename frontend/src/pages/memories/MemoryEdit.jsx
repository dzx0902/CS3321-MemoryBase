import { useState, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { memoriesApi } from '../../api/client';
import { useToast } from '../../components/Toast';

const MEMORY_TYPES = ['episodic', 'semantic', 'fact', 'profile', 'procedural', 'decision', 'preference', 'task', 'risk', 'constraint', 'policy', 'summary'];
const ACCESS_LEVELS = ['public', 'project', 'team', 'private'];
const STATUSES = ['active', 'archived', 'forgotten', 'superseded', 'conflicted'];

export default function MemoryEdit() {
  const { memoryId } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const workspaceId = searchParams.get('workspace_id');
  const toast = useToast();
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState(null);

  useEffect(() => {
    async function load() {
      if (!workspaceId) {
        toast.error('Missing workspace_id in URL');
        setLoading(false);
        return;
      }
      try {
        const data = await memoriesApi.detail(memoryId, { workspace_id: workspaceId });
        setForm({
          memory_type: data.memory_type || 'semantic',
          status: data.status || 'active',
          canonical_text: data.canonical_text || '',
          summary: data.summary || '',
          importance: data.importance ?? 3,
          access_level: data.access_level || 'project',
          revision_reason: '',
        });
      } catch (err) {
        toast.error(err.message || 'Failed to load memory');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [memoryId, workspaceId, toast]);

  function updateField(key, value) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await memoriesApi.update(memoryId, {
        status: form.status,
        canonical_text: form.canonical_text,
        summary: form.summary || null,
        importance: Number(form.importance),
        access_level: form.access_level,
      }, { workspace_id: workspaceId }, {
        actorType: 'user',
        revisionReason: form.revision_reason || 'Manual edit',
      });
      toast.success('Memory updated successfully');
      navigate(`/memories/${memoryId}?workspace_id=${workspaceId}`);
    } catch (err) {
      toast.error(err.message || 'Failed to update memory');
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) return <div className="loading"><div className="spinner" />Loading memory...</div>;
  if (!form) return <div className="empty-state"><div className="empty-state__title">Memory not found</div></div>;

  return (
    <div>
      <div className="section-header">
        <h1><span className="icon">✎</span> Edit Memory</h1>
      </div>

      <form onSubmit={handleSubmit} className="card">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 20px' }}>
          <div className="form-group">
            <label>Summary</label>
            <input className="input" value={form.summary}
              onChange={(e) => updateField('summary', e.target.value)} />
          </div>
          <div className="form-group">
            <label>Type</label>
            <select className="select" value={form.memory_type}
              onChange={(e) => updateField('memory_type', e.target.value)}>
              {MEMORY_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Status</label>
            <select className="select" value={form.status}
              onChange={(e) => updateField('status', e.target.value)}>
              {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
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
          <div className="form-group">
            <label>Revision Reason</label>
            <input className="input" value={form.revision_reason}
              onChange={(e) => updateField('revision_reason', e.target.value)}
              placeholder="Why are you making this change?" required />
          </div>
        </div>

        <div className="form-group">
          <label>Content</label>
          <textarea className="textarea" rows={8} value={form.canonical_text}
            onChange={(e) => updateField('canonical_text', e.target.value)} />
        </div>

        <div style={{ marginTop: 24, display: 'flex', gap: 10 }}>
          <button type="submit" className="btn btn--primary" disabled={submitting}>
            {submitting ? 'Saving...' : 'Save Changes'}
          </button>
          <button type="button" className="btn" onClick={() => navigate(`/memories/${memoryId}?workspace_id=${workspaceId}`)}>Cancel</button>
        </div>
      </form>
    </div>
  );
}
