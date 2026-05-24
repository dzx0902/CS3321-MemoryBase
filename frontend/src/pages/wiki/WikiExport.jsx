import { useCallback, useEffect, useState } from 'react';
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
  const [pages, setPages] = useState([]);
  const [keyword, setKeyword] = useState('');
  const [status, setStatus] = useState('');
  const [selectedPage, setSelectedPage] = useState(null);
  const [revisions, setRevisions] = useState([]);
  const [loadingPage, setLoadingPage] = useState(false);
  const [result, setResult] = useState(null);
  const [viewMode, setViewMode] = useState('form'); // 'form' | 'preview' | 'json'

  const loadPages = useCallback(async () => {
    try {
      const data = await wikiApi.list({
        workspace_id: form.workspace_id,
        keyword: keyword || undefined,
        status: status || undefined,
        page_size: 20,
      });
      setPages(data.items || []);
    } catch (err) {
      toast.error(err.message || 'Failed to load wiki pages');
    }
  }, [form.workspace_id, keyword, status, toast]);

  useEffect(() => {
    loadPages();
  }, [loadPages]);

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
      loadPages();
      toast.success('Wiki page exported successfully');
    } catch (err) {
      toast.error(err.message || 'Export failed');
    } finally {
      setExporting(false);
    }
  }

  async function loadPageDetail(page) {
    setLoadingPage(true);
    setSelectedPage(null);
    setRevisions([]);
    try {
      const [detail, revisionData] = await Promise.all([
        wikiApi.detail(page.page_id, { workspace_id: page.workspace_id }),
        wikiApi.revisions(page.page_id, { workspace_id: page.workspace_id, page_size: 20 }),
      ]);
      setSelectedPage(detail);
      setRevisions(revisionData.items || []);
      setViewMode('preview');
      if (detail.latest_revision?.body_markdown) {
        setResult({
          ...detail.latest_revision,
          page_id: detail.page_id,
          workspace_id: detail.workspace_id,
          page_slug: detail.page_slug,
          title: detail.title,
          page_type: detail.page_type,
          body_markdown: detail.latest_revision.body_markdown,
          frontmatter_json: detail.latest_revision.frontmatter_json,
        });
      }
    } catch (err) {
      toast.error(err.message || 'Failed to load wiki page');
    } finally {
      setLoadingPage(false);
    }
  }

  return (
    <div>
      <div className="section-header">
        <h1><span className="icon">▦</span> Wiki</h1>
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
          <div className="card" style={{ marginBottom: 20 }}>
            <div className="card__header">
              <h3 className="card__title">Existing Wiki Pages</h3>
              <button className="btn btn--sm" onClick={loadPages}>Refresh</button>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 140px', gap: 10, marginBottom: 14 }}>
              <input className="input" placeholder="Filter keyword..." value={keyword}
                onChange={(e) => setKeyword(e.target.value)} />
              <select className="select" value={status} onChange={(e) => setStatus(e.target.value)}>
                <option value="">Any status</option>
                <option value="active">active</option>
                <option value="forgotten">forgotten</option>
              </select>
            </div>
            {pages.length === 0 ? (
              <p className="text-muted">No wiki pages found for this workspace.</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {pages.map((page) => (
                  <div key={page.page_id} style={{ display: 'flex', justifyContent: 'space-between', gap: 12, padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
                    <div>
                      <div style={{ fontWeight: 500 }}>{page.title}</div>
                      <div className="text-muted text-mono" style={{ fontSize: '0.75rem' }}>{page.page_slug}</div>
                    </div>
                    <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                      <span className="badge badge--default">{page.page_type}</span>
                      {page.needs_rebuild && <span className="badge badge--danger">rebuild</span>}
                      <span className="text-muted" style={{ fontSize: '0.75rem' }}>v{page.current_revision_no}</span>
                      <button className="btn btn--sm" onClick={() => loadPageDetail(page)} disabled={loadingPage}>
                        View
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {selectedPage && (
            <div className="card" style={{ marginBottom: 20 }}>
              <div className="card__header">
                <h3 className="card__title">{selectedPage.title}</h3>
                <span className="badge badge--info">v{selectedPage.current_revision_no}</span>
              </div>
              <div className="detail-grid" style={{ marginBottom: 16 }}>
                <div className="detail-item">
                  <div className="detail-item__label">Slug</div>
                  <div className="detail-item__value text-mono">{selectedPage.page_slug}</div>
                </div>
                <div className="detail-item">
                  <div className="detail-item__label">Type</div>
                  <div className="detail-item__value">{selectedPage.page_type}</div>
                </div>
                <div className="detail-item">
                  <div className="detail-item__label">Memories</div>
                  <div className="detail-item__value">{selectedPage.memory_count}</div>
                </div>
                <div className="detail-item">
                  <div className="detail-item__label">Sources</div>
                  <div className="detail-item__value">{selectedPage.source_count}</div>
                </div>
              </div>

              <div className="card__header">
                <h3 className="card__title">Revisions</h3>
                <span className="badge badge--default">{revisions.length}</span>
              </div>
              {revisions.length === 0 ? (
                <p className="text-muted">No revisions found.</p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {revisions.map((revision) => (
                    <button
                      key={`${revision.page_id}-${revision.revision_no}`}
                      className="btn"
                      style={{ justifyContent: 'space-between' }}
                      onClick={() => {
                        setResult({
                          ...revision,
                          page_id: selectedPage.page_id,
                          workspace_id: selectedPage.workspace_id,
                          page_slug: selectedPage.page_slug,
                          title: selectedPage.title,
                          page_type: selectedPage.page_type,
                        });
                        setViewMode('preview');
                      }}
                    >
                      <span>Revision {revision.revision_no}</span>
                      <span className="text-muted" style={{ fontSize: '0.75rem' }}>
                        {revision.created_at ? new Date(revision.created_at).toLocaleString() : '—'}
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

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
