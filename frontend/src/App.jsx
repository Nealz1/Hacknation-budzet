import { useState } from 'react';
import './index.css';
import Dashboard from './components/Dashboard';
import Optimization from './components/Optimization';
import Compliance from './components/Compliance';
import Conflicts from './components/Conflicts';
import Departments from './components/Departments';
import Entries from './components/Entries';
import Documents from './components/Documents';

function App() {
  const [activePage, setActivePage] = useState('dashboard');
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: '🏠', section: 'główne' },
    { id: 'entries', label: 'Pozycje Budżetowe', icon: '📋', section: 'główne' },
    { id: 'departments', label: 'Departamenty', icon: '🏢', section: 'główne' },
    { id: 'optimization', label: 'Limit Negotiator', icon: '📊', section: 'agenci' },
    { id: 'compliance', label: 'Compliance Agent', icon: '✅', section: 'agenci' },
    { id: 'conflicts', label: 'Conflict Resolution', icon: '🔄', section: 'agenci' },
    { id: 'documents', label: 'Bureaucrat Agent', icon: '📄', section: 'agenci' },
  ];

  const groupedNav = navItems.reduce((acc, item) => {
    if (!acc[item.section]) acc[item.section] = [];
    acc[item.section].push(item);
    return acc;
  }, {});

  const renderPage = () => {
    switch (activePage) {
      case 'dashboard':
        return <Dashboard setActivePage={setActivePage} />;
      case 'optimization':
        return <Optimization />;
      case 'compliance':
        return <Compliance />;
      case 'conflicts':
        return <Conflicts />;
      case 'departments':
        return <Departments />;
      case 'entries':
        return <Entries setActivePage={setActivePage} />;
      case 'documents':
        return <Documents />;
      default:
        return <Dashboard setActivePage={setActivePage} />;
    }
  };

  return (
    <div className="app-container">
      {}
      <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
        {}
        <div className="sidebar-logo">
          <div className="sidebar-logo-icon">🏛️</div>
          <div>
            <h1>Skarbnik AI</h1>
            <span>Budget Orchestration</span>
          </div>
        </div>

        {}
        <nav className="sidebar-nav">
          {Object.entries(groupedNav).map(([section, items]) => (
            <div key={section} className="nav-section">
              <div className="nav-section-title">{section}</div>
              {items.map((item) => (
                <div
                  key={item.id}
                  className={`nav-item ${activePage === item.id ? 'active' : ''}`}
                  onClick={() => setActivePage(item.id)}
                >
                  <span className="nav-item-icon">{item.icon}</span>
                  <span>{item.label}</span>
                </div>
              ))}
            </div>
          ))}
        </nav>

        {}
        <div style={{ padding: 'var(--spacing-lg)', borderTop: '1px solid var(--border-color)' }}>
          <div className="p-md" style={{ background: 'var(--bg-darker)', borderRadius: 'var(--radius-md)' }}>
            <div className="flex items-center gap-sm mb-sm">
              <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--success)', animation: 'pulse 2s infinite' }}></div>
              <span className="text-secondary" style={{ fontSize: '0.75rem' }}>System Active</span>
            </div>
            <div className="text-muted" style={{ fontSize: '0.7rem' }}>
              Ministerstwo Cyfryzacji<br />
              Część budżetowa: 27
            </div>
          </div>
        </div>
      </aside>

      {}
      <main className="main-content">
        {renderPage()}
      </main>

      {}
      <button
        className="btn btn-primary"
        style={{
          position: 'fixed',
          bottom: '20px',
          right: '20px',
          zIndex: 1001,
          display: 'none',
          width: '50px',
          height: '50px',
          borderRadius: '50%',
          boxShadow: 'var(--shadow-lg)'
        }}
        onClick={() => setSidebarOpen(!sidebarOpen)}
      >
        ☰
      </button>
    </div>
  );
}

export default App;
