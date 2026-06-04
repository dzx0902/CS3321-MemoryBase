import { useState } from 'react';
import { shortTitle } from './graphLayout';

const NODE_COLORS = {
  workspace: '#355C7D',
  source: '#6D8EA0',
  chunk: '#8D95A3',
  memory: '#B45D5D',
  entity: '#6E8B74',
  scene: '#8A6F95',
  wiki: '#9B6B4A',
};

const EDGE_COLOR = 'rgba(74, 74, 82, 0.24)';
const EDGE_HIGHLIGHT = 'rgba(29, 78, 216, 0.55)';
const ARROW_COLOR = 'rgba(74, 74, 82, 0.35)';
const NODE_STROKE = 'rgba(74, 74, 82, 0.22)';
const NODE_HIGHLIGHT = '#1D4ED8';

export default function GraphSvg({ graph, selectedNode, onSelect, onMoveNode, height = 620 }) {
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
        background: 'var(--bg-elevated)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-md)',
        touchAction: 'none',
        userSelect: 'none',
      }}
    >
      <defs>
        <marker id="graph-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
          <path d="M 0 0 L 10 5 L 0 10 z" fill={ARROW_COLOR} />
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
              stroke={highlighted ? EDGE_HIGHLIGHT : EDGE_COLOR}
              strokeWidth={highlighted ? 2.2 : 1}
              markerEnd="url(#graph-arrow)"
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
            stroke={selectedId === node.id ? NODE_HIGHLIGHT : NODE_STROKE}
            strokeWidth={selectedId === node.id ? 3 : 1}
          />
          <text
            x={node.x}
            y={node.y + 36}
            fill="var(--text-primary)"
            fontSize="11"
            fontWeight={selectedId === node.id ? '700' : '500'}
            textAnchor="middle"
          >
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
