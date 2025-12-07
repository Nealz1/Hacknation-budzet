import { useState, useEffect } from 'react';
import api from '../services/api';

const downloadFile = (url, fallbackFilename) => {
    const iframe = document.createElement('iframe');
    iframe.style.display = 'none';
    iframe.src = url;
    document.body.appendChild(iframe);

    setTimeout(() => {
        document.body.removeChild(iframe);
    }, 5000);
};

export default function Documents() {
    const [departments, setDepartments] = useState([]);
    const [selectedDept, setSelectedDept] = useState('');
    const [loading, setLoading] = useState(false);
    const [generatedDoc, setGeneratedDoc] = useState(null);
    const [docType, setDocType] = useState('limit-letter');
    const [summaryReport, setSummaryReport] = useState(null);

    useEffect(() => {
        loadDepartments();
    }, []);

    const loadDepartments = async () => {
        try {
            const data = await api.getDepartments();
            setDepartments(data);
        } catch (error) {
            console.error('Failed to load departments:', error);
        }
    };

    const handleGenerateDocument = async () => {
        if (!selectedDept && docType !== 'summary-report') {
            alert('Wybierz departament');
            return;
        }

        setLoading(true);
        setGeneratedDoc(null);

        try {
            let response;

            if (docType === 'limit-letter') {
                response = await fetch(`http://localhost:8000/api/documents/limit-letter/${selectedDept}?year=2025`);
            } else if (docType === 'cut-notification') {
                response = await fetch(`http://localhost:8000/api/documents/cut-notification/${selectedDept}?year=2025`, {
                    method: 'POST'
                });
            } else if (docType === 'summary-report') {
                response = await fetch(`http://localhost:8000/api/documents/summary-report?year=2025`);
            }

            const data = await response.json();
            setGeneratedDoc(data.data);
        } catch (error) {
            alert('Błąd generowania dokumentu: ' + error.message);
        }

        setLoading(false);
    };

    const formatCurrency = (value) => {
        if (!value && value !== 0) return '-';
        return new Intl.NumberFormat('pl-PL').format(value) + ' tys. PLN';
    };

    const renderDocument = () => {
        if (!generatedDoc) return null;

        if (docType === 'summary-report') {
            return renderSummaryReport();
        }

        return (
            <div className="document-preview animate-fade-in">
                {}
                <div className="document-header">
                    <div className="document-sender">
                        <pre style={{ margin: 0, fontFamily: 'inherit' }}>
                            {generatedDoc.header?.sender}
                        </pre>
                    </div>
                    <div className="document-meta">
                        <div><strong>Data:</strong> {generatedDoc.header?.date}</div>
                        <div><strong>Nr ref:</strong> {generatedDoc.header?.reference}</div>
                    </div>
                </div>

                {}
                <div className="document-recipient">
                    <pre style={{ margin: 0, fontFamily: 'inherit' }}>
                        {generatedDoc.header?.recipient}
                    </pre>
                </div>

                {}
                <h2 className="document-title">{generatedDoc.content?.title}</h2>

                {}
                <div className="document-body">
                    <p><em>{generatedDoc.content?.opening}</em></p>
                    <div
                        className="document-content"
                        dangerouslySetInnerHTML={{
                            __html: (generatedDoc.content?.body || '')
                                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                                .replace(/\n\n/g, '</p><p>')
                        }}
                    />
                </div>

                {}
                <div className="document-closing">
                    <p>{generatedDoc.content?.closing}</p>
                    <p><strong>{generatedDoc.content?.signature}</strong></p>
                </div>

                {}
                {generatedDoc.attachments?.budget_table?.length > 0 && (
                    <div className="document-attachment">
                        <h4>Załącznik: Tabela budżetowa</h4>
                        <div className="table-container" style={{ maxHeight: '300px', overflowY: 'auto' }}>
                            <table className="data-table">
                                <thead>
                                    <tr>
                                        <th>Lp.</th>
                                        <th>Nazwa zadania</th>
                                        <th>Paragraf</th>
                                        <th>Kwota</th>
                                        <th>Priorytet</th>
                                        <th>Oblig.</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {generatedDoc.attachments.budget_table.slice(0, 15).map((row) => (
                                        <tr key={row.lp}>
                                            <td>{row.lp}</td>
                                            <td className="truncate" style={{ maxWidth: '200px' }}>{row.nazwa_zadania}</td>
                                            <td className="font-mono">{row.paragraf}</td>
                                            <td>{formatCurrency(row.kwota)}</td>
                                            <td>
                                                <span className={`badge badge-${row.priorytet === 'obligatory' ? 'danger' :
                                                    row.priorytet === 'high' ? 'warning' : 'primary'
                                                    }`}>
                                                    {row.priorytet}
                                                </span>
                                            </td>
                                            <td>
                                                <span className={row.obligatoryjne === 'TAK' ? 'text-danger' : ''}>
                                                    {row.obligatoryjne}
                                                </span>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}

                {}
                {generatedDoc.data && (
                    <div className="document-summary">
                        <h4>Podsumowanie</h4>
                        <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
                            <div className="stat-card">
                                <div className="stat-value">{formatCurrency(generatedDoc.data.assigned_limit)}</div>
                                <div className="stat-label">Przyznany limit</div>
                            </div>
                            <div className="stat-card">
                                <div className="stat-value">{formatCurrency(generatedDoc.data.current_requests)}</div>
                                <div className="stat-label">Zapotrzebowanie</div>
                            </div>
                            <div className={`stat-card ${generatedDoc.data.is_over_limit ? 'warning' : 'success'}`}>
                                <div className={`stat-value ${generatedDoc.data.variance > 0 ? 'negative' : 'positive'}`}>
                                    {generatedDoc.data.variance > 0 ? '+' : ''}{formatCurrency(generatedDoc.data.variance)}
                                </div>
                                <div className="stat-label">{generatedDoc.data.is_over_limit ? 'Przekroczenie' : 'Rezerwa'}</div>
                            </div>
                        </div>
                    </div>
                )}

                {}
                <div className="flex justify-between mt-lg">
                    <div className="flex gap-sm">
                        <button className="btn btn-secondary" onClick={() => window.print()}>
                            🖨️ Drukuj
                        </button>
                        <button className="btn btn-secondary" onClick={() => {
                            const blob = new Blob([JSON.stringify(generatedDoc, null, 2)], { type: 'application/json' });
                            const url = URL.createObjectURL(blob);
                            const a = document.createElement('a');
                            a.href = url;
                            a.download = `${docType}_${selectedDept}_2025.json`;
                            a.click();
                        }}>
                            📥 Pobierz JSON
                        </button>
                    </div>
                    <div className="flex gap-sm">
                        {docType === 'limit-letter' && selectedDept && (
                            <button
                                className="btn btn-primary"
                                onClick={() => downloadFile(
                                    `http://localhost:8000/api/export/word/limit-letter/${selectedDept}?year=2025`,
                                    `pismo_limit_${selectedDept}_2025.docx`
                                )}
                            >
                                📝 Pobierz Word (.docx)
                            </button>
                        )}
                        {docType === 'summary-report' && (
                            <button
                                className="btn btn-primary"
                                onClick={() => downloadFile(
                                    'http://localhost:8000/api/export/word/summary-report?year=2025',
                                    'raport_budzet_2025.docx'
                                )}
                            >
                                📝 Pobierz Word (.docx)
                            </button>
                        )}
                        <button
                            className="btn btn-success"
                            onClick={() => downloadFile(
                                'http://localhost:8000/api/export/excel?year=2025',
                                'budzet_2025.xlsx'
                            )}
                        >
                            📊 Eksport Excel (.xlsx)
                        </button>
                    </div>
                </div>
            </div>
        );
    };

    const renderSummaryReport = () => {
        const report = generatedDoc;
        if (!report) return null;

        return (
            <div className="document-preview animate-fade-in">
                <h2 className="document-title">{report.executive_summary?.title}</h2>

                {}
                <div className="stats-grid mb-lg">
                    <div className="stat-card">
                        <div className="stat-value">{formatCurrency(report.executive_summary?.global_limit)}</div>
                        <div className="stat-label">Limit Globalny</div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-value">{formatCurrency(report.executive_summary?.total_requests)}</div>
                        <div className="stat-label">Zapotrzebowanie</div>
                    </div>
                    <div className={`stat-card ${report.executive_summary?.is_over_limit ? 'warning' : 'success'}`}>
                        <div className={`stat-value ${report.executive_summary?.variance > 0 ? 'negative' : 'positive'}`}>
                            {report.executive_summary?.variance > 0 ? '+' : ''}{formatCurrency(report.executive_summary?.variance)}
                        </div>
                        <div className="stat-label">{report.executive_summary?.is_over_limit ? 'Przekroczenie' : 'Rezerwa'}</div>
                    </div>
                </div>

                {}
                <div className="card mb-lg">
                    <div className="card-header">
                        <h3 className="card-title">
                            <span className="card-title-icon">🏢</span>
                            Podział na departamenty
                        </h3>
                    </div>
                    <div className="table-container">
                        <table className="data-table">
                            <thead>
                                <tr>
                                    <th>Status</th>
                                    <th>Kod</th>
                                    <th>Nazwa</th>
                                    <th>Limit</th>
                                    <th>Zapotrzebowanie</th>
                                    <th>Różnica</th>
                                    <th>Pozycji</th>
                                </tr>
                            </thead>
                            <tbody>
                                {report.department_breakdown?.map((dept) => (
                                    <tr key={dept.code}>
                                        <td>{dept.status}</td>
                                        <td className="font-mono">{dept.code}</td>
                                        <td>{dept.name}</td>
                                        <td>{formatCurrency(dept.limit)}</td>
                                        <td>{formatCurrency(dept.requested)}</td>
                                        <td className={dept.variance > 0 ? 'text-danger' : 'text-success'}>
                                            {dept.variance > 0 ? '+' : ''}{formatCurrency(dept.variance)}
                                        </td>
                                        <td>{dept.entry_count}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>

                {}
                <div className="card mb-lg">
                    <div className="card-header">
                        <h3 className="card-title">
                            <span className="card-title-icon">📊</span>
                            Podział wg priorytetów
                        </h3>
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '1rem' }}>
                        {Object.entries(report.priority_breakdown || {}).map(([priority, amount]) => (
                            <div key={priority} className="p-md" style={{ background: 'var(--bg-darker)', borderRadius: 'var(--radius-md)' }}>
                                <div className="text-secondary" style={{ fontSize: '0.75rem', textTransform: 'capitalize' }}>
                                    {priority === 'obligatory' ? '🔒' :
                                        priority === 'high' ? '🔴' :
                                            priority === 'medium' ? '🟡' :
                                                priority === 'low' ? '🟢' : '⚪'} {priority}
                                </div>
                                <div className="font-bold">{formatCurrency(amount)}</div>
                            </div>
                        ))}
                    </div>
                </div>

                {}
                {report.recommendations?.length > 0 && (
                    <div className="agent-card">
                        <div className="agent-header">
                            <div className="agent-avatar">🤖</div>
                            <div>
                                <div className="agent-name">Rekomendacje AI</div>
                                <div className="agent-action">Analiza automatyczna</div>
                            </div>
                        </div>
                        <div className="agent-body">
                            {report.recommendations.map((rec, i) => (
                                <div key={i} className="alert alert-info mb-sm">
                                    {rec}
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        );
    };

    return (
        <div className="animate-fade-in">
            <div className="flex justify-between items-center mb-xl">
                <div>
                    <h1 style={{ fontSize: '1.75rem', marginBottom: '0.25rem' }}>
                        📄 Bureaucrat Agent
                    </h1>
                    <p className="text-secondary">
                        Automatyczne generowanie oficjalnej korespondencji urzędowej
                    </p>
                </div>
            </div>

            {}
            <div className="card mb-xl">
                <div className="card-header">
                    <h3 className="card-title">
                        <span className="card-title-icon">⚙️</span>
                        Generator Dokumentów
                    </h3>
                </div>
                <div className="p-lg">
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
                        <div className="form-group">
                            <label className="form-label">Typ dokumentu</label>
                            <select
                                className="form-input form-select"
                                value={docType}
                                onChange={(e) => setDocType(e.target.value)}
                            >
                                <option value="limit-letter">📋 Pismo o limitach</option>
                                <option value="cut-notification">✂️ Zawiadomienie o cięciach</option>
                                <option value="summary-report">📊 Raport zbiorczy</option>
                            </select>
                        </div>

                        {docType !== 'summary-report' && (
                            <div className="form-group">
                                <label className="form-label">Departament</label>
                                <select
                                    className="form-input form-select"
                                    value={selectedDept}
                                    onChange={(e) => setSelectedDept(e.target.value)}
                                >
                                    <option value="">Wybierz departament...</option>
                                    {departments.map((dept) => (
                                        <option key={dept.code} value={dept.code}>
                                            {dept.code} - {dept.name}
                                        </option>
                                    ))}
                                </select>
                            </div>
                        )}

                        <div className="form-group" style={{ alignSelf: 'flex-end' }}>
                            <button
                                className="btn btn-primary btn-lg"
                                onClick={handleGenerateDocument}
                                disabled={loading}
                                style={{ width: '100%' }}
                            >
                                {loading ? '⏳ Generowanie...' : '🔮 Generuj Dokument'}
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            {}
            {!generatedDoc && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }} className="mb-xl">
                    <div className="card">
                        <div className="flex items-center gap-md mb-md">
                            <div className="stat-icon primary">📋</div>
                            <div>
                                <h4>Pismo o Limitach</h4>
                                <p className="text-secondary" style={{ fontSize: '0.875rem' }}>
                                    Formalne zawiadomienie dla Dyrektora departamentu o przyznanym limicie finansowym
                                </p>
                            </div>
                        </div>
                    </div>

                    <div className="card">
                        <div className="flex items-center gap-md mb-md">
                            <div className="stat-icon warning">✂️</div>
                            <div>
                                <h4>Zawiadomienie o Cięciach</h4>
                                <p className="text-secondary" style={{ fontSize: '0.875rem' }}>
                                    Oficjalna informacja o wymaganych redukcjach budżetowych dla departamentu
                                </p>
                            </div>
                        </div>
                    </div>

                    <div className="card">
                        <div className="flex items-center gap-md mb-md">
                            <div className="stat-icon success">📊</div>
                            <div>
                                <h4>Raport Zbiorczy</h4>
                                <p className="text-secondary" style={{ fontSize: '0.875rem' }}>
                                    Kompleksowa informacja dla Kierownictwa o stanie budżetu
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {}
            {generatedDoc && renderDocument()}

            {}
            <div className="card">
                <div className="card-header">
                    <h3 className="card-title">
                        <span className="card-title-icon">💡</span>
                        Jak działa Bureaucrat Agent?
                    </h3>
                </div>
                <div className="agent-body">
                    <div className="alert alert-info mb-md">
                        <span className="alert-icon">🤖</span>
                        <div>
                            <strong>Reverse-Templating z LLM</strong>
                            <p>Zamiast prostego mail-merge, Agent generuje narratywną treść dokumentu,
                                synchronizując ją z aktualnymi danymi z bazy. Eliminuje to ryzyko rozbieżności
                                między "liczbami w Excelu" a "tekstem w piśmie".</p>
                        </div>
                    </div>

                    <ul style={{ listStyle: 'none', padding: 0 }}>
                        <li className="mb-sm">✅ <strong>Automatyczne numery referencyjne</strong> - format BBF-ROK/DEPT/MIESIĄC</li>
                        <li className="mb-sm">✅ <strong>Aktualne dane finansowe</strong> - pobierane w momencie generowania</li>
                        <li className="mb-sm">✅ <strong>Identyfikacja zadań obligatoryjnych</strong> - automatyczne wyliczanie</li>
                        <li className="mb-sm">✅ <strong>Rekomendacje AI</strong> - inteligentna analiza i sugestie</li>
                    </ul>
                </div>
            </div>

            <style>{`
        .document-preview {
          background: white;
          color: #333;
          padding: 2rem;
          border-radius: var(--radius-md);
          box-shadow: var(--shadow-lg);
        }
        
        .document-header {
          display: flex;
          justify-content: space-between;
          margin-bottom: 2rem;
          padding-bottom: 1rem;
          border-bottom: 1px solid #ddd;
        }
        
        .document-sender {
          font-size: 0.9rem;
        }
        
        .document-meta {
          text-align: right;
          font-size: 0.85rem;
        }
        
        .document-recipient {
          margin: 1.5rem 0;
          font-size: 0.9rem;
        }
        
        .document-title {
          text-align: center;
          margin: 2rem 0;
          font-size: 1.25rem;
          text-transform: uppercase;
          letter-spacing: 1px;
        }
        
        .document-body {
          line-height: 1.8;
          font-size: 0.95rem;
        }
        
        .document-body p {
          margin-bottom: 1rem;
        }
        
        .document-closing {
          margin-top: 2rem;
          text-align: right;
        }
        
        .document-attachment {
          margin-top: 2rem;
          padding-top: 1rem;
          border-top: 1px solid #ddd;
        }
        
        .document-summary {
          margin-top: 2rem;
          padding: 1rem;
          background: var(--bg-darker);
          border-radius: var(--radius-md);
        }
        
        @media print {
          .document-preview {
            box-shadow: none;
          }
          .btn, .card-header, nav, aside {
            display: none !important;
          }
        }
      `}</style>
        </div>
    );
}
