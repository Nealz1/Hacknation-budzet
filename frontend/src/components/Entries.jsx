import { useState, useEffect } from 'react';
import api from '../services/api';

export default function Entries({ setActivePage }) {
    const [entries, setEntries] = useState([]);
    const [loading, setLoading] = useState(true);
    const [filters, setFilters] = useState({
        status: '',
        priority: '',
        department_code: ''
    });
    const [departments, setDepartments] = useState([]);
    const [selectedEntry, setSelectedEntry] = useState(null);
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [newEntryData, setNewEntryData] = useState({
        department_id: '',
        nazwa_zadania: '',
        opis_projektu: '',
        kwota_2025: 0,
        paragraf: 6060,
        priority: 'medium',
        is_obligatory: false
    });

    useEffect(() => {
        loadEntries();
        loadDepartments();
    }, [filters]);

    const loadEntries = async () => {
        setLoading(true);
        try {
            const data = await api.getEntries(filters);
            setEntries(data);
        } catch (error) {
            console.error('Failed to load entries:', error);
        }
        setLoading(false);
    };

    const loadDepartments = async () => {
        try {
            const data = await api.getDepartments();
            setDepartments(data);
        } catch (error) {
            console.error('Failed to load departments:', error);
        }
    };

    const handleApprove = async (id) => {
        try {
            await api.approveEntry(id);
            loadEntries();
        } catch (error) {
            alert('Failed to approve: ' + error.message);
        }
    };

    const handleReject = async (id) => {
        const reason = prompt('Podaj powód odrzucenia:');
        if (!reason) return;
        try {
            await api.rejectEntry(id, reason);
            loadEntries();
        } catch (error) {
            alert('Failed to reject: ' + error.message);
        }
    };

    const handleValidate = async (id) => {
        try {
            const result = await api.validateEntry(id);
            alert(JSON.stringify(result.data?.warnings || [], null, 2) || 'Brak ostrzeżeń');
            loadEntries();
        } catch (error) {
            alert('Validation failed: ' + error.message);
        }
    };

    const formatCurrency = (value) => {
        if (!value && value !== 0) return '-';
        return new Intl.NumberFormat('pl-PL').format(value) + ' tys.';
    };

    const handleCreateSubmit = async (e) => {
        e.preventDefault();
        try {
            await api.createEntry(newEntryData);
            setShowCreateModal(false);
            loadEntries();
            setNewEntryData({
                department_id: '',
                nazwa_zadania: '',
                opis_projektu: '',
                kwota_2025: 0,
                paragraf: 6060,
                priority: 'medium',
                is_obligatory: false
            });
        } catch (error) {
            alert('Failed to create entry: ' + error.message);
        }
    };

    return (
        <div className="animate-fade-in">
            <div className="flex justify-between items-center mb-xl">
                <div>
                    <h1 style={{ fontSize: '1.75rem', marginBottom: '0.25rem' }}>
                        📋 Pozycje Budżetowe
                    </h1>
                    <p className="text-secondary">
                        Zarządzanie wszystkimi pozycjami budżetu
                    </p>
                </div>
                <div className="flex gap-md">
                    <button
                        className="btn btn-primary"
                        onClick={() => setShowCreateModal(true)}
                    >
                        ➕ Nowa Pozycja
                    </button>
                    <button
                        className="btn btn-secondary"
                        onClick={() => setActivePage('compliance')}
                    >
                        ✅ Waliduj wszystkie
                    </button>
                </div>
            </div>

            { }
            <div className="card mb-lg">
                <div className="flex gap-md flex-wrap items-center">
                    <div className="form-group" style={{ marginBottom: 0, flex: '1 1 200px' }}>
                        <label className="form-label">Status</label>
                        <select
                            className="form-input form-select"
                            value={filters.status}
                            onChange={(e) => setFilters({ ...filters, status: e.target.value })}
                        >
                            <option value="">Wszystkie</option>
                            <option value="draft">Wersja robocza</option>
                            <option value="submitted">Wysłane</option>
                            <option value="approved">Zatwierdzone</option>
                            <option value="rejected">Odrzucone</option>
                        </select>
                    </div>

                    <div className="form-group" style={{ marginBottom: 0, flex: '1 1 200px' }}>
                        <label className="form-label">Priorytet</label>
                        <select
                            className="form-input form-select"
                            value={filters.priority}
                            onChange={(e) => setFilters({ ...filters, priority: e.target.value })}
                        >
                            <option value="">Wszystkie</option>
                            <option value="obligatory">🔒 Obligatoryjne</option>
                            <option value="high">🔴 Wysokie</option>
                            <option value="medium">🟡 Średnie</option>
                            <option value="low">🟢 Niskie</option>
                            <option value="discretionary">⚪ Dyskrecjonalne</option>
                        </select>
                    </div>

                    <div className="form-group" style={{ marginBottom: 0, flex: '1 1 200px' }}>
                        <label className="form-label">Departament</label>
                        <select
                            className="form-input form-select"
                            value={filters.department_code}
                            onChange={(e) => setFilters({ ...filters, department_code: e.target.value })}
                        >
                            <option value="">Wszystkie</option>
                            {departments.map((dept) => (
                                <option key={dept.code} value={dept.code}>{dept.code} - {dept.name}</option>
                            ))}
                        </select>
                    </div>

                    <button
                        className="btn btn-secondary"
                        style={{ alignSelf: 'flex-end' }}
                        onClick={() => setFilters({ status: '', priority: '', department_code: '' })}
                    >
                        🔄 Reset
                    </button>
                </div>
            </div>

            { }
            {loading ? (
                <div className="loading-overlay" style={{ position: 'relative', minHeight: '300px' }}>
                    <div className="loading-spinner"></div>
                </div>
            ) : (
                <div className="card">
                    <div className="table-container" style={{ maxHeight: '600px', overflowY: 'auto' }}>
                        <table className="data-table">
                            <thead>
                                <tr>
                                    <th>ID</th>
                                    <th>Nazwa</th>
                                    <th>Paragraf</th>
                                    <th>2025</th>
                                    <th>2026</th>
                                    <th>2027</th>
                                    <th>Łącznie</th>
                                    <th>Priorytet</th>
                                    <th>Status</th>
                                    <th>Zgodność</th>
                                    <th>Akcje</th>
                                </tr>
                            </thead>
                            <tbody>
                                {entries.length === 0 ? (
                                    <tr>
                                        <td colSpan="11" style={{ textAlign: 'center', padding: '2rem' }}>
                                            <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>📭</div>
                                            <p className="text-secondary">Brak pozycji spełniających kryteria</p>
                                            <button className="btn btn-primary mt-md" onClick={() => api.loadDemoData().then(loadEntries)}>
                                                📥 Załaduj dane demo
                                            </button>
                                        </td>
                                    </tr>
                                ) : (
                                    entries.map((entry) => (
                                        <tr key={entry.id}>
                                            <td className="font-mono">{entry.id}</td>
                                            <td
                                                className="truncate"
                                                style={{ maxWidth: '250px', cursor: 'pointer' }}
                                                onClick={() => setSelectedEntry(entry)}
                                                title={entry.nazwa_zadania || entry.opis_projektu}
                                            >
                                                {entry.nazwa_zadania || entry.opis_projektu || 'Brak nazwy'}
                                            </td>
                                            <td className="font-mono">{entry.paragraf || '-'}</td>
                                            <td>{formatCurrency(entry.kwota_2025)}</td>
                                            <td>{formatCurrency(entry.kwota_2026)}</td>
                                            <td>{formatCurrency(entry.kwota_2027)}</td>
                                            <td className="font-bold">{formatCurrency(entry.total_amount)}</td>
                                            <td>
                                                <span className={`badge badge-${entry.priority === 'obligatory' ? 'danger' :
                                                    entry.priority === 'high' ? 'warning' :
                                                        entry.priority === 'medium' ? 'info' : 'primary'
                                                    }`}>
                                                    {entry.is_obligatory && '🔒 '}{entry.priority}
                                                </span>
                                            </td>
                                            <td>
                                                <span className={`badge badge-${entry.status === 'approved' ? 'success' :
                                                    entry.status === 'rejected' ? 'danger' :
                                                        entry.status === 'submitted' ? 'info' : 'warning'
                                                    }`}>
                                                    {entry.status}
                                                </span>
                                            </td>
                                            <td>
                                                {entry.compliance_validated ? (
                                                    entry.compliance_warnings && entry.compliance_warnings !== '[]' ? (
                                                        <span className="badge badge-warning">⚠️</span>
                                                    ) : (
                                                        <span className="badge badge-success">✅</span>
                                                    )
                                                ) : (
                                                    <span className="badge badge-primary">-</span>
                                                )}
                                            </td>
                                            <td>
                                                <div className="flex gap-sm">
                                                    <button
                                                        className="btn btn-sm btn-secondary"
                                                        onClick={() => handleValidate(entry.id)}
                                                        title="Waliduj"
                                                    >
                                                        🔍
                                                    </button>
                                                    {entry.status !== 'approved' && (
                                                        <button
                                                            className="btn btn-sm btn-success"
                                                            onClick={() => handleApprove(entry.id)}
                                                            title="Zatwierdź"
                                                        >
                                                            ✓
                                                        </button>
                                                    )}
                                                    {entry.status !== 'rejected' && (
                                                        <button
                                                            className="btn btn-sm btn-danger"
                                                            onClick={() => handleReject(entry.id)}
                                                            title="Odrzuć"
                                                        >
                                                            ✕
                                                        </button>
                                                    )}
                                                </div>
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>

                    <div className="flex justify-between items-center mt-md p-md" style={{ background: 'var(--bg-darker)', borderRadius: 'var(--radius-md)' }}>
                        <span className="text-secondary">
                            Pokazano {entries.length} pozycji
                        </span>
                        <span className="text-secondary">
                            Łączna wartość 2025: <strong className="text-primary">
                                {formatCurrency(entries.reduce((sum, e) => sum + (e.kwota_2025 || 0), 0))} PLN
                            </strong>
                        </span>
                    </div>
                </div>
            )}

            { }
            {selectedEntry && (
                <div className="modal-overlay" onClick={() => setSelectedEntry(null)}>
                    <div className="modal" onClick={(e) => e.stopPropagation()}>
                        <div className="modal-header">
                            <h3>Szczegóły Pozycji #{selectedEntry.id}</h3>
                            <button className="modal-close" onClick={() => setSelectedEntry(null)}>×</button>
                        </div>
                        <div className="modal-body">
                            <div className="form-group">
                                <label className="form-label">Nazwa Zadania</label>
                                <div className="p-md" style={{ background: 'var(--bg-darker)', borderRadius: 'var(--radius-sm)' }}>
                                    {selectedEntry.nazwa_zadania || 'Brak'}
                                </div>
                            </div>

                            <div className="form-group">
                                <label className="form-label">Opis Projektu</label>
                                <div className="p-md" style={{ background: 'var(--bg-darker)', borderRadius: 'var(--radius-sm)' }}>
                                    {selectedEntry.opis_projektu || 'Brak'}
                                </div>
                            </div>

                            <div className="form-group">
                                <label className="form-label">Szczegółowe Uzasadnienie</label>
                                <div className="p-md" style={{ background: 'var(--bg-darker)', borderRadius: 'var(--radius-sm)' }}>
                                    {selectedEntry.szczegolowe_uzasadnienie || 'Brak'}
                                </div>
                            </div>

                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem' }}>
                                <div className="form-group">
                                    <label className="form-label">Paragraf</label>
                                    <div className="font-mono font-bold">{selectedEntry.paragraf || '-'}</div>
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Źródło Fin.</label>
                                    <div className="font-mono">{selectedEntry.zrodlo_finansowania || '-'}</div>
                                </div>
                                <div className="form-group">
                                    <label className="form-label">BZ</label>
                                    <div className="font-mono">{selectedEntry.beneficjent_zadaniowy || '-'}</div>
                                </div>
                            </div>

                            {selectedEntry.compliance_warnings && selectedEntry.compliance_warnings !== '[]' && (
                                <div className="alert alert-warning">
                                    <span className="alert-icon">⚠️</span>
                                    <div>
                                        <strong>Ostrzeżenia Zgodności</strong>
                                        <pre style={{ fontSize: '0.8rem', whiteSpace: 'pre-wrap' }}>
                                            {selectedEntry.compliance_warnings}
                                        </pre>
                                    </div>
                                </div>
                            )}
                        </div>
                        <div className="modal-footer">
                            <button className="btn btn-secondary" onClick={() => setSelectedEntry(null)}>
                                Zamknij
                            </button>
                        </div>
                    </div>
                </div>
            )}
            {showCreateModal && (
                <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
                    <div className="modal" onClick={(e) => e.stopPropagation()}>
                        <div className="modal-header">
                            <h3>➕ Nowa Pozycja Budżetowa</h3>
                            <button className="modal-close" onClick={() => setShowCreateModal(false)}>×</button>
                        </div>
                        <form onSubmit={handleCreateSubmit}>
                            <div className="modal-body">
                                <div className="form-group">
                                    <label className="form-label">Departament *</label>
                                    <select
                                        className="form-input form-select"
                                        required
                                        value={newEntryData.department_id}
                                        onChange={e => setNewEntryData({ ...newEntryData, department_id: Number(e.target.value) })}
                                    >
                                        <option value="">Wybierz...</option>
                                        {departments.map(d => (
                                            <option key={d.id} value={d.id}>{d.code} - {d.name}</option>
                                        ))}
                                    </select>
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Nazwa Zadania *</label>
                                    <input
                                        className="form-input"
                                        required
                                        value={newEntryData.nazwa_zadania}
                                        onChange={e => setNewEntryData({ ...newEntryData, nazwa_zadania: e.target.value })}
                                        placeholder="np. Zakup licencji"
                                    />
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Opis Projektu</label>
                                    <textarea
                                        className="form-input"
                                        rows="3"
                                        value={newEntryData.opis_projektu}
                                        onChange={e => setNewEntryData({ ...newEntryData, opis_projektu: e.target.value })}
                                    ></textarea>
                                </div>
                                <div className="grid grid-cols-2 gap-md">
                                    <div className="form-group">
                                        <label className="form-label">Kwota 2025 (PLN) *</label>
                                        <input
                                            type="number"
                                            className="form-input"
                                            required
                                            min="0"
                                            value={newEntryData.kwota_2025}
                                            onChange={e => setNewEntryData({ ...newEntryData, kwota_2025: Number(e.target.value) })}
                                        />
                                    </div>
                                    <div className="form-group">
                                        <label className="form-label">Paragraf</label>
                                        <input
                                            type="number"
                                            className="form-input"
                                            value={newEntryData.paragraf}
                                            onChange={e => setNewEntryData({ ...newEntryData, paragraf: Number(e.target.value) })}
                                        />
                                    </div>
                                </div>
                                <div className="grid grid-cols-2 gap-md">
                                    <div className="form-group">
                                        <label className="form-label">Priorytet</label>
                                        <select
                                            className="form-input form-select"
                                            value={newEntryData.priority}
                                            onChange={e => setNewEntryData({ ...newEntryData, priority: e.target.value })}
                                        >
                                            <option value="medium">Medium</option>
                                            <option value="high">High</option>
                                            <option value="low">Low</option>
                                            <option value="obligatory">Obligatory</option>
                                            <option value="discretionary">Discretionary</option>
                                        </select>
                                    </div>
                                    <div className="form-group flex items-center pt-lg">
                                        <label className="flex items-center gap-sm cursor-pointer">
                                            <input
                                                type="checkbox"
                                                checked={newEntryData.is_obligatory}
                                                onChange={e => setNewEntryData({ ...newEntryData, is_obligatory: e.target.checked })}
                                            />
                                            <span>Wymagane prawnie?</span>
                                        </label>
                                    </div>
                                </div>
                            </div>
                            <div className="modal-footer">
                                <button type="button" className="btn btn-secondary" onClick={() => setShowCreateModal(false)}>
                                    Anuluj
                                </button>
                                <button type="submit" className="btn btn-primary">
                                    Utwórz Pozycję
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )
            }
        </div >
    );
}
