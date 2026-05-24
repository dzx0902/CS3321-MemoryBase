import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { sourcesApi } from '../api/client';

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [sources, memories, policies, conflicts] = await Promise.all([
          sourcesApi.list({ page_size: 1 }),
          fetch('/api/memories?page_size=1').then((r) => r.json()),
          fetch('/api/policies?page_size=1').then((r) => r.json()),
          fetch('/api/conflicts?page_size=1').then((r) => r.json()),
        ]);
        setStats({
          sources: sources.total || 0,
          memories: memories.total || 0,
          policies: policies.total || 0,
          conflicts: conflicts.total || 0,
        });
      } catch {
        setStats({ sources: '—', memories: '—', policies: '—', conflicts: '—' });
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
    { label: 'Policies', value: stats?.policies, to: '/governance/policies' },
    { label: 'Conflicts', value: stats?.conflicts, to: '/governance/conflicts' },
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
