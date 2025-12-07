import { useState, useEffect } from 'react';
import api from '../services/api';

export default function Optimization() {
    const [loading, setLoading] = useState(false);
    const [gapAnalysis, setGapAnalysis] = useState(null);
    const [suggestions, setSuggestions] = useState(null);
    const [applying, setApplying] = useState(null);

    useEffect(() => {
        loadGapAnalysis();
    }, []);

    const loadGapAnalysis = async () => {
        setLoading(true);
        try {
            const data = await api.getGapAnalysis();
            setGapAnalysis(data.data || data);
        } catch (error) {
            console.error('Failed to load gap analysis:', error);
        }
        setLoading(false);
    };

    const handleSuggestCuts = async () => {
        setLoading(true);
        try {
            const response = await api.suggestCuts();
            setSuggestions(response.data || response);
        } catch (error) {
            alert('Failed to generate suggestions: ' + error.message);
        }
        setLoading(false);
    };

    const handleApplySuggestion = async (suggestion) => {
        if (!confirm(`Czy na pewno chcesz zastosować "${suggestion.action}" dla "${suggestion.nazwa}"?`)) return;

        setApplying(suggestion.entry_id);
        try {
            await api.applyOptimization(
                suggestion.entry_id,
                suggestion.action,
                suggestion.suggested_amount
            );
            loadGapAnalysis();
            handleSuggestCuts();
        } catch (error) {
            alert('Failed to apply: ' + error.message);
        }
        setApplying(null);
    };

    const formatCurrency = (value) => {
        if (!value && value !== 0) return '-';
        return new Intl.NumberFormat('pl-PL', {
            style: 'decimal',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        }).format(value) + ' tys. PLN';
    };

    if (loading && !gapAnalysis) {
        return (
            <div className="loading-overlay" style={{ position: 'relative', minHeight: '400px' }}>
                <div className="loading-spinner"></div>
            </div>
        );
    }

    const isOverLimit = gapAnalysis?.is_over_limit;

    return (
        <div className="animate-fade-in">
            <div className="flex justify-between items-center mb-xl">
                <div>
                    <h1 style={{ fontSize: '1.75rem', marginBottom: '0.25rem' }}>
                        📊 Limit Negotiator Agent
                    </h1>
                    <p className="text-secondary">
                        Inteligentna optymalizacja budżetu i sugestie cięć
                    </p>
                </div>
            </div>

            {}
            {gapAnalysis && (
                <div className="stats-grid mb-xl">
                    <div className={`stat-card ${isOverLimit ? 'warning' : 'success'}`}>
                        <div className="stat-icon primary">🎯</div>
                        <div className="stat-value">{formatCurrency(gapAnalysis.global_limit)}</div>
                        <div className="stat-label">Limit Globalny 2025</div>
                    </div>

                    <div className="stat-card">
                        <div className="stat-icon warning">📈</div>
                        <div className="stat-value">{formatCurrency(gapAnalysis.current_total)}</div>
                        <div className="stat-label">Aktualne Zapotrzebowanie</div>
                    </div>

                    <div className={`stat-card ${isOverLimit ? 'warning' : ''}`}>
                        <div className={`stat-icon ${isOverLimit ? 'error' : 'success'}`}>
                            {isOverLimit ? '⚠️' : '✅'}
                        </div>
                        <div className={`stat-value ${isOverLimit ? 'negative' : 'positive'}`}>
                            {isOverLimit ? '+' : ''}{formatCurrency(gapAnalysis.variance)}
                        </div>
                        <div className="stat-label">
                            {isOverLimit ? 'Do Redukcji' : 'Rezerwa'}
                        </div>
                    </div>

                    <div className="stat-card">
                        <div className="stat-icon success">📊</div>
                        <div className="stat-value">
                            {gapAnalysis.over_percentage?.toFixed(1) || 0}%
                        </div>
                        <div className="stat-label">Przekroczenie %</div>
                    </div>
                </div>
            )}

            {}
            {gapAnalysis?.priority_breakdown && (
                <div className="card mb-xl">
                    <div className="card-header">
                        <h3 className="card-title">
                            <span className="card-title-icon">📋</span>
                            Podział wg Priorytetu
                        </h3>
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '1rem' }}>
                        {Object.entries(gapAnalysis.priority_breakdown).map(([priority, amount]) => (
                            <div key={priority} className="p-md" style={{ background: 'var(--bg-darker)', borderRadius: 'var(--radius-md)' }}>
                                <div className="text-secondary" style={{ fontSize: '0.75rem', marginBottom: '0.25rem', textTransform: 'capitalize' }}>
                                    {priority === 'obligatory' ? '🔒' :
                                        priority === 'high' ? '🔴' :
                                            priority === 'medium' ? '🟡' :
                                                priority === 'low' ? '🟢' : '⚪'} {priority}
                                </div>
                                <div className="font-bold">
                                    {formatCurrency(amount)}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {}
            {isOverLimit && !suggestions && (
                <div className="agent-card mb-xl">
                    <div className="agent-header">
                        <div className="agent-avatar">🤖</div>
                        <div>
                            <div className="agent-name">Limit Negotiator Agent</div>
                            <div className="agent-action">Gotowy do analizy</div>
                        </div>
                    </div>
                    <div className="agent-body">
                        <div className="alert alert-warning mb-md">
                            <span className="alert-icon">⚠️</span>
                            <div>
                                <strong>Wymagana redukcja budżetu!</strong>
                                <p>Limit został przekroczony o <strong>{formatCurrency(gapAnalysis?.variance)}</strong>.
                                    Agent może zasugerować optymalne cięcia, priorytetyzując zadania obligatoryjne i cyberbezpieczeństwo.</p>
                            </div>
                        </div>
                        <button
                            className="btn btn-primary btn-lg"
                            onClick={handleSuggestCuts}
                            disabled={loading}
                        >
                            {loading ? '⏳ Analizuję...' : '🔮 Wygeneruj Sugestie Cięć'}
                        </button>
                    </div>
                </div>
            )}

            {}
            {suggestions && (
                <div className="agent-card animate-slide-in">
                    <div className="agent-header">
                        <div className="agent-avatar">🤖</div>
                        <div>
                            <div className="agent-name">Limit Negotiator Agent</div>
                            <div className="agent-action">Sugestie Optymalizacji</div>
                        </div>
                    </div>
                    <div className="agent-body">
                        {}
                        <div className="alert alert-info mb-lg">
                            <span className="alert-icon">📊</span>
                            <div>
                                <strong>Podsumowanie Analizy</strong>
                                <p>Cel redukcji: <strong>{formatCurrency(suggestions.target_reduction)}</strong></p>
                                <p>Możliwa redukcja: <strong>{formatCurrency(suggestions.achievable_reduction)}</strong></p>
                                {suggestions.can_meet_target ? (
                                    <p className="text-success">✅ Możliwe osiągnięcie celu bez cięcia zadań obligatoryjnych</p>
                                ) : (
                                    <p className="text-danger">⚠️ Wymagane decyzje Kierownictwa dot. zadań obligatoryjnych</p>
                                )}
                            </div>
                        </div>

                        {}
                        {suggestions.protected_items?.length > 0 && (
                            <div className="mb-lg">
                                <h4 className="mb-md">🔒 Zadania Chronione (Obligatoryjne)</h4>
                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                                    {suggestions.protected_items.map((item) => (
                                        <span key={item.entry_id} className="badge badge-danger">
                                            {(item.nazwa || 'Zadanie').substring(0, 40)}... ({formatCurrency(item.amount)})
                                        </span>
                                    ))}
                                </div>
                            </div>
                        )}

                        {}
                        <h4 className="mb-md">💡 Sugestie Optymalizacji</h4>
                        {suggestions.suggestions?.map((suggestion, index) => (
                            <div key={suggestion.entry_id} className="suggestion-item">
                                <div className={`suggestion-icon ${suggestion.action}`}>
                                    {suggestion.action === 'defer' ? '⏸️' : '📉'}
                                </div>
                                <div className="suggestion-content">
                                    <div className="suggestion-title">
                                        {index + 1}. {suggestion.nazwa?.substring(0, 60) || 'Brak nazwy'}...
                                    </div>
                                    <div className="suggestion-meta">
                                        <span>Dept: {suggestion.department}</span>
                                        <span style={{ margin: '0 0.5rem' }}>•</span>
                                        <span>Priorytet: {suggestion.priority}</span>
                                        <span style={{ margin: '0 0.5rem' }}>•</span>
                                        <span>Akcja: <strong>{suggestion.action === 'defer' ? 'Przełóż' : 'Zredukuj'}</strong></span>
                                    </div>
                                    <div className="flex gap-md mt-sm items-center">
                                        <span>
                                            {formatCurrency(suggestion.current_amount)} → {formatCurrency(suggestion.suggested_amount)}
                                        </span>
                                        <span className="suggestion-savings">
                                            Oszczędność: {formatCurrency(suggestion.savings)}
                                        </span>
                                    </div>
                                    <div className="text-secondary mt-sm" style={{ fontSize: '0.8rem' }}>
                                        {suggestion.reason}
                                    </div>
                                </div>
                                <button
                                    className="btn btn-sm btn-success"
                                    onClick={() => handleApplySuggestion(suggestion)}
                                    disabled={applying === suggestion.entry_id}
                                >
                                    {applying === suggestion.entry_id ? '⏳' : '✓ Zastosuj'}
                                </button>
                            </div>
                        ))}

                        <div className="flex justify-between mt-lg">
                            <button className="btn btn-secondary" onClick={loadGapAnalysis}>
                                🔄 Odśwież
                            </button>
                            <button className="btn btn-primary" onClick={handleSuggestCuts}>
                                🔮 Przelicz Sugestie
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {}
            {!isOverLimit && gapAnalysis && (
                <div className="agent-card">
                    <div className="agent-header">
                        <div className="agent-avatar" style={{ background: 'linear-gradient(135deg, var(--success) 0%, var(--accent-teal) 100%)' }}>✅</div>
                        <div>
                            <div className="agent-name" style={{ color: 'var(--success)' }}>Status: OK</div>
                            <div className="agent-action">Budżet w limicie</div>
                        </div>
                    </div>
                    <div className="agent-body">
                        <div className="alert alert-success">
                            <span className="alert-icon">🎉</span>
                            <div>
                                <strong>Gratulacje!</strong>
                                <p>Budżet mieści się w przydzielonym limicie. Pozostała rezerwa: <strong>{formatCurrency(Math.abs(gapAnalysis.variance))}</strong></p>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
