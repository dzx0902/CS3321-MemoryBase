import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { sourcesApi } from '../../api/client';
import { DEMO_WORKSPACE_ID } from '../../api/constants';
import { useToast } from '../../components/Toast';

const DOC_TYPES = ['markdown', 'txt', 'meeting', 'chat', 'note', 'report'];

export default function SourceCreate() {
  const navigate = useNavigate();
  const toast = useToast();
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({
    workspace_id: DEMO_WORKSPACE_ID,
    title: '',
    doc_type: 'markdown',
    source_path: '',
    raw_text: '',
  });

  function updateField(key, value) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setSubmitting(true);
    try {
      const created = await sourcesApi.create({
        workspace_id: form.workspace_id,
        title: form.title,
        doc_type: form.doc_type,
        source_path: form.source_path || null,
        raw_text: form.raw_text,
      });
      toast.success(`Source created with ${created.chunk_count} chunks`);
      navigate(`/sources/${created.doc_id}?workspace_id=${form.workspace_id}`);
    } catch (err) {
      toast.error(err.message || 'Failed to create source');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div>
      <div className="section-header">
        <h1><span className="icon">+</span> New Source</h1>
        <Link to="/sources" className="btn">Back to Sources</Link>
      </div>

      <form onSubmit={handleSubmit} className="card">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 20px' }}>
          <div className="form-group">
            <label>Workspace ID</label>
            <input
              className="input"
              value={form.workspace_id}
              onChange={(event) => updateField('workspace_id', event.target.value)}
              required
            />
          </div>
          <div className="form-group">
            <label>Document Type</label>
            <select
              className="select"
              value={form.doc_type}
              onChange={(event) => updateField('doc_type', event.target.value)}
            >
              {DOC_TYPES.map((type) => <option key={type} value={type}>{type}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Title</label>
            <input
              className="input"
              value={form.title}
              onChange={(event) => updateField('title', event.target.value)}
              placeholder="Discussion notes, design draft, meeting recap..."
              required
            />
          </div>
          <div className="form-group">
            <label>Source Path</label>
            <input
              className="input"
              value={form.source_path}
              onChange={(event) => updateField('source_path', event.target.value)}
              placeholder="Optional logical path or filename"
            />
          </div>
        </div>

        <div className="form-group">
          <label>Raw Text</label>
          <textarea
            className="textarea"
            rows={14}
            value={form.raw_text}
            onChange={(event) => updateField('raw_text', event.target.value)}
            placeholder="Paste the source material here. MemoryBase will split it into chunks after creation."
            required
          />
        </div>

        <div style={{ display: 'flex', gap: 10, marginTop: 24 }}>
          <button type="submit" className="btn btn--primary" disabled={submitting}>
            {submitting ? 'Creating...' : 'Create Source'}
          </button>
          <Link to="/sources" className="btn">Cancel</Link>
        </div>
      </form>
    </div>
  );
}
