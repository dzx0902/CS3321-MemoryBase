import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { graphApi } from '../../api/client';
import { DEMO_AGENT_ID, DEMO_WORKSPACE_ID, GRAPH_DEMO_WORKSPACE_ID } from '../../api/constants';
import { useToast } from '../../components/Toast';
import GraphSvg from './GraphSvg';
import { countByType, filterGraph, layoutGraph } from './graphLayout';

export default function GraphExplorer({ fullScreen = false }) {
  const [searchParams] = useSearchParams();
  const toast = useToast();
  const initialWorkspaceId = searchParams.get('workspace_id') || DEMO_WORKSPACE_ID;
  const initialAgentId = searchParams.get('agent_id') || '';
  const initialLimit = Number(searchParams.get('limit') || 30);
  const initialViewMode = searchParams.get('view') || 'story';
  const [workspaceId, setWorkspaceId] = useState(initialWorkspaceId);
  const [agentId, setAgentId] = useState(initialAgentId);
  const [limit, setLimit] = useState(initialLimit);
  const [viewMode, setViewMode] = useState(initialViewMode);
  const [draggedPositions, setDraggedPositions] = useState({});
  const [health, setHealth] = useState(null);
  const [graph, setGraph] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);

  const effectiveLimit = Math.min(100, Math.max(1, Number(limit) || 30));
  const visibleGraph = useMemo(() => filterGraph(graph, viewMode), [graph, viewMode]);
  const positioned = useMemo(() => layoutGraph(visibleGraph, draggedPositions), [visibleGraph, draggedPositions]);
  const counts = useMemo(() => countByType(graph?.nodes || []), [graph]);
  const fullscreenHref = `/graph/fullscreen?workspace_id=${encodeURIComponent(workspaceId)}&limit=${effectiveLimit}&view=${viewMode}${agentId ? `&agent_id=${encodeURIComponent(agentId)}` : ''}`;

  const loadHealth = useCallback(async () => {
    try {
      setHealth(await graphApi.health());
    } catch (err) {
      toast.error(err.message || 'Failed to load graph health');
    }
  }, [toast]);

  const loadGraph = useCallback(async ({
    usePreview = false,
    workspaceId: workspaceOverride,
    agentId: agentOverride = '',
    limit: limitOverride,
  }) => {
    setLoading(true);
    setSelectedNode(null);
    try {
      const data = usePreview
        ? await graphApi.preview({ workspace_id: workspaceOverride, limit: limitOverride })
        : await graphApi.workspace({
            workspace_id: workspaceOverride,
            agent_id: agentOverride || undefined,
            limit: limitOverride,
            fallback: true,
          });
      setGraph(data);
      setDraggedPositions({});
    } catch (err) {
      toast.error(err.message || 'Failed to load graph');
    } finally {
      setLoading(false);
    }
  }, [toast]);

  const loadCurrentGraph = useCallback((usePreview = false) => {
    return loadGraph({
      usePreview,
      workspaceId,
      agentId,
      limit: effectiveLimit,
    });
  }, [agentId, effectiveLimit, loadGraph, workspaceId]);

  const useGraphDemo = useCallback(() => {
    setWorkspaceId(GRAPH_DEMO_WORKSPACE_ID);
    setAgentId(DEMO_AGENT_ID);
    void loadGraph({
      workspaceId: GRAPH_DEMO_WORKSPACE_ID,
      agentId: DEMO_AGENT_ID,
      limit: effectiveLimit,
    });
  }, [effectiveLimit, loadGraph]);

  const syncGraph = useCallback(async () => {
    setSyncing(true);
    try {
      const result = await graphApi.sync({
        workspace_id: workspaceId,
        agent_id: agentId || undefined,
        limit: effectiveLimit,
      });
      toast.success(`Synced ${result.node_count} nodes and ${result.edge_count} edges`);
      await loadHealth();
      await loadCurrentGraph(false);
    } catch (err) {
      toast.error(err.message || 'Failed to sync Neo4j graph');
    } finally {
      setSyncing(false);
    }
  }, [agentId, effectiveLimit, loadCurrentGraph, loadHealth, toast, workspaceId]);

  useEffect(() => {
    void loadHealth();
    void loadGraph({
      workspaceId: initialWorkspaceId,
      agentId: initialAgentId,
      limit: Math.min(100, Math.max(1, Number(initialLimit) || 30)),
    });
  }, [initialAgentId, initialLimit, initialWorkspaceId, loadGraph, loadHealth]);

  if (fullScreen) {
    return (
      <div style={{ minHeight: 'calc(100vh - 76px)' }}>
        <div className="section-header">
          <h1><span className="icon">⬡</span> Graph View</h1>
          <div style={{ display: 'flex', gap: 8 }}>
            <select className="select" value={viewMode} onChange={(e) => setViewMode(e.target.value)} style={{ width: 160 }}>
              <option value="story">Story View</option>
              <option value="evidence">Evidence View</option>
              <option value="full">Full Graph</option>
            </select>
            <button className="btn" onClick={() => loadCurrentGraph(false)} disabled={loading}>
              {loading ? 'Loading...' : 'Reload'}
            </button>
            <Link className="btn" to="/graph">Back</Link>
          </div>
        </div>

        <div className="card" style={{ padding: 12 }}>
          {loading || !graph ? (
            <div className="loading"><div className="spinner" />Loading graph...</div>
          ) : (
            <GraphSvg
              graph={positioned}
              selectedNode={selectedNode}
              onSelect={setSelectedNode}
              onMoveNode={(nodeId, position) => setDraggedPositions((prev) => ({ ...prev, [nodeId]: position }))}
              height={760}
            />
          )}
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="section-header">
        <h1><span className="icon">⬡</span> Graph Explorer</h1>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn" onClick={useGraphDemo}>Use Graph Demo</button>
          <Link className="btn" to={fullscreenHref} target="_blank" rel="noreferrer">Open Fullscreen</Link>
          <button className="btn" onClick={() => loadCurrentGraph(true)} disabled={loading}>Preview</button>
          <button className="btn btn--primary" onClick={syncGraph} disabled={syncing}>
            {syncing ? 'Syncing...' : 'Sync Neo4j'}
          </button>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 20 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(220px, 1fr) minmax(220px, 1fr) 120px 220px auto', gap: 12, alignItems: 'end' }}>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label>Workspace ID</label>
            <input className="input text-mono" value={workspaceId} onChange={(e) => setWorkspaceId(e.target.value)} />
          </div>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label>Agent ID (optional)</label>
            <input className="input text-mono" value={agentId} onChange={(e) => setAgentId(e.target.value)} placeholder="blank = public/project view" />
          </div>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label>Limit</label>
            <input className="input" type="number" min="1" max="100" value={limit} onChange={(e) => setLimit(Number(e.target.value))} />
          </div>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label>View</label>
            <select className="select" value={viewMode} onChange={(e) => setViewMode(e.target.value)}>
              <option value="story">Story View</option>
              <option value="evidence">Evidence View</option>
              <option value="full">Full Graph</option>
            </select>
          </div>
          <button className="btn" onClick={() => loadCurrentGraph(false)} disabled={loading}>
            {loading ? 'Loading...' : 'Load Graph'}
          </button>
        </div>

        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 14 }}>
          <span className={`badge ${health?.available ? 'badge--success' : 'badge--danger'}`}>
            Neo4j {health?.available ? 'available' : health?.enabled ? 'unavailable' : 'disabled'}
          </span>
          <span className="badge badge--default">{graph?.source || 'not loaded'}</span>
          {health?.error && <span className="text-muted" style={{ fontSize: '0.78rem' }}>{health.error}</span>}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 320px', gap: 20, alignItems: 'start' }}>
        <div className="card">
          <div className="card__header">
            <h3 className="card__title">Workspace Knowledge Graph</h3>
            <span className="badge badge--info">
              {visibleGraph?.nodes?.length || 0}/{graph?.nodes?.length || 0} nodes · {visibleGraph?.edges?.length || 0}/{graph?.edges?.length || 0} edges
            </span>
          </div>

          {loading ? (
            <div className="loading"><div className="spinner" />Loading graph...</div>
          ) : !graph || visibleGraph.nodes.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state__icon">⬡</div>
              <div className="empty-state__title">No graph data</div>
              <p className="text-muted">Load a workspace graph or sync Neo4j first.</p>
            </div>
          ) : (
            <GraphSvg
              graph={positioned}
              selectedNode={selectedNode}
              onSelect={setSelectedNode}
              onMoveNode={(nodeId, position) => setDraggedPositions((prev) => ({ ...prev, [nodeId]: position }))}
            />
          )}
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          <div className="card">
            <div className="card__header">
              <h3 className="card__title">Node Types</h3>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {Object.entries(counts).map(([type, count]) => (
                <div key={type} style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
                  <span>{type}</span>
                  <span className="badge badge--default">{count}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="card">
            <div className="card__header">
              <h3 className="card__title">Selection</h3>
            </div>
            {selectedNode ? (
              <div>
                <span className="badge badge--accent">{selectedNode.type}</span>
                <h3 style={{ marginTop: 10, marginBottom: 6, fontSize: '1rem' }}>{selectedNode.title}</h3>
                <p className="text-muted" style={{ fontSize: '0.82rem', lineHeight: 1.5 }}>{selectedNode.subtitle || 'No subtitle'}</p>
                <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.74rem', maxHeight: 260, overflow: 'auto' }}>
                  {JSON.stringify(selectedNode.properties || {}, null, 2)}
                </pre>
              </div>
            ) : (
              <p className="text-muted">Select a node in the graph.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
