import { useState, useEffect } from 'react';
import api from '../services/api';

export default function Conflicts() {
    const [loading, setLoading] = useState(false);
    const [summary, setSummary] = useState(null);
    const [conflicts, setConflicts] = useState(null);
    const [resolving, setResolving] = useState(null);

    useEffect(() => {
        loadSummary();
    }, []);

    const loadSummary = async () => {
        try {
            const data = await api.getConflictsSummary();
            setSummary(data);
        } catch (error) {
            console.error('Failed to load conflict summary:', error);
        }
    };

    const handleDetectConflicts = async () => {
        setLoading(true);
        try {
            const response = await api.detectConflicts();
            setConflicts(response.data || response);
            loadSummary();
        } catch (error) {
            alert('Detection failed: ' + error.message);
        }
        setLoading(false);
    };

    const handleResolve = async (conflict, resolution, keepEntryId = null) => {
        setResolving(conflict.entry_a_id + '-' + conflict.entry_b_id);
        try {
            await api.resolveConflict(conflict.entry_a_id, resolution, keepEntryId);
            handleDetectConflicts();
        } catch (error) {
            alert('Resolution failed: ' + error.message);
        }
        setResolving(null);
    };

    const formatCurrency = (value) => {
        if (!value && value !== 0) return '-';
        return new Intl.NumberFormat('pl-PL').format(value) + ' tys. PLN';
    };

    return (
        <div className="animate-fade-in">
            <div className="flex justify-between items-center mb-xl">
                <div>
                    <h1 style={{ fontSize: '1.75rem', marginBottom: '0.25rem' }}>
                        🔄 Conflict Resolution Agent
                    </h1>
                    <p className="text-secondary">
                        Wykrywanie duplikatów i semantycznych konfliktów między departamentami
                    </p>
                </div>
                <button
                    className="btn btn-primary btn-lg"
                    onClick={handleDetectConflicts}
                    disabled={loading}
                >
                    {loading ? '⏳ Skanowanie...' : '🔍 Skanuj w poszukiwaniu konfliktów'}
                </button>
            </div>

            {}
            {summary && (
                <div className="stats-grid mb-xl">
                    <div className="stat-card">
                        <div className="stat-icon warning">🔄</div>
                        <div className="stat-value">{summary.total_conflicts || 0}</div>
                        <div className="stat-label">Wszystkich Konfliktów</div>
                    </div>

                    <div className={`stat-card ${summary.pending > 0 ? 'warning' : ''}`}>
                        <div className={`stat-icon ${summary.pending > 0 ? 'warning' : 'success'}`}>
                            {summary.pending > 0 ? '⏳' : '✅'}
                        </div>
                        <div className={`stat-value ${summary.pending > 0 ? 'negative' : 'positive'}`}>
                            {summary.pending || 0}
                        </div>
                        <div className="stat-label">Oczekujących</div>
                    </div>

                    <div className="stat-card success">
                        <div className="stat-icon success">✅</div>
                        <div className="stat-value positive">{summary.resolved || 0}</div>
                        <div className="stat-label">Rozwiązanych</div>
                    </div>
                </div>
            )}

            {}
            <div className="card mb-xl">
                <div className="card-header">
                    <h3 className="card-title">
                        <span className="card-title-icon">💡</span>
                        Jak Działa Agent?
                    </h3>
                </div>
                <div className="agent-body">
                    <p className="mb-md">
                        Agent porównuje wszystkie pozycje budżetowe między departamentami, szukając:
                    </p>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1rem' }}>
                        <div className="p-md" style={{ background: 'var(--bg-darker)', borderRadius: 'var(--radius-md)', borderLeft: '3px solid var(--error)' }}>
                            <h5 className="mb-sm">🔴 Duplikaty (85%+ podobieństwa)</h5>
                            <p className="text-secondary" style={{ fontSize: '0.875rem' }}>
                                Identyczne lub bardzo podobne zapotrzebowania - sugestia konsolidacji
                            </p>
                        </div>
                        <div className="p-md" style={{ background: 'var(--bg-darker)', borderRadius: 'var(--radius-md)', borderLeft: '3px solid var(--warning)' }}>
                            <h5 className="mb-sm">🟡 Nakładanie się (70-85%)</h5>
                            <p className="text-secondary" style={{ fontSize: '0.875rem' }}>
                                Częściowo pokrywające się potrzeby - możliwa synergia
                            </p>
                        </div>
                        <div className="p-md" style={{ background: 'var(--bg-darker)', borderRadius: 'var(--radius-md)', borderLeft: '3px solid var(--info)' }}>
                            <h5 className="mb-sm">🔵 Podobne (60-70%)</h5>
                            <p className="text-secondary" style={{ fontSize: '0.875rem' }}>
                                Semantycznie powiązane - warto sprawdzić
                            </p>
                        </div>
                    </div>
                </div>
            </div>

            {}
            {conflicts && (
                <div className="agent-card animate-slide-in">
                    <div className="agent-header">
                        <div className="agent-avatar">🤖</div>
                        <div>
                            <div className="agent-name">Conflict Resolution Agent</div>
                            <div className="agent-action">Wykryte Konflikty</div>
                        </div>
                    </div>
                    <div className="agent-body">
                        {conflicts.conflicts?.length === 0 ? (
                            <div className="alert alert-success">
                                <span className="alert-icon">🎉</span>
                                <div>
                                    <strong>Brak Konfliktów!</strong>
                                    <p>Nie wykryto semantycznych duplikatów między departamentami.</p>
                                </div>
                            </div>
                        ) : (
                            <>
                                <div className="alert alert-warning mb-lg">
                                    <span className="alert-icon">📊</span>
                                    <div>
                                        <strong>Wykryto {conflicts.conflicts?.length || 0} potencjalnych konfliktów</strong>
                                        <p>Konsolidacja może przynieść oszczędności ~15% na zakupach hurtowych.</p>
                                    </div>
                                </div>

                                {conflicts.conflicts?.map((conflict, index) => (
                                    <div key={index} className="card mb-md" style={{ padding: 'var(--spacing-lg)' }}>
                                        <div className="flex justify-between items-center mb-md">
                                            <span className={`badge ${conflict.conflict_type === 'duplicate' ? 'badge-danger' :
                                                    conflict.conflict_type === 'overlap' ? 'badge-warning' : 'badge-info'
                                                }`}>
                                                {conflict.conflict_type === 'duplicate' ? '🔴 Duplikat' :
                                                    conflict.conflict_type === 'overlap' ? '🟡 Nakładanie' : '🔵 Podobne'}
                                            </span>
                                            <span className="text-secondary">
                                                Podobieństwo: <strong>{(conflict.similarity_score * 100).toFixed(0)}%</strong>
                                            </span>
                                        </div>

                                        <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', gap: '1rem', alignItems: 'center' }}>
                                            {}
                                            <div className="p-md" style={{ background: 'var(--bg-darker)', borderRadius: 'var(--radius-md)' }}>
                                                <div className="badge badge-primary mb-sm">{conflict.entry_a_department}</div>
                                                <div className="font-semibold mb-sm" style={{ fontSize: '0.9rem' }}>
                                                    {conflict.entry_a_name || 'Brak nazwy'}
                                                </div>
                                                <div className="text-success font-bold">
                                                    {formatCurrency(conflict.entry_a_amount)}
                                                </div>
                                            </div>

                                            {}
                                            <div style={{ fontSize: '1.5rem', opacity: 0.5 }}>⚔️</div>

                                            {}
                                            <div className="p-md" style={{ background: 'var(--bg-darker)', borderRadius: 'var(--radius-md)' }}>
                                                <div className="badge badge-primary mb-sm">{conflict.entry_b_department}</div>
                                                <div className="font-semibold mb-sm" style={{ fontSize: '0.9rem' }}>
                                                    {conflict.entry_b_name || 'Brak nazwy'}
                                                </div>
                                                <div className="text-success font-bold">
                                                    {formatCurrency(conflict.entry_b_amount)}
                                                </div>
                                            </div>
                                        </div>

                                        <div className="alert alert-info mt-md" style={{ marginBottom: 0 }}>
                                            <span className="alert-icon">💡</span>
                                            <div>
                                                <strong>{conflict.suggested_action}</strong>
                                                <p>Potencjalna oszczędność: <strong className="text-success">{formatCurrency(conflict.potential_savings)}</strong></p>
                                            </div>
                                        </div>

                                        <div className="flex gap-sm mt-md justify-between">
                                            <button
                                                className="btn btn-success btn-sm"
                                                onClick={() => handleResolve(conflict, 'consolidate', conflict.entry_a_id)}
                                                disabled={resolving === conflict.entry_a_id + '-' + conflict.entry_b_id}
                                            >
                                                🔗 Konsoliduj (zachowaj A)
                                            </button>
                                            <button
                                                className="btn btn-success btn-sm"
                                                onClick={() => handleResolve(conflict, 'consolidate', conflict.entry_b_id)}
                                                disabled={resolving === conflict.entry_a_id + '-' + conflict.entry_b_id}
                                            >
                                                🔗 Konsoliduj (zachowaj B)
                                            </button>
                                            <button
                                                className="btn btn-secondary btn-sm"
                                                onClick={() => handleResolve(conflict, 'keep_both')}
                                                disabled={resolving === conflict.entry_a_id + '-' + conflict.entry_b_id}
                                            >
                                                ✓ Zachowaj oba
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </>
                        )}
                    </div>
                </div>
            )}

            {}
            <div className="card">
                <div className="card-header">
                    <h3 className="card-title">
                        <span className="card-title-icon">📋</span>
                        Przykład Scenariusza
                    </h3>
                </div>
                <div className="agent-body">
                    <div className="p-lg" style={{ background: 'var(--bg-darker)', borderRadius: 'var(--radius-md)' }}>
                        <p className="mb-md"><strong>Sytuacja:</strong></p>
                        <p className="mb-lg text-secondary">
                            Departament A i Departament B <strong>obydwa</strong> zgłosiły zapotrzebowanie na "Licencje Microsoft Office 365" - każdy w swoim pliku Excel.
                        </p>

                        <p className="mb-md"><strong>Standardowe scalanie:</strong></p>
                        <p className="mb-lg text-secondary">
                            ❌ Tworzy dwie osobne pozycje → płacimy 2x za tę samą rzecz
                        </p>

                        <p className="mb-md"><strong>Skarbnik AI:</strong></p>
                        <div className="alert alert-success">
                            <span className="alert-icon">🤖</span>
                            <div>
                                <strong>Wykryto podobieństwo potrzeb!</strong>
                                <p>Zarówno Dept A jak i Dept B zgłosiły zapotrzebowanie na licencje Office.
                                    Czy skonsolidować pod jednym departamentem (IT) dla oszczędności na zakupie hurtowym?</p>
                                <p className="text-success mt-sm">💰 Szacowana oszczędność: ~15% wartości zamówienia</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
