import { useState, useEffect } from 'react';
import api from '../services/api';

export default function Departments() {
    const [departments, setDepartments] = useState([]);
    const [selectedDept, setSelectedDept] = useState(null);
    const [deptData, setDeptData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [editingEntry, setEditingEntry] = useState(null);
    const [editValues, setEditValues] = useState({});
    const [canEdit, setCanEdit] = useState({ can_edit: true, reason: '' });
    const [submitResult, setSubmitResult] = useState(null);

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

    const loadDepartmentData = async (code) => {
        setLoading(true);
        setSelectedDept(code);
        setSubmitResult(null);
        try {
            const data = await api.getDepartmentEntries(code);
            setDeptData(data);

            const editCheck = await fetch(`http://localhost:8000/api/departments/${code}/can-edit`);
            const editData = await editCheck.json();
            setCanEdit(editData);
        } catch (error) {
            console.error('Failed to load department data:', error);
        }
        setLoading(false);
    };

    const handleEditEntry = (entry) => {
        if (!canEdit.can_edit) {
            alert(canEdit.reason);
            return;
        }
        setEditingEntry(entry.id);
        setEditValues({
            kwota_2025: entry.kwota_2025,
            kwota_2026: entry.kwota_2026,
            kwota_2027: entry.kwota_2027,
            priority: entry.priority,
            uwagi: entry.uwagi || '',
        });
    };

    const handleSaveEntry = async (entryId) => {
        try {
            await api.updateEntry(entryId, editValues);
            loadDepartmentData(selectedDept);
            setEditingEntry(null);
        } catch (error) {
            alert('Failed to save: ' + error.message);
        }
    };

    const handleSubmitEntry = async (entryId) => {
        try {
            const response = await fetch(`http://localhost:8000/api/entries/${entryId}/submit`, {
                method: 'POST'
            });
            const data = await response.json();

            if (!response.ok) {
                const detail = data.detail;
                if (typeof detail === 'object') {
                    alert(`❌ ${detail.message}\n\nBłędy:\n${detail.errors?.join('\n') || ''}`);
                } else {
                    alert(`❌ ${detail}`);
                }
                return;
            }

            loadDepartmentData(selectedDept);
        } catch (error) {
            alert('Failed to submit: ' + error.message);
        }
    };

    const handleSubmitAll = async () => {
        try {
            const response = await fetch(`http://localhost:8000/api/entries/submit-all?department_code=${selectedDept}`, {
                method: 'POST'
            });
            const data = await response.json();

            if (!response.ok) {
                alert(`❌ ${data.detail}`);
                return;
            }

            setSubmitResult(data);
            loadDepartmentData(selectedDept);
        } catch (error) {
            alert('Failed to submit all: ' + error.message);
        }
    };

    const formatCurrency = (value) => {
        if (!value && value !== 0) return '-';
        return new Intl.NumberFormat('pl-PL').format(value);
    };

    const validateAmount = (value, limit) => {
        const numValue = parseFloat(value) || 0;
        const total = deptData?.entries?.reduce((sum, e) => {
            if (e.id === editingEntry) return sum;
            return sum + (e.kwota_2025 || 0);
        }, 0) || 0;

        return (total + numValue) <= (limit || Infinity);
    };

    return (
        <div className="animate-fade-in">
            <div className="mb-xl">
                <h1 style={{ fontSize: '1.75rem', marginBottom: '0.25rem' }}>
                    🏢 Widok Departamentów
                </h1>
                <p className="text-secondary">
                    Generative UI - Dynamicznie generowane formularze dla Dyrektorów
                </p>
            </div>

            {}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '1rem' }} className="mb-xl">
                {departments.map((dept) => (
                    <div
                        key={dept.code}
                        className={`card ${selectedDept === dept.code ? 'active' : ''}`}
                        style={{
                            cursor: 'pointer',
                            borderColor: selectedDept === dept.code ? 'var(--primary-500)' : 'var(--border-color)',
                            boxShadow: selectedDept === dept.code ? 'var(--shadow-glow)' : 'none'
                        }}
                        onClick={() => loadDepartmentData(dept.code)}
                    >
                        <div className="flex items-center gap-md">
                            <div className="stat-icon primary" style={{ width: '36px', height: '36px', fontSize: '1rem' }}>
                                🏛️
                            </div>
                            <div>
                                <div className="font-semibold">{dept.code}</div>
                                <div className="text-secondary" style={{ fontSize: '0.75rem' }}>
                                    {dept.name?.substring(0, 25) || 'Departament'}
                                </div>
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {}
            {loading && (
                <div className="loading-overlay" style={{ position: 'relative', minHeight: '300px' }}>
                    <div className="loading-spinner"></div>
                </div>
            )}

            {deptData && !loading && (
                <div className="animate-slide-in">
                    {}
                    <div className="card mb-lg">
                        <div className="flex justify-between items-center">
                            <div>
                                <h2>{deptData.department?.code} - {deptData.department?.name}</h2>
                                <p className="text-secondary">Rok budżetowy: {deptData.year}</p>
                            </div>
                            <div className="text-right">
                                <div className="text-secondary" style={{ fontSize: '0.8rem' }}>Limit Departamentu</div>
                                <div className="font-bold" style={{ fontSize: '1.5rem' }}>
                                    {formatCurrency(deptData.department?.budget_limit)} tys. PLN
                                </div>
                            </div>
                        </div>

                        {}
                        <div className="progress-container mt-lg">
                            <div className="progress-header">
                                <span>Wykorzystanie limitu</span>
                                <span className={deptData.department?.is_over_limit ? 'text-danger' : 'text-success'}>
                                    {formatCurrency(deptData.department?.total_requested)} / {formatCurrency(deptData.department?.budget_limit)} tys. PLN
                                </span>
                            </div>
                            <div className="progress-bar">
                                <div
                                    className={`progress-fill ${deptData.department?.is_over_limit ? 'danger' :
                                        (deptData.department?.total_requested / deptData.department?.budget_limit) > 0.85 ? 'warning' : 'success'
                                        }`}
                                    style={{
                                        width: `${Math.min(
                                            (deptData.department?.total_requested / (deptData.department?.budget_limit || 1)) * 100,
                                            100
                                        )}%`
                                    }}
                                ></div>
                            </div>
                        </div>

                        {deptData.department?.is_over_limit && (
                            <div className="alert alert-danger mt-md" style={{ marginBottom: 0 }}>
                                <span className="alert-icon">⚠️</span>
                                <div>
                                    <strong>Przekroczenie limitu!</strong>
                                    <p>Zapotrzebowanie przekracza limit o {formatCurrency(deptData.department?.variance)} tys. PLN</p>
                                </div>
                            </div>
                        )}

                        {}
                        {!canEdit.can_edit && (
                            <div className="alert alert-warning mt-md" style={{ marginBottom: 0 }}>
                                <span className="alert-icon">🔒</span>
                                <div>
                                    <strong>Edycja zablokowana</strong>
                                    <p>{canEdit.reason}</p>
                                </div>
                            </div>
                        )}

                        {canEdit.deadline && canEdit.can_edit && (
                            <div className="alert alert-info mt-md" style={{ marginBottom: 0 }}>
                                <span className="alert-icon">⏰</span>
                                <div>
                                    <strong>Termin edycji</strong>
                                    <p>Do: {new Date(canEdit.deadline).toLocaleString('pl-PL')}</p>
                                </div>
                            </div>
                        )}

                        {}
                        <div className="flex justify-between items-center mt-lg">
                            <div className="text-secondary">
                                Pozycji roboczych: {deptData.entries?.filter(e => e.status === 'draft').length || 0}
                            </div>
                            <button
                                className="btn btn-primary"
                                onClick={handleSubmitAll}
                                disabled={!canEdit.can_edit || deptData.entries?.filter(e => e.status === 'draft').length === 0}
                            >
                                📤 Prześlij wszystkie do akceptacji
                            </button>
                        </div>

                        {}
                        {submitResult && (
                            <div className={`alert ${submitResult.failed_count > 0 ? 'alert-warning' : 'alert-success'} mt-md`} style={{ marginBottom: 0 }}>
                                <span className="alert-icon">{submitResult.failed_count > 0 ? '⚠️' : '✅'}</span>
                                <div>
                                    <strong>{submitResult.message}</strong>
                                    {submitResult.failed_count > 0 && (
                                        <div className="mt-sm">
                                            <p>Pozycje z błędami walidacji:</p>
                                            <ul style={{ marginLeft: '1rem', fontSize: '0.85rem' }}>
                                                {submitResult.failed_entries?.slice(0, 5).map((fe, i) => (
                                                    <li key={i}>
                                                        {fe.nazwa?.substring(0, 40)}... - {fe.errors?.length} błędów
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}
                    </div>

                    {}
                    <div className="card">
                        <div className="card-header">
                            <h3 className="card-title">
                                <span className="card-title-icon">📋</span>
                                Pozycje Budżetowe ({deptData.entries?.length || 0})
                            </h3>
                        </div>

                        <div className="table-container" style={{ maxHeight: '500px', overflowY: 'auto' }}>
                            <table className="data-table">
                                <thead>
                                    <tr>
                                        <th>Nazwa Zadania</th>
                                        <th>Paragraf</th>
                                        <th>2025 (tys.)</th>
                                        <th>2026 (tys.)</th>
                                        <th>2027 (tys.)</th>
                                        <th>Priorytet</th>
                                        <th>Status</th>
                                        <th>Akcje</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {deptData.entries?.map((entry) => (
                                        <tr key={entry.id}>
                                            <td className="truncate" style={{ maxWidth: '250px' }}>
                                                {entry.nazwa_zadania || entry.opis_projektu || 'Brak nazwy'}
                                            </td>
                                            <td className="font-mono">{entry.paragraf || '-'}</td>

                                            {}
                                            {editingEntry === entry.id ? (
                                                <>
                                                    <td>
                                                        <input
                                                            type="number"
                                                            className={`form-input ${!validateAmount(editValues.kwota_2025, deptData.department?.budget_limit) ? 'text-danger' : ''}`}
                                                            style={{ width: '100px' }}
                                                            value={editValues.kwota_2025 || ''}
                                                            onChange={(e) => setEditValues({ ...editValues, kwota_2025: parseFloat(e.target.value) || 0 })}
                                                        />
                                                        {!validateAmount(editValues.kwota_2025, deptData.department?.budget_limit) && (
                                                            <div className="text-danger" style={{ fontSize: '0.7rem' }}>⚠️ Przekracza limit!</div>
                                                        )}
                                                    </td>
                                                    <td>
                                                        <input
                                                            type="number"
                                                            className="form-input"
                                                            style={{ width: '100px' }}
                                                            value={editValues.kwota_2026 || ''}
                                                            onChange={(e) => setEditValues({ ...editValues, kwota_2026: parseFloat(e.target.value) || 0 })}
                                                        />
                                                    </td>
                                                    <td>
                                                        <input
                                                            type="number"
                                                            className="form-input"
                                                            style={{ width: '100px' }}
                                                            value={editValues.kwota_2027 || ''}
                                                            onChange={(e) => setEditValues({ ...editValues, kwota_2027: parseFloat(e.target.value) || 0 })}
                                                        />
                                                    </td>
                                                </>
                                            ) : (
                                                <>
                                                    <td>{formatCurrency(entry.kwota_2025)}</td>
                                                    <td>{formatCurrency(entry.kwota_2026)}</td>
                                                    <td>{formatCurrency(entry.kwota_2027)}</td>
                                                </>
                                            )}

                                            <td>
                                                {editingEntry === entry.id ? (
                                                    <select
                                                        className="form-input form-select"
                                                        value={editValues.priority || 'medium'}
                                                        onChange={(e) => setEditValues({ ...editValues, priority: e.target.value })}
                                                    >
                                                        <option value="obligatory">🔒 Obligatoryjne</option>
                                                        <option value="high">🔴 Wysokie</option>
                                                        <option value="medium">🟡 Średnie</option>
                                                        <option value="low">🟢 Niskie</option>
                                                        <option value="discretionary">⚪ Dyskrecjonalne</option>
                                                    </select>
                                                ) : (
                                                    <span className={`badge badge-${entry.priority === 'obligatory' ? 'danger' :
                                                        entry.priority === 'high' ? 'warning' :
                                                            entry.priority === 'medium' ? 'info' : 'primary'
                                                        }`}>
                                                        {entry.priority}
                                                    </span>
                                                )}
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
                                                {editingEntry === entry.id ? (
                                                    <div className="flex gap-sm">
                                                        <button
                                                            className="btn btn-success btn-sm"
                                                            onClick={() => handleSaveEntry(entry.id)}
                                                        >
                                                            ✓
                                                        </button>
                                                        <button
                                                            className="btn btn-secondary btn-sm"
                                                            onClick={() => setEditingEntry(null)}
                                                        >
                                                            ✕
                                                        </button>
                                                    </div>
                                                ) : (
                                                    <div className="flex gap-sm">
                                                        <button
                                                            className="btn btn-secondary btn-sm"
                                                            onClick={() => handleEditEntry(entry)}
                                                            disabled={entry.status === 'approved'}
                                                        >
                                                            ✏️
                                                        </button>
                                                        {entry.status === 'draft' && (
                                                            <button
                                                                className="btn btn-primary btn-sm"
                                                                onClick={() => handleSubmitEntry(entry.id)}
                                                            >
                                                                📤
                                                            </button>
                                                        )}
                                                    </div>
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>

                    {}
                    <div className="card mt-lg">
                        <div className="card-header">
                            <h3 className="card-title">
                                <span className="card-title-icon">💡</span>
                                Generative UI - Jak to działa?
                            </h3>
                        </div>
                        <div className="agent-body">
                            <div className="alert alert-info">
                                <span className="alert-icon">🤖</span>
                                <div>
                                    <strong>Zamiast wysyłać plik Excel</strong>
                                    <p>System generuje spersonalizowany formularz dla każdego Dyrektora Departamentu,
                                        pokazując <strong>tylko ich pozycje</strong>. Walidacja w czasie rzeczywistym zapobiega
                                        przekroczeniu limitu <strong>zanim</strong> dane zostaną zapisane.</p>
                                </div>
                            </div>
                            <ul style={{ listStyle: 'none', padding: 0 }}>
                                <li className="mb-sm">✅ <strong>Brak konfliktów wersji</strong> - wszystkie zmiany zapisywane centralnie</li>
                                <li className="mb-sm">✅ <strong>Walidacja na żywo</strong> - system blokuje przekroczenie limitu</li>
                                <li className="mb-sm">✅ <strong>Audit trail</strong> - każda zmiana jest logowana</li>
                                <li className="mb-sm">✅ <strong>Zgodność z regulacjami</strong> - automatyczna walidacja paragrafów</li>
                            </ul>
                        </div>
                    </div>
                </div>
            )}

            {}
            {!selectedDept && !loading && (
                <div className="card" style={{ textAlign: 'center', padding: 'var(--spacing-2xl)' }}>
                    <div style={{ fontSize: '4rem', marginBottom: '1rem' }}>🏢</div>
                    <h3 className="mb-md">Wybierz Departament</h3>
                    <p className="text-secondary">
                        Kliknij na departament powyżej, aby zobaczyć jego pozycje budżetowe
                    </p>
                </div>
            )}
        </div>
    );
}
