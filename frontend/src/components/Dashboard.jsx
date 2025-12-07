import { useState, useEffect } from 'react';
import api from '../services/api';

export default function Dashboard({ setActivePage }) {
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);
    const [gapAnalysis, setGapAnalysis] = useState(null);
    const [recentEntries, setRecentEntries] = useState([]);

    useEffect(() => {
        loadDashboardData();
    }, []);

    const loadDashboardData = async () => {
        setLoading(true);
        try {
            const [statsData, gapData, entriesData] = await Promise.all([
                api.getDashboardStats().catch(() => null),
                api.getGapAnalysis().catch(() => null),
                api.getEntries({ limit: 5 }).catch(() => []),
            ]);

            setStats(statsData);
            setGapAnalysis(gapData);
            setRecentEntries(entriesData);
        } catch (error) {
            console.error('Failed to load dashboard:', error);
        }
        setLoading(false);
    };

    const handleLoadDemoData = async () => {
        try {
            await api.loadDemoData();
            loadDashboardData();
        } catch (error) {
            alert('Failed to load demo data: ' + error.message);
        }
    };

    const formatCurrency = (value) => {
        if (!value && value !== 0) return '-';
        return new Intl.NumberFormat('pl-PL', {
            style: 'decimal',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        }).format(value) + ' tys. PLN';
    };

    const formatPercent = (value) => {
        return (value || 0).toFixed(1) + '%';
    };

    if (loading) {
        return (
            <div className="loading-overlay" style={{ position: 'relative', minHeight: '400px' }}>
                <div className="loading-spinner"></div>
            </div>
        );
    }

    const hasData = stats && stats.total_entries > 0;
    const budgetUsage = stats ? (stats.total_budget_2025 / stats.global_limit_2025 * 100) : 0;
    const isOverBudget = stats ? stats.variance > 0 : false;

    return (
        <div className="animate-fade-in">
            {}
            <div className="flex justify-between items-center mb-xl">
                <div>
                    <h1 style={{ fontSize: '1.75rem', marginBottom: '0.25rem' }}>
                        🏛️ Skarbnik AI Dashboard
                    </h1>
                    <p className="text-secondary">
                        Agentic Budget Orchestration Platform
                    </p>
                </div>
                {!hasData && (
                    <button className="btn btn-primary btn-lg" onClick={handleLoadDemoData}>
                        📥 Załaduj Dane Demo
                    </button>
                )}
            </div>

            {}
            <div className="stats-grid mb-xl">
                <div className={`stat-card ${isOverBudget ? 'warning' : 'success'}`}>
                    <div className="stat-icon primary">📊</div>
                    <div className="stat-value">{formatCurrency(stats?.total_budget_2025)}</div>
                    <div className="stat-label">Całkowity Budżet 2025</div>
                    <div className={`stat-change ${isOverBudget ? 'negative' : 'positive'}`}>
                        {isOverBudget ? '⚠️' : '✅'} {formatPercent(budgetUsage)} limitu
                    </div>
                </div>

                <div className="stat-card">
                    <div className="stat-icon success">🎯</div>
                    <div className="stat-value">{formatCurrency(stats?.global_limit_2025)}</div>
                    <div className="stat-label">Limit MF na 2025</div>
                </div>

                <div className={`stat-card ${isOverBudget ? 'warning' : ''}`}>
                    <div className={`stat-icon ${isOverBudget ? 'error' : 'success'}`}>
                        {isOverBudget ? '📈' : '📉'}
                    </div>
                    <div className={`stat-value ${isOverBudget ? 'negative' : 'positive'}`}>
                        {isOverBudget ? '+' : ''}{formatCurrency(stats?.variance)}
                    </div>
                    <div className="stat-label">
                        {isOverBudget ? 'Przekroczenie Limitu' : 'Rezerwa'}
                    </div>
                </div>

                <div className="stat-card">
                    <div className="stat-icon primary">📝</div>
                    <div className="stat-value">{stats?.total_entries || 0}</div>
                    <div className="stat-label">Pozycji Budżetowych</div>
                </div>
            </div>

            {}
            {hasData && (
                <div className="card mb-xl">
                    <div className="card-header">
                        <h3 className="card-title">
                            <span className="card-title-icon">📊</span>
                            Wykorzystanie Budżetu 2025
                        </h3>
                    </div>
                    <div className="progress-container">
                        <div className="progress-header">
                            <span>Limit vs Zapotrzebowanie</span>
                            <span className={isOverBudget ? 'text-danger' : 'text-success'}>
                                {formatPercent(budgetUsage)}
                            </span>
                        </div>
                        <div className="progress-bar">
                            <div
                                className={`progress-fill ${budgetUsage > 100 ? 'danger' : budgetUsage > 85 ? 'warning' : 'success'}`}
                                style={{ width: `${Math.min(budgetUsage, 100)}%` }}
                            ></div>
                        </div>
                    </div>

                    {}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '1rem', marginTop: '1.5rem' }}>
                        <div className="p-md" style={{ background: 'var(--bg-darker)', borderRadius: 'var(--radius-md)' }}>
                            <div className="text-secondary" style={{ fontSize: '0.75rem', marginBottom: '0.25rem' }}>
                                🔒 Obligatoryjne
                            </div>
                            <div className="font-bold text-warning">
                                {formatCurrency(stats?.obligatory_total)}
                            </div>
                        </div>
                        <div className="p-md" style={{ background: 'var(--bg-darker)', borderRadius: 'var(--radius-md)' }}>
                            <div className="text-secondary" style={{ fontSize: '0.75rem', marginBottom: '0.25rem' }}>
                                💡 Dyskrecjonalne
                            </div>
                            <div className="font-bold text-success">
                                {formatCurrency(stats?.discretionary_total)}
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {}
            {hasData && isOverBudget && (
                <div className="agent-card mb-xl animate-slide-in">
                    <div className="agent-header">
                        <div className="agent-avatar">🤖</div>
                        <div>
                            <div className="agent-name">Limit Negotiator Agent</div>
                            <div className="agent-action">Analiza Optymalizacji</div>
                        </div>
                    </div>
                    <div className="agent-body">
                        <div className="alert alert-warning mb-md">
                            <span className="alert-icon">⚠️</span>
                            <div>
                                <strong>Przekroczenie limitu!</strong>
                                <p>Budżet przekracza limit o <strong>{formatCurrency(stats?.variance)}</strong>.
                                    Kliknij poniżej, aby uzyskać sugestie optymalizacji.</p>
                            </div>
                        </div>
                        <button
                            className="btn btn-primary"
                            onClick={() => setActivePage('optimization')}
                        >
                            📊 Uruchom Analizę Optymalizacji
                        </button>
                    </div>
                </div>
            )}

            {}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
                <div
                    className="card"
                    style={{ cursor: 'pointer' }}
                    onClick={() => setActivePage('compliance')}
                >
                    <div className="flex items-center gap-md">
                        <div className="stat-icon success">✅</div>
                        <div>
                            <h4>Walidacja Zgodności</h4>
                            <p className="text-secondary" style={{ fontSize: '0.875rem' }}>
                                Sprawdź zgodność z Rozporządzeniami
                            </p>
                        </div>
                    </div>
                </div>

                <div
                    className="card"
                    style={{ cursor: 'pointer' }}
                    onClick={() => setActivePage('conflicts')}
                >
                    <div className="flex items-center gap-md">
                        <div className="stat-icon warning">🔄</div>
                        <div>
                            <h4>Wykrywanie Konfliktów</h4>
                            <p className="text-secondary" style={{ fontSize: '0.875rem' }}>
                                Znajdź duplikaty między departamentami
                            </p>
                        </div>
                    </div>
                </div>

                <div
                    className="card"
                    style={{ cursor: 'pointer' }}
                    onClick={() => setActivePage('departments')}
                >
                    <div className="flex items-center gap-md">
                        <div className="stat-icon primary">🏢</div>
                        <div>
                            <h4>Widok Departamentów</h4>
                            <p className="text-secondary" style={{ fontSize: '0.875rem' }}>
                                Generative UI dla Dyrektorów
                            </p>
                        </div>
                    </div>
                </div>
            </div>

            {}
            {recentEntries.length > 0 && (
                <div className="card mt-lg">
                    <div className="card-header">
                        <h3 className="card-title">
                            <span className="card-title-icon">📋</span>
                            Ostatnie Pozycje
                        </h3>
                        <button
                            className="btn btn-secondary btn-sm"
                            onClick={() => setActivePage('entries')}
                        >
                            Zobacz wszystkie →
                        </button>
                    </div>
                    <div className="table-container">
                        <table className="data-table">
                            <thead>
                                <tr>
                                    <th>Nazwa Zadania</th>
                                    <th>Paragraf</th>
                                    <th>Kwota 2025</th>
                                    <th>Status</th>
                                    <th>Priorytet</th>
                                </tr>
                            </thead>
                            <tbody>
                                {recentEntries.map((entry) => (
                                    <tr key={entry.id}>
                                        <td className="truncate" style={{ maxWidth: '300px' }}>
                                            {entry.nazwa_zadania || entry.opis_projektu || 'Brak nazwy'}
                                        </td>
                                        <td className="font-mono">{entry.paragraf || '-'}</td>
                                        <td>{formatCurrency(entry.kwota_2025)}</td>
                                        <td>
                                            <span className={`badge badge-${entry.status === 'approved' ? 'success' :
                                                    entry.status === 'rejected' ? 'danger' :
                                                        entry.status === 'submitted' ? 'info' : 'warning'
                                                }`}>
                                                {entry.status}
                                            </span>
                                        </td>
                                        <td>
                                            <span className={`badge badge-${entry.priority === 'obligatory' ? 'danger' :
                                                    entry.priority === 'high' ? 'warning' :
                                                        entry.priority === 'medium' ? 'info' : 'primary'
                                                }`}>
                                                {entry.priority}
                                            </span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}
        </div>
    );
}
