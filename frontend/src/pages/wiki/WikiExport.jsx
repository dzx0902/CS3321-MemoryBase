import { useState } from 'react';
import { wikiApi } from '../../api/client';
import { DEMO_WORKSPACE_ID } from '../../api/constants';
import { useToast } from '../../components/Toast';

const PAGE_TYPES = ['source', 'entity', 'concept', 'synthesis', 'report', 'timeline', 'handbook'];

export default function WikiExport() {
  const toast = useToast();
  const [form, setForm] = useState({
    workspace_id: DEMO_WORKSPACE_ID,
    page_slug: '',
    title: '',
    page_type: 'synthesis',
    max_memories: 20,
    memory_ids: '',
    write_files: true,
  });
  const [exporting, setExporting] = useState(false);
  const [result, setResult] = useState(null);
  const [viewMode, setViewMode] = useState('form'); // 'form' | 'preview' | 'json'

  function updateField(key, value) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  async function handleExport(e) {
    e.preventDefault();
    if (!form.page_slug.trim() || !form.title.trim()) {
      toast.error('Page slug and title are required');
      return;
    }
    setExporting(true);
    setResult(null);
    try {
      const memoryIds = form.memory_ids
        ? form.memory_ids.split(',').map((s) => s.trim()).filter(Boolean)
        : undefined;
      const data = await wikiApi.export({
        workspace_id: form.workspace_id,
        page_slug: form.page_slug,
        title: form.title,
        page_type: form.page_type,
        max_memories: Number(form.max_memories),
        memory_ids: memoryIds,
        write_files: form.write_files,
      });
      setResult(data);
      setViewMode('preview');
      toast.success('Wiki page exported successfully');
    } catch (err) {
      toast.error(err.message || 'Export failed');
    } finally {
      setExporting(false);
    }
  }

  return (
    <div>
      <div className="section-header">
        <h1><span className="icon">▦</span> Wiki Export</h1>
      </div>

      <div className="panels" style={{ alignItems: 'start' }}>
        <form onSubmit={handleExport} className="card">
          <div className="card__header">
            <h3 className="card__title">Export Settings</h3>
          </div>

          <div className="form-group">
            <label>Workspace</label>
            <input className="input text-mono" value={form.workspace_id}
              onChange={(e) => updateField('workspace_id', e.target.value)}
              required />
          </div>
          <div className="form-group">
            <label>Page Slug</label>
            <input className="input text-mono" value={form.page_slug}
              onChange={(e) => updateField('page_slug', e.target.value)}
              placeholder="my-wiki-page" required />
          </div>
          <div className="form-group">
            <label>Title</label>
            <input className="input" value={form.title}
              onChange={(e) => updateField('title', e.target.value)}
              placeholder="My Wiki Page" required />
          </div>
          <div className="form-group">
            <label>Page Type</label>
            <select className="select" value={form.page_type}
              onChange={(e) => updateField('page_type', e.target.value)}>
              {PAGE_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Max Memories</label>
            <input className="input" type="number" min="1" max="100" value={form.max_memories}
              onChange={(e) => updateField('max_memories', e.target.value)} />
          </div>
          <div className="form-group">
            <label>Memory IDs (comma-separated, optional)</label>
            <input className="input text-mono" value={form.memory_ids}
              onChange={(e) => updateField('memory_ids', e.target.value)}
              placeholder="mem-001, mem-002" />
          </div>
          <div className="form-group" style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <input type="checkbox" id="write-files" checked={form.write_files}
              onChange={(e) => updateField('write_files', e.target.checked)}
              style={{ accentColor: 'var(--accent)' }} />
            <label htmlFor="write-files" style={{ margin: 0, cursor: 'pointer' }}>Write to disk (data/markdown_wiki/)</label>
          </div>

          <button type="submit" className="btn btn--primary" disabled={exporting} style={{ marginTop: 8 }}>
            {exporting ? 'Exporting...' : '▦ Export Wiki Page'}
          </button>
        </form>

        <div>
          {result && (
            <div className="card">
              <div className="card__header">
                <h3 className="card__title">Result</h3>
                <div style={{ display: 'flex', gap: 4 }}>
                  <button className={`btn btn--sm ${viewMode === 'preview' ? 'btn--primary' : ''}`}
                    onClick={() => setViewMode('preview')}>Preview</button>
                  <button className={`btn btn--sm ${viewMode === 'json' ? 'btn--primary' : ''}`}
                    onClick={() => setViewMode('json')}>JSON</button>
                </div>
              </div>

              {viewMode === 'preview' && result.body_markdown ? (
                <div className="markdown-body">
                  {result.frontmatter_json && (
                    <div style={{
                      padding: '10px 14px', background: 'var(--bg-secondary)',
                      borderRadius: 'var(--radius-md)', marginBottom: 16, border: '1px solid var(--border)',
                    }}>
                      <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', marginBottom: 4 }}>
                        Frontmatter
                      </div>
                      <pre style={{ fontSize: '0.78rem', whiteSpace: 'pre-wrap' }}>
                        {JSON.stringify(result.frontmatter_json, null, 2)}
                      </pre>
                    </div>
                  )}
                  <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit', fontSize: '0.88rem', lineHeight: 1.7 }}>
                    {result.body_markdown}
                  </pre>
                </div>
              ) : viewMode === 'json' ? (
                <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.78rem', maxHeight: 500, overflowY: 'auto' }}>
                  {JSON.stringify(result, null, 2)}
                </pre>
              ) : null}

              {!result.body_markdown && !Object.keys(result).length && (
                <p className="text-muted">Export completed. Check the output directory.</p>
              )}
            </div>
          )}

          {!result && !exporting && (
            <div className="card" style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <div className="empty-state">
                <div className="empty-state__icon">▦</div>
                <div className="empty-state__title">Export a Wiki Page</div>
                <p className="text-muted">Configure settings and export to see the result here.</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
