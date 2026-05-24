import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { statsApi } from '../api/client';
import { DEMO_WORKSPACE_ID } from '../api/constants';

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const overview = await statsApi.overview({ workspace_id: DEMO_WORKSPACE_ID });
        setStats({
          sources: overview.source_count || 0,
          chunks: overview.chunk_count || 0,
          memories: overview.memory_count || 0,
          activeMemories: overview.active_memory_count || 0,
          wikiPages: overview.wiki_page_count || 0,
          policies: overview.policy_count || 0,
          conflicts: overview.conflict_count || 0,
          entities: overview.entity_count || 0,
          scenes: overview.scene_count || 0,
          latestActivityAt: overview.latest_activity_at,
        });
      } catch {
        setStats({ sources: '—', chunks: '—', memories: '—', activeMemories: '—', wikiPages: '—', policies: '—', conflicts: '—', entities: '—', scenes: '—' });
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner" />
        Loading dashboard...
      </div>
    );
  }

  const cards = [
    { label: 'Sources', value: stats?.sources, to: '/sources', accent: true },
    { label: 'Memories', value: stats?.memories, to: '/memories', accent: true },
    { label: 'Active Memories', value: stats?.activeMemories, to: '/memories' },
    { label: 'Chunks', value: stats?.chunks, to: '/sources' },
    { label: 'Wiki Pages', value: stats?.wikiPages, to: '/wiki' },
    { label: 'Policies', value: stats?.policies, to: '/governance/policies' },
    { label: 'Conflicts', value: stats?.conflicts, to: '/governance/conflicts' },
    { label: 'Entities', value: stats?.entities, to: '/memories' },
    { label: 'Scenes', value: stats?.scenes, to: '/wiki' },
  ];

  return (
    <div>
      <div className="section-header">
        <h1>
          <span className="icon">◇</span> Dashboard
        </h1>
      </div>

      <div className="stats-grid">
        {cards.map((c) => (
          <Link key={c.label} to={c.to} style={{ textDecoration: 'none' }}>
            <div className="stat-card">
              <div className="stat-card__label">{c.label}</div>
              <div className={`stat-card__value ${c.accent ? 'accent' : ''}`}>{c.value}</div>
            </div>
          </Link>
        ))}
      </div>

      <div className="panels">
        <div className="card">
          <div className="card__header">
            <h3 className="card__title">Quick Actions</h3>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <Link to="/sources" className="btn" style={{ justifyContent: 'flex-start' }}>
              ▤ Browse Sources
            </Link>
            <Link to="/memories/new" className="btn btn--primary" style={{ justifyContent: 'flex-start' }}>
              + Create Memory
            </Link>
            <Link to="/recall" className="btn" style={{ justifyContent: 'flex-start' }}>
              ◎ Query Recall
            </Link>
            <Link to="/wiki" className="btn" style={{ justifyContent: 'flex-start' }}>
              ▦ Export Wiki
            </Link>
          </div>
        </div>

        <div className="card">
          <div className="card__header">
            <h3 className="card__title">System Overview</h3>
          </div>
          <p className="text-muted" style={{ fontSize: '0.88rem', lineHeight: 1.7 }}>
            MemoryBase is a file-database dual-state long-term memory system designed for AI agent
            collaborative development. It provides semantic recall, wiki export, governance
            policies, audit trails, conflict detection, and forget-request workflows — all backed
            by PostgreSQL with full-text search.
          </p>
          <div style={{ marginTop: 16, display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            <span className="badge badge--accent">FastAPI</span>
            <span className="badge badge--info">PostgreSQL</span>
            <span className="badge badge--accent">React</span>
            <span className="badge badge--info">Vite</span>
            <span className="badge badge--default">Full-text Search</span>
            <span className="badge badge--default">Semantic Recall</span>
          </div>
        </div>
      </div>
    </div>
  );
}
