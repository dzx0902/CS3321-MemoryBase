import { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { graphApi } from '../../api/client';
import { DEMO_WORKSPACE_ID, GRAPH_DEMO_WORKSPACE_ID } from '../../api/constants';
import { useToast } from '../../components/Toast';

const NODE_COLORS = {
  workspace: '#d6b25e',
  source: '#6aa7d8',
  chunk: '#8d98a8',
  memory: '#e06c75',
  entity: '#71c299',
  scene: '#c18bd9',
  wiki: '#d99b70',
};

export default function GraphExplorer({ fullScreen = false }) {
  const [searchParams] = useSearchParams();
  const toast = useToast();
  const [workspaceId, setWorkspaceId] = useState(searchParams.get('workspace_id') || DEMO_WORKSPACE_ID);
  const [limit, setLimit] = useState(Number(searchParams.get('limit') || 30));
  const [viewMode, setViewMode] = useState(searchParams.get('view') || 'story');
  const [draggedPositions, setDraggedPositions] = useState({});
  const [health, setHealth] = useState(null);
  const [graph, setGraph] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);

  const visibleGraph = useMemo(() => filterGraph(graph, viewMode), [graph, viewMode]);
  const positioned = useMemo(() => layoutGraph(visibleGraph, draggedPositions), [visibleGraph, draggedPositions]);

  async function loadHealth() {
    try {
      setHealth(await graphApi.health());
    } catch (err) {
      toast.error(err.message || 'Failed to load graph health');
    }
  }

  async function loadGraph(usePreview = false, workspaceOverride = workspaceId) {
    setLoading(true);
    setSelectedNode(null);
    try {
      const data = usePreview
        ? await graphApi.preview({ workspace_id: workspaceOverride, limit })
        : await graphApi.workspace({ workspace_id: workspaceOverride, limit, fallback: true });
      setGraph(data);
      setDraggedPositions({});
    } catch (err) {
      toast.error(err.message || 'Failed to load graph');
    } finally {
      setLoading(false);
    }
  }

  function useGraphDemo() {
    setWorkspaceId(GRAPH_DEMO_WORKSPACE_ID);
    loadGraph(false, GRAPH_DEMO_WORKSPACE_ID);
  }

  async function syncGraph() {
    setSyncing(true);
    try {
      const result = await graphApi.sync({ workspace_id: workspaceId, limit: Math.max(limit, 50) });
      toast.success(`Synced ${result.node_count} nodes and ${result.edge_count} edges`);
      await loadHealth();
      await loadGraph(false);
    } catch (err) {
      toast.error(err.message || 'Failed to sync Neo4j graph');
    } finally {
      setSyncing(false);
    }
  }

  useEffect(() => {
    loadHealth();
    loadGraph(false);
  }, []);

  const counts = countByType(graph?.nodes || []);
  const fullscreenHref = `/graph/fullscreen?workspace_id=${encodeURIComponent(workspaceId)}&limit=${limit}&view=${viewMode}`;

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
            <button className="btn" onClick={() => loadGraph(false)} disabled={loading}>
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
          <button className="btn" onClick={() => loadGraph(true)} disabled={loading}>Preview</button>
          <button className="btn btn--primary" onClick={syncGraph} disabled={syncing}>
            {syncing ? 'Syncing...' : 'Sync Neo4j'}
          </button>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 20 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(260px, 1fr) 140px 260px auto', gap: 12, alignItems: 'end' }}>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label>Workspace ID</label>
            <input className="input text-mono" value={workspaceId} onChange={(e) => setWorkspaceId(e.target.value)} />
          </div>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label>Limit</label>
            <input className="input" type="number" min="1" max="100" value={limit}
              onChange={(e) => setLimit(Number(e.target.value))} />
          </div>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label>View</label>
            <select className="select" value={viewMode} onChange={(e) => setViewMode(e.target.value)}>
              <option value="story">Story View</option>
              <option value="evidence">Evidence View</option>
              <option value="full">Full Graph</option>
            </select>
          </div>
          <button className="btn" onClick={() => loadGraph(false)} disabled={loading}>
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
                  <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{
                      width: 10,
                      height: 10,
                      borderRadius: '50%',
                      background: NODE_COLORS[type] || '#9aa4b2',
                    }} />
                    {type}
                  </span>
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

function GraphSvg({ graph, selectedNode, onSelect, onMoveNode, height = 620 }) {
  const selectedId = selectedNode?.id;
  const [draggingId, setDraggingId] = useState(null);
  const viewBox = { width: 960, height: 620 };

  function svgPoint(event) {
    const svg = event.currentTarget;
    const rect = svg.getBoundingClientRect();
    return {
      x: ((event.clientX - rect.left) / rect.width) * viewBox.width,
      y: ((event.clientY - rect.top) / rect.height) * viewBox.height,
    };
  }

  function handlePointerMove(event) {
    if (!draggingId) return;
    event.preventDefault();
    onMoveNode(draggingId, svgPoint(event));
  }

  function stopDragging() {
    setDraggingId(null);
  }

  return (
    <svg
      viewBox={`0 0 ${viewBox.width} ${viewBox.height}`}
      role="img"
      onPointerMove={handlePointerMove}
      onPointerUp={stopDragging}
      onPointerLeave={stopDragging}
      style={{
      width: '100%',
      minHeight: height,
      background: 'var(--bg-secondary)',
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius-md)',
      touchAction: 'none',
      userSelect: 'none',
    }}>
      <defs>
        <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
          <path d="M 0 0 L 10 5 L 0 10 z" fill="rgba(220,220,220,0.45)" />
        </marker>
      </defs>

      {graph.edges.map((edge) => {
        const source = graph.nodeMap.get(edge.source);
        const target = graph.nodeMap.get(edge.target);
        if (!source || !target) return null;
        const highlighted = selectedId && (selectedId === edge.source || selectedId === edge.target);
        return (
          <g key={edge.id}>
            <line
              x1={source.x}
              y1={source.y}
              x2={target.x}
              y2={target.y}
              stroke={highlighted ? 'rgba(214,178,94,0.88)' : 'rgba(120,130,145,0.24)'}
              strokeWidth={highlighted ? 2.2 : 1}
              markerEnd="url(#arrow)"
            />
            {highlighted && (
              <text
                x={(source.x + target.x) / 2}
                y={(source.y + target.y) / 2 - 4}
                fill="var(--text-secondary)"
                fontSize="10"
                textAnchor="middle"
              >
                {edge.type}
              </text>
            )}
          </g>
        );
      })}

      {graph.nodes.map((node) => (
        <g
          key={node.id}
          onClick={() => onSelect(node)}
          onPointerDown={(event) => {
            event.preventDefault();
            setDraggingId(node.id);
            onSelect(node);
          }}
          style={{ cursor: draggingId === node.id ? 'grabbing' : 'grab' }}
        >
          <circle
            cx={node.x}
            cy={node.y}
            r={selectedId === node.id ? 24 : 19}
            fill={NODE_COLORS[node.type] || '#9aa4b2'}
            stroke={selectedId === node.id ? '#f5e7b9' : 'rgba(255,255,255,0.45)'}
            strokeWidth={selectedId === node.id ? 3 : 1}
          />
          <text x={node.x} y={node.y + 36} fill="var(--text-primary)" fontSize="11" fontWeight={selectedId === node.id ? '700' : '500'} textAnchor="middle">
            {shortTitle(node)}
          </text>
          <text x={node.x} y={node.y + 52} fill="var(--text-muted)" fontSize="10" textAnchor="middle">
            {node.type}
          </text>
        </g>
      ))}
    </svg>
  );
}

function layoutGraph(graph, draggedPositions = {}) {
  if (!graph) return { nodes: [], edges: [], nodeMap: new Map() };
  const lanes = {
    source: { x: 135, y1: 150, y2: 480 },
    chunk: { x: 275, y1: 85, y2: 535 },
    entity: { x: 385, y1: 175, y2: 445 },
    workspace: { x: 480, y1: 300, y2: 300 },
    scene: { x: 480, y1: 180, y2: 440 },
    memory: { x: 670, y1: 95, y2: 525 },
    wiki: { x: 835, y1: 210, y2: 410 },
  };
  const grouped = groupByType(graph.nodes);
  const nodes = graph.nodes.map((node) => {
    const lane = lanes[node.type] || { x: 500, y1: 120, y2: 500 };
    const peers = grouped[node.type] || [];
    const index = peers.findIndex((candidate) => candidate.id === node.id);
    const y = distributeY(lane.y1, lane.y2, peers.length, Math.max(index, 0));
    return { ...node, x: draggedPositions[node.id]?.x ?? lane.x, y: draggedPositions[node.id]?.y ?? y };
  });
  return { nodes, edges: graph.edges || [], nodeMap: new Map(nodes.map((node) => [node.id, node])) };
}

function filterGraph(graph, viewMode) {
  if (!graph) return { nodes: [], edges: [] };
  if (viewMode === 'full') return graph;

  const importantMemoryIds = new Set(
    graph.nodes
      .filter((node) => node.type === 'memory' && Number(node.properties?.importance || 0) >= 5)
      .map((node) => node.id),
  );
  const sceneMemoryIds = new Set(
    graph.edges
      .filter((edge) => edge.type === 'CONTAINS_MEMORY')
      .map((edge) => edge.target),
  );

  const visibleIds = new Set();
  graph.nodes.forEach((node) => {
    if (viewMode === 'story') {
      if (node.type === 'chunk') return;
      if (node.type === 'memory' && !importantMemoryIds.has(node.id) && !sceneMemoryIds.has(node.id)) return;
      visibleIds.add(node.id);
      return;
    }
    if (viewMode === 'evidence') {
      if (node.type === 'memory' && !importantMemoryIds.has(node.id) && !sceneMemoryIds.has(node.id)) return;
      visibleIds.add(node.id);
    }
  });

  const edges = graph.edges.filter((edge) => visibleIds.has(edge.source) && visibleIds.has(edge.target));
  const connectedIds = new Set(edges.flatMap((edge) => [edge.source, edge.target]));
  const nodes = graph.nodes.filter((node) => visibleIds.has(node.id) && (connectedIds.has(node.id) || node.type === 'workspace'));
  return { ...graph, nodes, edges };
}

function groupByType(nodes) {
  return nodes.reduce((acc, node) => {
    acc[node.type] = acc[node.type] || [];
    acc[node.type].push(node);
    return acc;
  }, {});
}

function distributeY(y1, y2, count, index) {
  if (count <= 1) return (y1 + y2) / 2;
  const step = (y2 - y1) / (count - 1);
  return y1 + step * index;
}

function countByType(nodes) {
  return nodes.reduce((acc, node) => {
    acc[node.type] = (acc[node.type] || 0) + 1;
    return acc;
  }, {});
}

function truncate(value, maxLen) {
  if (!value) return '';
  return value.length <= maxLen ? value : value.slice(0, maxLen - 3) + '...';
}

function shortTitle(node) {
  const props = node.properties || {};
  if (node.type === 'source') return props.title_short || truncate(node.title.replace(/^Graph Demo \d+:\s*/, '').replace(/^Discussion \d+:\s*/, ''), 18);
  if (node.type === 'memory') return truncate(node.title.replace(/\.$/, ''), 22);
  if (node.type === 'workspace') return truncate(node.title.replace(/^Graph Demo:\s*/, ''), 20);
  return truncate(node.title, 20);
}
