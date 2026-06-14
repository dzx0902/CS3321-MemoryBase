import { useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { memoriesApi, memoryExtractionApi, sourcesApi } from '../../api/client';
import { useToast } from '../../components/Toast';

export default function SourceDetail() {
  const { docId } = useParams();
  const [searchParams] = useSearchParams();
  const workspaceId = searchParams.get('workspace_id');
  const [source, setSource] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedChunkIds, setSelectedChunkIds] = useState([]);
  const [candidates, setCandidates] = useState([]);
  const [extracting, setExtracting] = useState(false);
  const [decidingId, setDecidingId] = useState(null);
  const [maxCandidates, setMaxCandidates] = useState(10);
  const toast = useToast();

  useEffect(() => {
    async function load() {
      if (!workspaceId) {
        toast.error('Missing workspace_id in URL');
        setLoading(false);
        return;
      }
      try {
        const data = await sourcesApi.detail(docId, { workspace_id: workspaceId });
        setSource(data);
        setSelectedChunkIds([]);
        setCandidates([]);
      } catch (err) {
        toast.error(err.message || 'Failed to load source');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [docId, workspaceId, toast]);

  const chunks = source?.chunks || [];
  const allSelected = chunks.length > 0 && selectedChunkIds.length === chunks.length;

  function toggleChunk(chunkId) {
    setSelectedChunkIds((current) => (
      current.includes(chunkId)
        ? current.filter((id) => id !== chunkId)
        : [...current, chunkId]
    ));
  }

  function toggleAllChunks() {
    setSelectedChunkIds(allSelected ? [] : chunks.map((chunk) => chunk.chunk_id));
  }

  async function hydrateCandidates(candidateSummaries) {
    return Promise.all(
      candidateSummaries.map(async (candidate) => {
        try {
          return await memoriesApi.detail(candidate.memory_id, { workspace_id: candidate.workspace_id });
        } catch {
          return candidate;
        }
      }),
    );
  }

  async function handleExtract() {
    if (!workspaceId || selectedChunkIds.length === 0) {
      toast.error('Select at least one chunk');
      return;
    }
    setExtracting(true);
    try {
      const result = await memoryExtractionApi.extractFromChunks({
        workspace_id: workspaceId,
        chunk_ids: selectedChunkIds,
        max_candidates: Number(maxCandidates) || 10,
      });
      const detailedCandidates = await hydrateCandidates(result.candidates || []);
      setCandidates(detailedCandidates);
      toast.success(`Created ${result.created_count || 0} candidate memories`);
    } catch (err) {
      toast.error(err.message || 'Failed to extract candidates');
    } finally {
      setExtracting(false);
    }
  }

  async function decideCandidate(candidate, decision) {
    if (!workspaceId) return;
    setDecidingId(candidate.memory_id);
    try {
      const result = decision === 'approve'
        ? await memoryExtractionApi.approve(candidate.memory_id, { workspace_id: workspaceId })
        : await memoryExtractionApi.reject(candidate.memory_id, { workspace_id: workspaceId });
      setCandidates((current) => current.map((item) => (
        item.memory_id === candidate.memory_id
          ? { ...item, ...result.memory, evidence: item.evidence || [] }
          : item
      )));
      toast.success(decision === 'approve' ? 'Candidate approved' : 'Candidate rejected');
    } catch (err) {
      toast.error(err.message || `Failed to ${decision} candidate`);
    } finally {
      setDecidingId(null);
    }
  }

  if (loading) {
    return <div className="loading"><div className="spinner" />Loading source...</div>;
  }
  if (!source) {
    return <div className="empty-state"><div className="empty-state__title">Source not found</div></div>;
  }

  return (
    <div>
      <div className="section-header">
        <h1><span className="icon">▤</span> {source.title || 'Untitled'}</h1>
        <Link to="/sources" className="btn">Back to Sources</Link>
      </div>

      <div className="detail-grid">
        <div className="detail-item">
          <div className="detail-item__label">Document ID</div>
          <div className="detail-item__value text-mono">{source.doc_id}</div>
        </div>
        <div className="detail-item">
          <div className="detail-item__label">Type</div>
          <div className="detail-item__value"><span className="badge badge--accent">{source.doc_type || '-'}</span></div>
        </div>
        <div className="detail-item">
          <div className="detail-item__label">Workspace</div>
          <div className="detail-item__value">{source.workspace_id || '-'}</div>
        </div>
        <div className="detail-item">
          <div className="detail-item__label">Source Path</div>
          <div className="detail-item__value text-mono">{source.source_path || '-'}</div>
        </div>
        <div className="detail-item">
          <div className="detail-item__label">Created</div>
          <div className="detail-item__value">{source.imported_at ? new Date(source.imported_at).toLocaleString() : '-'}</div>
        </div>
        <div className="detail-item">
          <div className="detail-item__label">Chunks</div>
          <div className="detail-item__value">{chunks.length}</div>
        </div>
      </div>

      {source.raw_text && (
        <div className="card" style={{ marginBottom: 24 }}>
          <div className="card__header">
            <h3 className="card__title">Raw Text</h3>
          </div>
          <pre className="markdown-body" style={{ whiteSpace: 'pre-wrap', fontSize: '0.85rem', maxHeight: 400, overflowY: 'auto' }}>
            {source.raw_text}
          </pre>
        </div>
      )}

      {chunks.length > 0 && (
        <div className="card" style={{ marginBottom: 24 }}>
          <div className="card__header">
            <h3 className="card__title">Chunks ({chunks.length})</h3>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
              <span className="badge badge--default">{selectedChunkIds.length} selected</span>
              <label style={{ display: 'inline-flex', alignItems: 'center', gap: 6, marginBottom: 0, cursor: 'pointer' }}>
                <input type="checkbox" checked={allSelected} onChange={toggleAllChunks} />
                Select all
              </label>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <label style={{ marginBottom: 0 }}>Max</label>
                <input
                  className="input"
                  type="number"
                  min="1"
                  max="50"
                  value={maxCandidates}
                  onChange={(event) => setMaxCandidates(event.target.value)}
                  style={{ width: 76 }}
                />
              </div>
              <button className="btn btn--primary" onClick={handleExtract} disabled={extracting || selectedChunkIds.length === 0}>
                {extracting ? 'Extracting...' : 'Extract Candidates'}
              </button>
            </div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {chunks.map((chunk) => (
              <div key={chunk.chunk_id} style={{
                background: 'var(--bg-elevated)',
                borderRadius: 'var(--radius-md)',
                padding: '14px 18px',
                border: '1px solid var(--border)',
              }}>
                <div style={{ display: 'flex', gap: 12, marginBottom: 6, alignItems: 'center' }}>
                  <input
                    type="checkbox"
                    checked={selectedChunkIds.includes(chunk.chunk_id)}
                    onChange={() => toggleChunk(chunk.chunk_id)}
                    aria-label={`Select chunk ${chunk.chunk_no}`}
                  />
                  <span className="badge badge--info">Chunk {chunk.chunk_no}</span>
                  <span className="text-muted" style={{ fontSize: '0.75rem' }}>
                    Lines {chunk.start_line ?? '-'}-{chunk.end_line ?? '-'}
                  </span>
                  <span className="text-muted" style={{ fontSize: '0.75rem' }}>
                    {chunk.token_count} tokens
                  </span>
                </div>
                <pre style={{
                  whiteSpace: 'pre-wrap',
                  fontSize: '0.83rem',
                  color: 'var(--text-primary)',
                  lineHeight: 1.6,
                  fontFamily: 'inherit',
                }}>
                  {chunk.chunk_text}
                </pre>
              </div>
            ))}
          </div>
        </div>
      )}

      {candidates.length > 0 && (
        <div className="card">
          <div className="card__header">
            <h3 className="card__title">Candidate Memories ({candidates.length})</h3>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {candidates.map((candidate) => {
              const evidence = candidate.evidence?.[0];
              const isCandidate = candidate.status === 'candidate';
              return (
                <div key={candidate.memory_id} style={{
                  background: 'var(--bg-elevated)',
                  borderRadius: 'var(--radius-md)',
                  padding: '16px 18px',
                  border: '1px solid var(--border)',
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'flex-start' }}>
                    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 8 }}>
                      <span className="badge badge--accent">{candidate.memory_type || 'unknown'}</span>
                      <span className={`badge ${candidate.status === 'active' ? 'badge--success' : candidate.status === 'rejected' ? 'badge--danger' : 'badge--default'}`}>
                        {candidate.status || 'candidate'}
                      </span>
                      <span className="badge badge--default">importance {candidate.importance ?? '-'}</span>
                      <span className="badge badge--info">confidence {Number(candidate.confidence ?? 0).toFixed(2)}</span>
                    </div>
                    <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
                      {isCandidate && (
                        <>
                          <button
                            className="btn btn--sm"
                            style={{ borderColor: 'var(--success)', color: 'var(--success)' }}
                            disabled={decidingId === candidate.memory_id}
                            onClick={() => decideCandidate(candidate, 'approve')}
                          >
                            Approve
                          </button>
                          <button
                            className="btn btn--danger btn--sm"
                            disabled={decidingId === candidate.memory_id}
                            onClick={() => decideCandidate(candidate, 'reject')}
                          >
                            Reject
                          </button>
                        </>
                      )}
                      <Link
                        className="btn btn--sm"
                        to={`/memories/${candidate.memory_id}?workspace_id=${candidate.workspace_id || workspaceId}`}
                      >
                        View
                      </Link>
                    </div>
                  </div>

                  <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6, marginBottom: 10 }}>
                    {candidate.canonical_text}
                  </div>

                  {evidence && (
                    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
                      <span className="badge badge--default">Chunk {evidence.chunk_no}</span>
                      <span className="text-muted" style={{ fontSize: '0.78rem' }}>
                        Lines {evidence.start_line ?? '-'}-{evidence.end_line ?? '-'}
                      </span>
                      <span className="text-muted" style={{ fontSize: '0.78rem' }}>
                        {evidence.source_title}
                      </span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
