import { useState, useEffect } from 'react';
import api from '../services/api';

function AuditHistory({ setActivePage }) {
    const [auditLogs, setAuditLogs] = useState([]);
    const [entryHistory, setEntryHistory] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [selectedEntryId, setSelectedEntryId] = useState('');
    const [actionFilter, setActionFilter] = useState('');
    const [comparison, setComparison] = useState(null);
    const [selectedVersions, setSelectedVersions] = useState([]);

    useEffect(() => {
        loadAuditHistory();
    }, [actionFilter]);

    const loadAuditHistory = async () => {
        try {
            setLoading(true);
            const data = await api.getAllAuditHistory(100, actionFilter || null);
            setAuditLogs(data.history || []);
            setError(null);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const loadEntryHistory = async (entryId) => {
        if (!entryId) {
            setEntryHistory(null);
            return;
        }
        try {
            setLoading(true);
            const data = await api.getEntryHistory(entryId);
            setEntryHistory(data);
            setSelectedVersions([]);
            setComparison(null);
            setError(null);
        } catch (err) {
            setError(err.message);
            setEntryHistory(null);
        } finally {
            setLoading(false);
        }
    };

    const handleRestore = async (entryId, auditId, timestamp) => {
        if (!confirm(`Czy na pewno chcesz przywrócić wersję z ${timestamp}?`)) return;

        try {
            setLoading(true);
            await api.restoreVersion(entryId, auditId);
            alert('Wersja została przywrócona!');
            loadEntryHistory(entryId);
            loadAuditHistory();
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleCompare = async () => {
        if (selectedVersions.length !== 2) {
            alert('Wybierz dokładnie 2 wersje do porównania');
            return;
        }
        try {
            setLoading(true);
            const data = await api.compareVersions(
                entryHistory.entry_id,
                selectedVersions[0],
                selectedVersions[1]
            );
            setComparison(data);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const toggleVersionSelection = (auditId) => {
        setSelectedVersions(prev => {
            if (prev.includes(auditId)) {
                return prev.filter(id => id !== auditId);
            }
            if (prev.length >= 2) {
                return [prev[1], auditId];
            }
            return [...prev, auditId];
        });
    };

    const getActionBadge = (action) => {
        const styles = {
            CREATE: { bg: 'var(--success)', icon: '➕' },
            UPDATE: { bg: 'var(--warning)', icon: '✏️' },
            APPROVE: { bg: 'var(--success)', icon: '✅' },
            REJECT: { bg: 'var(--danger)', icon: '❌' },
            RESTORE: { bg: 'var(--info)', icon: '↩️' }
        };
        const style = styles[action] || { bg: 'var(--text-muted)', icon: '📝' };
        return (
            <span
                className="badge"
                style={{
                    background: style.bg,
                    color: 'white',
                    padding: '4px 8px',
                    borderRadius: '4px',
                    fontSize: '0.75rem',
                    fontWeight: '600'
                }}
            >
                {style.icon} {action}
            </span>
        );
    };

    const formatTimestamp = (timestamp) => {
        if (!timestamp) return 'Brak daty';
        return new Date(timestamp).toLocaleString('pl-PL', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    return (
        <div className="page-container">
            {/* Header */}
            <div className="page-header">
                <div>
                    <h1 className="page-title">
                        <span className="title-icon">📜</span>
                        Historia Zmian
                    </h1>
                    <p className="page-subtitle">
                        Pełna historia wersji • Przywracanie • Porównywanie
                    </p>
                </div>
                <div className="flex gap-md">
                    <button className="btn btn-secondary" onClick={loadAuditHistory}>
                        🔄 Odśwież
                    </button>
                </div>
            </div>

            {error && (
                <div className="card" style={{ background: 'var(--danger-bg)', borderColor: 'var(--danger)', marginBottom: 'var(--spacing-lg)' }}>
                    <p style={{ color: 'var(--danger)', margin: 0 }}>⚠️ {error}</p>
                </div>
            )}

            {/* Filters */}
            <div className="card mb-lg">
                <h3 className="mb-md">🔍 Filtry</h3>
                <div className="grid grid-cols-2 gap-md">
                    <div>
                        <label className="text-muted mb-xs" style={{ display: 'block', fontSize: '0.875rem' }}>
                            Filtruj po akcji:
                        </label>
                        <select
                            className="input"
                            value={actionFilter}
                            onChange={(e) => setActionFilter(e.target.value)}
                        >
                            <option value="">Wszystkie akcje</option>
                            <option value="CREATE">➕ CREATE - Tworzenie</option>
                            <option value="UPDATE">✏️ UPDATE - Edycja</option>
                            <option value="APPROVE">✅ APPROVE - Zatwierdzenie</option>
                            <option value="REJECT">❌ REJECT - Odrzucenie</option>
                            <option value="RESTORE">↩️ RESTORE - Przywrócenie</option>
                        </select>
                    </div>
                    <div>
                        <label className="text-muted mb-xs" style={{ display: 'block', fontSize: '0.875rem' }}>
                            Historia konkretnej pozycji (ID):
                        </label>
                        <div className="flex gap-sm">
                            <input
                                type="number"
                                className="input"
                                placeholder="ID pozycji budżetowej"
                                value={selectedEntryId}
                                onChange={(e) => setSelectedEntryId(e.target.value)}
                            />
                            <button
                                className="btn btn-primary"
                                onClick={() => loadEntryHistory(selectedEntryId)}
                                disabled={!selectedEntryId}
                            >
                                Pokaż historię
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            {/* Entry-specific history */}
            {entryHistory && (
                <div className="card mb-lg" style={{ borderColor: 'var(--primary)', borderWidth: '2px' }}>
                    <div className="flex justify-between items-center mb-md">
                        <div>
                            <h3>📋 Historia pozycji #{entryHistory.entry_id}</h3>
                            <p className="text-muted">{entryHistory.entry_name}</p>
                        </div>
                        <div className="flex gap-sm">
                            {selectedVersions.length === 2 && (
                                <button className="btn btn-secondary" onClick={handleCompare}>
                                    🔀 Porównaj wybrane ({selectedVersions.length}/2)
                                </button>
                            )}
                            <button className="btn btn-ghost" onClick={() => {
                                setEntryHistory(null);
                                setSelectedEntryId('');
                                setComparison(null);
                            }}>
                                ✕ Zamknij
                            </button>
                        </div>
                    </div>

                    <p className="text-secondary mb-md">
                        Łącznie zmian: <strong>{entryHistory.total_changes}</strong>
                        {selectedVersions.length > 0 && (
                            <span className="ml-md">
                                | Zaznaczono do porównania: <strong>{selectedVersions.length}</strong>
                            </span>
                        )}
                    </p>

                    {/* Version comparison result */}
                    {comparison && (
                        <div className="mb-lg p-md" style={{ background: 'var(--bg-darker)', borderRadius: 'var(--radius-md)' }}>
                            <h4 className="mb-md">🔀 Porównanie wersji</h4>
                            <div className="grid grid-cols-2 gap-md mb-md">
                                <div className="p-sm" style={{ background: 'var(--bg-dark)', borderRadius: 'var(--radius-sm)' }}>
                                    <p className="text-muted text-sm">Wersja A</p>
                                    <p>{comparison.version_a.action} @ {formatTimestamp(comparison.version_a.timestamp)}</p>
                                </div>
                                <div className="p-sm" style={{ background: 'var(--bg-dark)', borderRadius: 'var(--radius-sm)' }}>
                                    <p className="text-muted text-sm">Wersja B</p>
                                    <p>{comparison.version_b.action} @ {formatTimestamp(comparison.version_b.timestamp)}</p>
                                </div>
                            </div>
                            {comparison.differences.length > 0 ? (
                                <table className="table">
                                    <thead>
                                        <tr>
                                            <th>Pole</th>
                                            <th>Wersja A</th>
                                            <th>Wersja B</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {comparison.differences.map((diff, idx) => (
                                            <tr key={idx}>
                                                <td><strong>{diff.field}</strong></td>
                                                <td style={{ color: 'var(--danger)' }}>{String(diff.version_a)}</td>
                                                <td style={{ color: 'var(--success)' }}>{String(diff.version_b)}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            ) : (
                                <p className="text-success">✅ Brak różnic między wersjami</p>
                            )}
                            <button className="btn btn-ghost mt-md" onClick={() => setComparison(null)}>
                                Zamknij porównanie
                            </button>
                        </div>
                    )}

                    {/* History timeline */}
                    <div className="timeline">
                        {entryHistory.history.map((log, idx) => (
                            <div
                                key={log.id}
                                className="timeline-item p-md mb-sm"
                                style={{
                                    background: selectedVersions.includes(log.id) ? 'var(--primary-bg)' : 'var(--bg-dark)',
                                    borderRadius: 'var(--radius-md)',
                                    borderLeft: `4px solid ${selectedVersions.includes(log.id) ? 'var(--primary)' : 'var(--border-color)'}`,
                                    cursor: 'pointer'
                                }}
                                onClick={() => toggleVersionSelection(log.id)}
                            >
                                <div className="flex justify-between items-start">
                                    <div>
                                        <div className="flex items-center gap-sm mb-sm">
                                            {getActionBadge(log.action)}
                                            <span className="text-muted text-sm">{formatTimestamp(log.timestamp)}</span>
                                            {selectedVersions.includes(log.id) && (
                                                <span className="badge" style={{ background: 'var(--primary)' }}>
                                                    ✓ Wybrano
                                                </span>
                                            )}
                                        </div>
                                        <p className="text-secondary">{log.notes}</p>
                                        <p className="text-muted text-sm mt-xs">Użytkownik: {log.user_id}</p>
                                    </div>
                                    {log.old_values && idx > 0 && (
                                        <button
                                            className="btn btn-sm btn-warning"
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                handleRestore(entryHistory.entry_id, log.id, log.timestamp);
                                            }}
                                        >
                                            ↩️ Przywróć
                                        </button>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Global audit log */}
            <div className="card">
                <h3 className="mb-md">📊 Globalna historia zmian</h3>

                {loading ? (
                    <div className="text-center p-xl">
                        <div className="spinner"></div>
                        <p className="text-muted mt-md">Ładowanie historii...</p>
                    </div>
                ) : auditLogs.length === 0 ? (
                    <div className="text-center p-xl">
                        <p className="text-muted">Brak zapisanych zmian w historii</p>
                        <p className="text-sm text-muted mt-sm">
                            Zmiany pojawią się po utworzeniu lub edycji pozycji budżetowych
                        </p>
                    </div>
                ) : (
                    <div className="table-container">
                        <table className="table">
                            <thead>
                                <tr>
                                    <th>Akcja</th>
                                    <th>ID Pozycji</th>
                                    <th>Nazwa</th>
                                    <th>Data</th>
                                    <th>Użytkownik</th>
                                    <th>Szczegóły</th>
                                    <th>Akcje</th>
                                </tr>
                            </thead>
                            <tbody>
                                {auditLogs.map((log) => (
                                    <tr key={log.id}>
                                        <td>{getActionBadge(log.action)}</td>
                                        <td>
                                            <span className="badge" style={{ background: 'var(--bg-darker)' }}>
                                                #{log.entry_id}
                                            </span>
                                        </td>
                                        <td className="text-secondary" style={{ maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                            {log.entry_name}
                                        </td>
                                        <td className="text-muted text-sm">{formatTimestamp(log.timestamp)}</td>
                                        <td className="text-muted">{log.user_id}</td>
                                        <td className="text-sm" style={{ maxWidth: '250px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                            {log.notes}
                                        </td>
                                        <td>
                                            <button
                                                className="btn btn-sm btn-ghost"
                                                onClick={() => {
                                                    setSelectedEntryId(String(log.entry_id));
                                                    loadEntryHistory(log.entry_id);
                                                }}
                                            >
                                                📜 Historia
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* Stats footer */}
            <div className="grid grid-cols-4 gap-md mt-lg">
                <div className="card text-center">
                    <div className="text-3xl mb-sm">📝</div>
                    <div className="text-2xl font-bold text-primary">
                        {auditLogs.filter(l => l.action === 'CREATE').length}
                    </div>
                    <div className="text-muted text-sm">Utworzono</div>
                </div>
                <div className="card text-center">
                    <div className="text-3xl mb-sm">✏️</div>
                    <div className="text-2xl font-bold text-warning">
                        {auditLogs.filter(l => l.action === 'UPDATE').length}
                    </div>
                    <div className="text-muted text-sm">Edytowano</div>
                </div>
                <div className="card text-center">
                    <div className="text-3xl mb-sm">✅</div>
                    <div className="text-2xl font-bold text-success">
                        {auditLogs.filter(l => l.action === 'APPROVE').length}
                    </div>
                    <div className="text-muted text-sm">Zatwierdzono</div>
                </div>
                <div className="card text-center">
                    <div className="text-3xl mb-sm">❌</div>
                    <div className="text-2xl font-bold text-danger">
                        {auditLogs.filter(l => l.action === 'REJECT').length}
                    </div>
                    <div className="text-muted text-sm">Odrzucono</div>
                </div>
            </div>
        </div>
    );
}

export default AuditHistory;
