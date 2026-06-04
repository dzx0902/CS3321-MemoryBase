export function layoutGraph(graph, draggedPositions = {}) {
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
    return {
      ...node,
      x: draggedPositions[node.id]?.x ?? lane.x,
      y: draggedPositions[node.id]?.y ?? y,
    };
  });
  return {
    nodes,
    edges: graph.edges || [],
    nodeMap: new Map(nodes.map((node) => [node.id, node])),
  };
}

export function filterGraph(graph, viewMode) {
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
      if (node.type === 'memory' && !importantMemoryIds.has(node.id) && !sceneMemoryIds.has(node.id)) {
        return;
      }
      visibleIds.add(node.id);
      return;
    }
    if (viewMode === 'evidence') {
      if (node.type === 'memory' && !importantMemoryIds.has(node.id) && !sceneMemoryIds.has(node.id)) {
        return;
      }
      visibleIds.add(node.id);
    }
  });

  const edges = graph.edges.filter((edge) => visibleIds.has(edge.source) && visibleIds.has(edge.target));
  const connectedIds = new Set(edges.flatMap((edge) => [edge.source, edge.target]));
  const nodes = graph.nodes.filter(
    (node) => visibleIds.has(node.id) && (connectedIds.has(node.id) || node.type === 'workspace'),
  );
  return { ...graph, nodes, edges };
}

export function countByType(nodes) {
  return nodes.reduce((acc, node) => {
    acc[node.type] = (acc[node.type] || 0) + 1;
    return acc;
  }, {});
}

export function shortTitle(node) {
  const props = node.properties || {};
  if (node.type === 'source') {
    return props.title_short || truncate(node.title.replace(/^Graph Demo \d+:\s*/, '').replace(/^Discussion \d+:\s*/, ''), 18);
  }
  if (node.type === 'memory') return truncate(node.title.replace(/\.$/, ''), 22);
  if (node.type === 'workspace') return truncate(node.title.replace(/^Graph Demo:\s*/, ''), 20);
  return truncate(node.title, 20);
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

function truncate(value, maxLen) {
  if (!value) return '';
  return value.length <= maxLen ? value : value.slice(0, maxLen - 3) + '...';
}
