import { useState } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';

const NAV = [
  { to: '/', label: 'Dashboard', icon: '◇' },
  { to: '/sources', label: 'Sources', icon: '▤' },
  { to: '/memories', label: 'Memories', icon: '◈' },
  { to: '/recall', label: 'Recall', icon: '◎' },
  {
    label: 'Agent Runtime',
    icon: '⌁',
    children: [
      { to: '/runtime/sessions', label: 'Sessions', icon: '◉' },
      { to: '/runtime/messages', label: 'Messages', icon: '✉' },
      { to: '/runtime/search', label: 'Hybrid Search', icon: '⌕' },
    ],
  },
  { to: '/wiki', label: 'Wiki', icon: '▦' },
  {
    label: 'Governance',
    icon: '◫',
    children: [
      { to: '/governance/timeline', label: 'Timeline', icon: '↗' },
      { to: '/governance/audit', label: 'Audit Log', icon: '☰' },
      { to: '/governance/policies', label: 'Policies', icon: '⇧' },
      { to: '/governance/conflicts', label: 'Conflicts', icon: '⚠' },
      { to: '/governance/forget-requests', label: 'Forget Requests', icon: '⌫' },
    ],
  },
];

function NavGroup({ item }) {
  const [open, setOpen] = useState(true);
  const location = useLocation();
  const isChildActive = item.children?.some((c) => location.pathname.startsWith(c.to));

  return (
    <div className="nav-group">
      <button
        className={`nav-item nav-item--parent ${isChildActive ? 'active' : ''}`}
        onClick={() => setOpen(!open)}
      >
        <span className="nav-icon">{item.icon}</span>
        <span className="nav-label">{item.label}</span>
        <span className={`nav-chevron ${open ? 'open' : ''}`}>▾</span>
      </button>
      {open && (
        <div className="nav-children">
          {item.children.map((c) => (
            <NavLink key={c.to} to={c.to} className="nav-item nav-item--child" end>
              <span className="nav-icon">{c.icon}</span>
              <span className="nav-label">{c.label}</span>
            </NavLink>
          ))}
        </div>
      )}
    </div>
  );
}

export default function Layout() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar__brand">
          <span className="sidebar__logo">⬡</span>
          <span className="sidebar__title">MemoryBase</span>
        </div>
        <nav className="sidebar__nav">
          {NAV.map((item) =>
            item.children ? (
              <NavGroup key={item.label} item={item} />
            ) : (
              <NavLink key={item.to} to={item.to} className="nav-item" end>
                <span className="nav-icon">{item.icon}</span>
                <span className="nav-label">{item.label}</span>
              </NavLink>
            ),
          )}
        </nav>
        <div className="sidebar__footer">
          <span className="text-mono" style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
            v0.1.0
          </span>
        </div>
      </aside>
      <main className="main-content">
        <Outlet />
      </main>

      <style>{`
        .app-shell {
          display: flex;
          min-height: 100vh;
        }
        .sidebar {
          width: 250px;
          min-width: 250px;
          background: var(--bg-secondary);
          border-right: 1px solid var(--border);
          display: flex;
          flex-direction: column;
          position: sticky;
          top: 0;
          height: 100vh;
          overflow-y: auto;
          z-index: 100;
        }
        .sidebar__brand {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 20px 20px 16px;
          border-bottom: 1px solid var(--border);
        }
        .sidebar__logo {
          font-size: 1.5rem;
          color: var(--accent);
        }
        .sidebar__title {
          font-family: var(--serif);
          font-size: 1.35rem;
          font-weight: 700;
          letter-spacing: 0.01em;
        }
        .sidebar__nav {
          flex: 1;
          padding: 12px 10px;
          display: flex;
          flex-direction: column;
          gap: 2px;
        }
        .sidebar__footer {
          padding: 12px 20px;
          border-top: 1px solid var(--border);
        }
        .nav-item {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 10px 14px;
          border-radius: var(--radius-md);
          font-size: 0.94rem;
          font-weight: 500;
          color: var(--text-secondary);
          text-decoration: none;
          transition: all var(--transition);
          cursor: pointer;
          border: none;
          background: none;
          width: 100%;
          text-align: left;
          font-family: inherit;
          position: relative;
        }
        .nav-item:hover {
          background: var(--bg-hover);
          color: var(--text-primary);
        }
        .nav-item.active {
          background: var(--accent-dim);
          color: var(--accent);
          font-weight: 600;
        }
        .nav-item.active::before {
          content: '';
          position: absolute;
          left: 0;
          top: 6px;
          bottom: 6px;
          width: 3px;
          background: var(--accent);
          border-radius: 0 2px 2px 0;
        }
        .nav-item--parent {
          font-weight: 600;
        }
        .nav-item--child {
          padding-left: 44px;
          font-size: 0.88rem;
        }
        .nav-icon {
          font-size: 0.95rem;
          width: 20px;
          text-align: center;
          flex-shrink: 0;
        }
        .nav-chevron {
          margin-left: auto;
          font-size: 0.6rem;
          transition: transform var(--transition);
          opacity: 0.5;
        }
        .nav-chevron.open { transform: rotate(180deg); }
        .main-content {
          flex: 1;
          min-width: 0;
          padding: 28px 36px 48px;
          overflow-y: auto;
        }
        @media (max-width: 768px) {
          .app-shell {
            flex-direction: column;
          }
          .sidebar {
            display: flex;
            width: 100%;
            min-width: 0;
            height: auto;
            max-height: 44vh;
            border-right: 0;
            border-bottom: 1px solid var(--border);
          }
          .sidebar__brand {
            padding: 14px 16px 10px;
          }
          .sidebar__nav {
            padding: 8px;
          }
          .sidebar__footer {
            display: none;
          }
          .main-content { padding: 16px; }
        }
      `}</style>
    </div>
  );
}
