import { useState, useEffect } from 'react';
import api from '../services/api';

export default function Compliance() {
    const [loading, setLoading] = useState(false);
    const [summary, setSummary] = useState(null);
    const [validationResults, setValidationResults] = useState(null);
    const [docs, setDocs] = useState(null);

    useEffect(() => {
        loadSummary();
    }, []);

    const loadSummary = async () => {
        try {
            const [summaryData, docsData] = await Promise.all([
                api.getComplianceSummary(),
                api.getKnowledgeFiles()
            ]);
            setSummary(summaryData);
            setDocs(docsData);
        } catch (error) {
            console.error('Failed to load compliance data:', error);
        }
    };

    const handleValidateAll = async () => {
        setLoading(true);
        try {
            const response = await api.validateAllEntries();
            setValidationResults(response.data || response);
            loadSummary();
        } catch (error) {
            alert('Validation failed: ' + error.message);
        }
        setLoading(false);
    };

    const handleSemanticAudit = async (entryId) => {
        try {
            const btn = document.getElementById(`audit-btn-${entryId}`);
            if (btn) btn.innerHTML = '🕵️ Analiza AI...';

            const response = await api.semanticValidateEntry(entryId);

            // Append semantic result to the specific result item in state
            setValidationResults(prev => {
                const newResults = [...prev.results];
                const idx = newResults.findIndex(r => r.entry_id === entryId);
                if (idx !== -1) {
                    newResults[idx].semantic = response.data;
                }
                return { ...prev, results: newResults };
            });

            if (btn) btn.innerHTML = '🕵️ Pełny Audyt AI';
        } catch (error) {
            alert('AI Audit failed: ' + error.message);
        }
    };

    return (
        <div className="animate-fade-in">
            <div className="flex justify-between items-center mb-xl">
                <div>
                    <h1 style={{ fontSize: '1.75rem', marginBottom: '0.25rem' }}>
                        ✅ Compliance Agent
                    </h1>
                    <p className="text-secondary">
                        Walidacja zgodności z Rozporządzeniami MF
                    </p>
                </div>
                <button
                    className="btn btn-primary btn-lg"
                    onClick={handleValidateAll}
                    disabled={loading}
                >
                    {loading ? '⏳ Walidacja...' : '🔍 Zwaliduj Wszystkie Pozycje'}
                </button>
            </div>

            { }
            {summary && (
                <div className="stats-grid mb-xl">
                    <div className="stat-card">
                        <div className="stat-icon primary">📝</div>
                        <div className="stat-value">{summary.total_entries || 0}</div>
                        <div className="stat-label">Wszystkich Pozycji</div>
                    </div>

                    <div className="stat-card success">
                        <div className="stat-icon success">✅</div>
                        <div className="stat-value">{summary.validated || 0}</div>
                        <div className="stat-label">Zwalidowanych</div>
                    </div>

                    <div className={`stat-card ${summary.with_warnings > 0 ? 'warning' : ''}`}>
                        <div className={`stat-icon ${summary.with_warnings > 0 ? 'warning' : 'success'}`}>
                            {summary.with_warnings > 0 ? '⚠️' : '✓'}
                        </div>
                        <div className={`stat-value ${summary.with_warnings > 0 ? 'negative' : 'positive'}`}>
                            {summary.with_warnings || 0}
                        </div>
                        <div className="stat-label">Z Ostrzeżeniami</div>
                    </div>

                    <div className="stat-card">
                        <div className="stat-icon success">📊</div>
                        <div className={`stat-value ${summary.compliance_rate >= 80 ? 'positive' : 'negative'}`}>
                            {(summary.compliance_rate || 100).toFixed(1)}%
                        </div>
                        <div className="stat-label">Wskaźnik Zgodności</div>
                    </div>
                </div>
            )}

            { }
            <div className="card mb-xl">
                <div className="card-header">
                    <h3 className="card-title">
                        <span className="card-title-icon">📚</span>
                        Baza Wiedzy (RAG Context)
                    </h3>
                    <div className="badge badge-primary">
                        {docs?.length || 0} Dokumentów Zindeksowanych
                    </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '0.75rem' }}>
                    {docs ? docs.map((doc, idx) => (
                        <div key={idx} className="p-md flex items-center gap-md" style={{ background: 'var(--bg-darker)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
                            <div style={{ fontSize: '2rem' }}>
                                {doc.type === 'PDF' ? '📕' : '📊'}
                            </div>
                            <div style={{ flex: 1, overflow: 'hidden' }}>
                                <a href={doc.url} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline font-bold block truncate" title={doc.name}>
                                    {doc.name}
                                </a>
                                <div className="flex justify-between items-center mt-xs">
                                    <span className="text-secondary" style={{ fontSize: '0.75rem' }}>{doc.size}</span>
                                    <span className="badge badge-success" style={{ fontSize: '0.6rem', padding: '2px 6px' }}>
                                        ✓ AI READY
                                    </span>
                                </div>
                            </div>
                        </div>
                    )) : (
                        <div className="p-lg text-center text-secondary">Ładowanie bazy wiedzy...</div>
                    )}
                </div>
            </div>

            { }
            {validationResults && (
                <div className="agent-card animate-slide-in">
                    <div className="agent-header">
                        <div className="agent-avatar">🤖</div>
                        <div>
                            <div className="agent-name">Compliance Agent</div>
                            <div className="agent-action">Wyniki Walidacji</div>
                        </div>
                    </div>
                    <div className="agent-body">
                        <div className="alert alert-info mb-lg">
                            <span className="alert-icon">📋</span>
                            <div>
                                <strong>Walidacja Zakończona</strong>
                                <p>Zwalidowano {validationResults.summary?.total_entries || 0} pozycji.
                                    {validationResults.summary?.with_warnings || 0} wymaga uwagi.</p>
                            </div>
                        </div>

                        { }
                        {validationResults.results?.filter(r => r.validation?.warnings?.length > 0).map((result) => (
                            <div key={result.entry_id} className="suggestion-item" style={{ borderLeftColor: 'var(--warning)' }}>
                                <div className="suggestion-icon" style={{ background: 'rgba(255, 152, 0, 0.15)', color: 'var(--warning)' }}>
                                    ⚠️
                                </div>
                                <div className="suggestion-content">
                                    <div className="suggestion-title">
                                        ID: {result.entry_id} - {(result.nazwa || 'Brak nazwy').substring(0, 60)}
                                    </div>
                                    <div className="agent-warnings mt-sm">
                                        {result.validation.warnings.map((warning, idx) => (
                                            <div key={idx} className="alert alert-warning mb-sm" style={{ padding: '0.5rem 1rem' }}>
                                                {warning}
                                            </div>
                                        ))}
                                    </div>
                                    {result.validation.auto_corrections?.length > 0 && (
                                        <div className="mt-sm">
                                            <strong className="text-info">🔧 Sugerowane Korekty:</strong>
                                            {result.validation.auto_corrections.map((correction, idx) => (
                                                <div key={idx} className="text-secondary mt-sm" style={{ fontSize: '0.85rem' }}>
                                                    {correction.field}: {correction.original} → {correction.corrected}
                                                    <br />
                                                    <em>{correction.reason}</em>
                                                </div>
                                            ))}
                                        </div>
                                    )}

                                    <div className="mt-md pt-sm" style={{ borderTop: '1px solid rgba(255,255,255,0.1)' }}>
                                        {!result.semantic ? (
                                            <button
                                                id={`audit-btn-${result.entry_id}`}
                                                className="btn btn-sm btn-ai"
                                                onClick={() => handleSemanticAudit(result.entry_id)}
                                            >
                                                🕵️ Pełny Audyt AI (Semantyczny)
                                            </button>
                                        ) : (
                                            <div className="audit-result p-sm mt-sm" style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '4px' }}>
                                                <div className="flex items-center gap-sm mb-sm">
                                                    <span style={{ fontSize: '1.2rem' }}>🕵️</span>
                                                    <strong>Skarbnik AI Judge</strong>
                                                </div>

                                                {!result.semantic.is_compliant ? (
                                                    <>
                                                        <div className="text-danger font-bold mb-xs">
                                                            RYZYKO: {result.semantic.risk_level?.toUpperCase()}
                                                        </div>
                                                        <div className="mb-xs">
                                                            <strong>Naruszenie:</strong> {result.semantic.legal_citation}
                                                        </div>
                                                        <div className="mb-xs">
                                                            <strong>Uzasadnienie:</strong> {result.semantic.reasoning}
                                                        </div>
                                                        <div className="text-success">
                                                            <strong>Sugestia:</strong> {result.semantic.suggestion}
                                                        </div>
                                                    </>
                                                ) : (
                                                    <div className="text-success">
                                                        ✅ Analiza semantyczna nie wykryła ukrytych zagrożeń.
                                                    </div>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                </div>
                                <div className="text-center">
                                    <div className={`badge ${result.validation.compliance_score >= 70 ? 'badge-success' : 'badge-danger'}`}>
                                        {result.validation.compliance_score}%
                                    </div>
                                </div>
                            </div>
                        ))}

                        {!validationResults.results?.filter(r => r.validation?.warnings?.length > 0).length && (
                            <div className="alert alert-success">
                                <span className="alert-icon">🎉</span>
                                <div>
                                    <strong>Brak ostrzeżeń!</strong>
                                    <p>Wszystkie pozycje są zgodne z regulacjami.</p>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}

            <div className="card">
                <div className="card-header">
                    <h3 className="card-title">
                        <span className="card-title-icon">💡</span>
                        Przykład Działania Agenta
                    </h3>
                </div>
                <div className="agent-body p-lg" style={{ background: 'var(--bg-darker)', borderRadius: 'var(--radius-md)' }}>
                    <p className="mb-md">
                        Gdy użytkownik próbuje zabudżetować <strong>"Zakup serwera"</strong> pod paragrafem <strong>4210</strong> (Zakup materiałów), Agent wykrywa błąd:
                    </p>
                    <div className="alert alert-warning">
                        <span className="alert-icon">⚠️</span>
                        <div>
                            <strong>Ostrzeżenie o Zgodności</strong>
                            <p>Zgodnie z Rozporządzeniem 2c, zakup sprzętu typu 'serwer' kwalifikuje się jako <strong>'Zakupy inwestycyjne'</strong> (Paragraf 6060),
                                a nie 'Zakup materiałów i wyposażenia' (Paragraf 4210).</p>
                            <p className="mt-sm text-info">🔧 Automatycznie skorygowano kod paragrafu.</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
