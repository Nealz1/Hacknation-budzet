import { useState, useEffect } from 'react';
import api from '../services/api';

function Forecaster({ setActivePage }) {
    const [forecast, setForecast] = useState(null);
    const [anomalies, setAnomalies] = useState([]);
    const [optimization, setOptimization] = useState(null);
    const [loading, setLoading] = useState(true);
    const [exporting, setExporting] = useState(false);
    const [error, setError] = useState(null);
    const [activeTab, setActiveTab] = useState('forecast');
    const [generatedAt, setGeneratedAt] = useState(null);

    useEffect(() => {
        loadForecast();
    }, []);

    const loadForecast = async () => {
        try {
            setLoading(true);
            const [forecastData, anomalyData] = await Promise.all([
                api.getForecast(2025, 4),
                api.getAnomalies(2025)
            ]);
            setForecast(forecastData);
            setAnomalies(anomalyData || []);
            setGeneratedAt(new Date());
            setError(null);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const runOptimization = async () => {
        try {
            setLoading(true);
            const result = await api.optimizeAllocation();
            setOptimization(result);
            setActiveTab('optimization');
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const exportReport = async () => {
        try {
            setExporting(true);
            // Use the existing summary report endpoint
            const response = await fetch('http://localhost:8000/api/documents/summary-report?year=2025');
            if (!response.ok) throw new Error('Export failed');

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `Raport_Prognozy_${new Date().toISOString().split('T')[0]}.docx`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        } catch (err) {
            setError('Błąd eksportu: ' + err.message);
        } finally {
            setExporting(false);
        }
    };

    const navigateToEntry = (entryId) => {
        // Navigate to entries page with the specific entry
        if (setActivePage) {
            setActivePage('entries');
            // Store the entry ID in sessionStorage for the Entries component to pick up
            sessionStorage.setItem('highlightEntryId', entryId);
        }
    };

    const formatNumber = (num) => {
        return new Intl.NumberFormat('pl-PL').format(Math.round(num || 0));
    };

    const formatTimestamp = (date) => {
        if (!date) return '';
        return date.toLocaleString('pl-PL', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    // Polish translations for trends
    const translateTrend = (trend) => {
        const translations = {
            'rapidly_increasing': 'Szybko rosnący',
            'increasing': 'Rosnący',
            'stable': 'Stabilny',
            'decreasing': 'Malejący',
            'unknown': 'Nieznany'
        };
        return translations[trend] || trend;
    };

    const getTrendIcon = (trend) => {
        switch (trend) {
            case 'rapidly_increasing': return '🚀';
            case 'increasing': return '📈';
            case 'stable': return '➡️';
            case 'decreasing': return '📉';
            default: return '❓';
        }
    };

    const getSeverityLabel = (severity) => {
        const labels = {
            'high': 'Wysoki',
            'medium': 'Średni',
            'low': 'Niski'
        };
        return labels[severity] || severity;
    };

    const getAnomalyTypeLabel = (type) => {
        const labels = {
            'outlier': 'Wartość odstająca',
            'missing_justification': 'Brak uzasadnienia',
            'classification_mismatch': 'Niezgodność klasyfikacji'
        };
        return labels[type] || type;
    };

    const getSeverityColor = (severity) => {
        switch (severity) {
            case 'high': return 'var(--danger)';
            case 'medium': return 'var(--warning)';
            case 'low': return 'var(--info)';
            default: return 'var(--text-muted)';
        }
    };

    const getMaxForecast = () => {
        if (!forecast?.forecasts) return 0;
        return Math.max(
            forecast.base_total,
            ...forecast.forecasts.map(f => f.predicted_total)
        );
    };

    // Data for line chart
    const getChartData = () => {
        if (!forecast?.forecasts) return [];
        return [
            { year: forecast.base_year, value: forecast.base_total, type: 'actual' },
            ...forecast.forecasts.map(f => ({ year: f.year, value: f.predicted_total, type: 'forecast', confidence: f.confidence }))
        ];
    };

    return (
        <div className="page-container">
            {/* Header */}
            <div className="page-header">
                <div>
                    <h1 className="page-title">
                        <span className="title-icon">🔮</span>
                        Forecaster Agent
                    </h1>
                    <p className="page-subtitle">
                        Prognozowanie wieloletnie • Wykrywanie anomalii • Optymalizacja alokacji
                    </p>
                    {generatedAt && (
                        <p className="text-muted text-sm mt-xs">
                            📅 Wygenerowano: {formatTimestamp(generatedAt)}
                        </p>
                    )}
                </div>
                <div className="flex gap-md">
                    <button className="btn btn-secondary" onClick={loadForecast} disabled={loading}>
                        🔄 Odśwież
                    </button>
                    <button
                        className="btn btn-secondary"
                        onClick={exportReport}
                        disabled={exporting || loading}
                    >
                        {exporting ? '⏳ Eksportowanie...' : '📄 Eksportuj raport'}
                    </button>
                    <button className="btn btn-primary" onClick={runOptimization} disabled={loading}>
                        ⚡ Optymalizuj alokację
                    </button>
                </div>
            </div>

            {error && (
                <div className="card" style={{ background: 'var(--danger-bg)', borderColor: 'var(--danger)', marginBottom: 'var(--spacing-lg)' }}>
                    <p style={{ color: 'var(--danger)', margin: 0 }}>⚠️ {error}</p>
                </div>
            )}

            {/* Tabs */}
            <div className="flex gap-sm mb-lg">
                {['forecast', 'anomalies', 'optimization'].map((tab) => (
                    <button
                        key={tab}
                        className={`btn ${activeTab === tab ? 'btn-primary' : 'btn-ghost'}`}
                        onClick={() => setActiveTab(tab)}
                    >
                        {tab === 'forecast' && '📊 Prognoza'}
                        {tab === 'anomalies' && `🚨 Anomalie (${anomalies.length})`}
                        {tab === 'optimization' && '⚡ Optymalizacja'}
                    </button>
                ))}
            </div>

            {loading ? (
                <div className="card text-center p-xl">
                    <div className="spinner"></div>
                    <p className="text-muted mt-md">Obliczanie prognoz...</p>
                </div>
            ) : (
                <>
                    {/* Forecast Tab */}
                    {activeTab === 'forecast' && forecast && (
                        <div>
                            {/* Summary Cards */}
                            <div className="grid grid-cols-4 gap-md mb-lg">
                                <div className="card text-center">
                                    <div className="text-muted text-sm mb-sm">Rok bazowy</div>
                                    <div className="text-3xl font-bold text-primary">{forecast.base_year}</div>
                                    <div className="text-lg text-secondary">{formatNumber(forecast.base_total)} tys.</div>
                                </div>

                                {forecast.forecasts?.slice(0, 3).map((f, idx) => (
                                    <div key={idx} className="card text-center">
                                        <div className="text-muted text-sm mb-sm">Prognoza {f.year}</div>
                                        <div className="text-3xl font-bold" style={{ color: idx === 0 ? 'var(--warning)' : idx === 1 ? 'var(--info)' : 'var(--success)' }}>
                                            {f.year}
                                        </div>
                                        <div className="text-lg text-secondary">{formatNumber(f.predicted_total)} tys.</div>
                                        <div className="text-xs text-muted">
                                            {getTrendIcon(f.trend)} {(f.confidence * 100).toFixed(0)}% pewności
                                        </div>
                                    </div>
                                ))}
                            </div>

                            {/* Trend Analysis */}
                            <div className="card mb-lg">
                                <h3 className="mb-md">📈 Analiza Trendu</h3>
                                {forecast.trend_analysis && (
                                    <div className="grid grid-cols-3 gap-md">
                                        <div className="p-md" style={{ background: 'var(--bg-darker)', borderRadius: 'var(--radius-md)' }}>
                                            <div className="text-muted text-sm">Trend</div>
                                            <div className="text-xl font-bold">
                                                {getTrendIcon(forecast.trend_analysis.trend)} {translateTrend(forecast.trend_analysis.trend)}
                                            </div>
                                        </div>
                                        <div className="p-md" style={{ background: 'var(--bg-darker)', borderRadius: 'var(--radius-md)' }}>
                                            <div className="text-muted text-sm">Wzrost łączny</div>
                                            <div className="text-xl font-bold" style={{ color: forecast.trend_analysis.total_growth_percent > 0 ? 'var(--warning)' : 'var(--success)' }}>
                                                {forecast.trend_analysis.total_growth_percent > 0 ? '+' : ''}{forecast.trend_analysis.total_growth_percent}%
                                            </div>
                                        </div>
                                        <div className="p-md" style={{ background: 'var(--bg-darker)', borderRadius: 'var(--radius-md)' }}>
                                            <div className="text-muted text-sm">Wzrost roczny</div>
                                            <div className="text-xl font-bold">
                                                {forecast.trend_analysis.annual_growth_percent > 0 ? '+' : ''}{forecast.trend_analysis.annual_growth_percent}%
                                            </div>
                                        </div>
                                    </div>
                                )}
                                {forecast.trend_analysis?.warning && (
                                    <div className="mt-md p-md" style={{ background: 'var(--warning-bg)', borderRadius: 'var(--radius-md)', color: 'var(--warning)' }}>
                                        {forecast.trend_analysis.warning}
                                    </div>
                                )}
                            </div>

                            {/* Line Chart Visualization */}
                            <div className="card mb-lg">
                                <h3 className="mb-md">📉 Wykres Trendu Wieloletniego</h3>
                                <div style={{ position: 'relative', height: '250px', padding: '20px' }}>
                                    {/* Y-Axis labels */}
                                    <div style={{ position: 'absolute', left: 0, top: 20, bottom: 40, width: '60px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', alignItems: 'flex-end', paddingRight: '10px' }}>
                                        <span className="text-xs text-muted">{formatNumber(getMaxForecast())}</span>
                                        <span className="text-xs text-muted">{formatNumber(getMaxForecast() / 2)}</span>
                                        <span className="text-xs text-muted">0</span>
                                    </div>

                                    {/* Chart Area */}
                                    <div style={{ marginLeft: '70px', height: '100%', position: 'relative' }}>
                                        {/* Grid lines */}
                                        <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 30, borderBottom: '1px solid var(--border-color)', borderLeft: '1px solid var(--border-color)' }}>
                                            <div style={{ position: 'absolute', top: '50%', left: 0, right: 0, borderTop: '1px dashed var(--border-color)' }}></div>
                                        </div>

                                        {/* Line Chart with SVG */}
                                        <svg style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: 'calc(100% - 30px)' }} preserveAspectRatio="none">
                                            {/* Area fill */}
                                            <defs>
                                                <linearGradient id="areaGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                                                    <stop offset="0%" stopColor="var(--primary)" stopOpacity="0.3" />
                                                    <stop offset="100%" stopColor="var(--primary)" stopOpacity="0.05" />
                                                </linearGradient>
                                            </defs>

                                            {getChartData().length > 0 && (
                                                <>
                                                    {/* Area Path */}
                                                    <path
                                                        d={`M ${0} ${100 - (getChartData()[0].value / getMaxForecast()) * 100}% 
                                                            ${getChartData().map((d, i) =>
                                                            `L ${(i / (getChartData().length - 1)) * 100}% ${100 - (d.value / getMaxForecast()) * 100}%`
                                                        ).join(' ')} 
                                                            L 100% 100% L 0% 100% Z`}
                                                        fill="url(#areaGradient)"
                                                    />

                                                    {/* Line Path */}
                                                    <polyline
                                                        points={getChartData().map((d, i) =>
                                                            `${(i / (getChartData().length - 1)) * 100}%,${100 - (d.value / getMaxForecast()) * 100}%`
                                                        ).join(' ')}
                                                        fill="none"
                                                        stroke="var(--primary)"
                                                        strokeWidth="3"
                                                        strokeLinejoin="round"
                                                    />
                                                </>
                                            )}
                                        </svg>

                                        {/* Data Points */}
                                        <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 30, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
                                            {getChartData().map((d, i) => (
                                                <div
                                                    key={i}
                                                    style={{
                                                        position: 'relative',
                                                        height: `${(d.value / getMaxForecast()) * 100}%`,
                                                        display: 'flex',
                                                        flexDirection: 'column',
                                                        alignItems: 'center'
                                                    }}
                                                >
                                                    {/* Point */}
                                                    <div
                                                        style={{
                                                            width: '12px',
                                                            height: '12px',
                                                            borderRadius: '50%',
                                                            background: d.type === 'actual' ? 'var(--primary)' : 'var(--warning)',
                                                            border: '2px solid white',
                                                            boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
                                                            opacity: d.confidence || 1
                                                        }}
                                                        title={`${d.year}: ${formatNumber(d.value)} tys. PLN`}
                                                    ></div>

                                                    {/* Value label */}
                                                    <div
                                                        className="text-xs font-bold"
                                                        style={{
                                                            position: 'absolute',
                                                            top: '-20px',
                                                            whiteSpace: 'nowrap',
                                                            color: d.type === 'actual' ? 'var(--primary)' : 'var(--warning)'
                                                        }}
                                                    >
                                                        {formatNumber(d.value)}
                                                    </div>
                                                </div>
                                            ))}
                                        </div>

                                        {/* X-Axis Labels */}
                                        <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, height: '30px', display: 'flex', justifyContent: 'space-between' }}>
                                            {getChartData().map((d, i) => (
                                                <div key={i} className="text-sm font-bold text-center" style={{ color: d.type === 'actual' ? 'var(--primary)' : 'var(--text-secondary)' }}>
                                                    {d.year}
                                                    {d.type === 'forecast' && <div className="text-xs text-muted">(prognoza)</div>}
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                </div>

                                {/* Legend */}
                                <div className="flex gap-lg justify-center mt-md">
                                    <div className="flex items-center gap-sm">
                                        <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: 'var(--primary)' }}></div>
                                        <span className="text-sm">Dane rzeczywiste</span>
                                    </div>
                                    <div className="flex items-center gap-sm">
                                        <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: 'var(--warning)' }}></div>
                                        <span className="text-sm">Prognoza</span>
                                    </div>
                                </div>
                            </div>

                            {/* Bar Chart - Original */}
                            <div className="card mb-lg">
                                <h3 className="mb-md">📊 Porównanie Roczne</h3>
                                <div className="flex items-end gap-md" style={{ height: '180px', padding: '20px 0' }}>
                                    {/* Base Year */}
                                    <div className="flex flex-col items-center" style={{ flex: 1 }}>
                                        <div
                                            style={{
                                                width: '100%',
                                                maxWidth: '80px',
                                                height: `${(forecast.base_total / getMaxForecast()) * 150}px`,
                                                background: 'linear-gradient(to top, var(--primary), var(--primary-light))',
                                                borderRadius: 'var(--radius-md) var(--radius-md) 0 0',
                                                transition: 'height 0.5s ease'
                                            }}
                                        ></div>
                                        <div className="text-sm font-bold mt-sm">{forecast.base_year}</div>
                                        <div className="text-xs text-muted">{formatNumber(forecast.base_total)}</div>
                                    </div>

                                    {/* Forecasted Years */}
                                    {forecast.forecasts?.map((f, idx) => {
                                        const colors = ['var(--warning)', 'var(--info)', 'var(--success)', 'var(--accent)'];
                                        return (
                                            <div key={idx} className="flex flex-col items-center" style={{ flex: 1 }}>
                                                <div
                                                    style={{
                                                        width: '100%',
                                                        maxWidth: '80px',
                                                        height: `${(f.predicted_total / getMaxForecast()) * 150}px`,
                                                        background: `linear-gradient(to top, ${colors[idx]}, ${colors[idx]}88)`,
                                                        borderRadius: 'var(--radius-md) var(--radius-md) 0 0',
                                                        transition: 'height 0.5s ease',
                                                        opacity: f.confidence
                                                    }}
                                                ></div>
                                                <div className="text-sm font-bold mt-sm">{f.year}</div>
                                                <div className="text-xs text-muted">{formatNumber(f.predicted_total)}</div>
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>

                            {/* Recommendations */}
                            {forecast.recommendations?.length > 0 && (
                                <div className="card">
                                    <h3 className="mb-md">💡 Rekomendacje</h3>
                                    <div className="flex flex-col gap-md">
                                        {forecast.recommendations.map((rec, idx) => (
                                            <div
                                                key={idx}
                                                className="p-md"
                                                style={{
                                                    background: 'var(--bg-darker)',
                                                    borderRadius: 'var(--radius-md)',
                                                    borderLeft: `4px solid ${rec.priority === 'high' || rec.priority === 'wysoki' ? 'var(--danger)' : rec.priority === 'średni' || rec.priority === 'medium' ? 'var(--warning)' : 'var(--info)'}`
                                                }}
                                            >
                                                <div className="flex justify-between items-start">
                                                    <div>
                                                        <div className="font-bold mb-xs">{rec.title}</div>
                                                        <div className="text-secondary text-sm">{rec.description}</div>
                                                        <div className="text-muted text-xs mt-sm">💡 {rec.action}</div>
                                                    </div>
                                                    <span
                                                        className="badge"
                                                        style={{
                                                            background: rec.priority === 'high' || rec.priority === 'wysoki' ? 'var(--danger)' : rec.priority === 'średni' || rec.priority === 'medium' ? 'var(--warning)' : 'var(--info)',
                                                            color: 'white'
                                                        }}
                                                    >
                                                        {rec.priority === 'high' ? 'Wysoki' : rec.priority === 'medium' ? 'Średni' : rec.priority}
                                                    </span>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Anomalies Tab */}
                    {activeTab === 'anomalies' && (
                        <div className="card">
                            <h3 className="mb-md">🚨 Wykryte Anomalie ({anomalies.length})</h3>

                            {anomalies.length === 0 ? (
                                <div className="text-center p-xl">
                                    <div className="text-4xl mb-md">✅</div>
                                    <p className="text-success font-bold">Brak wykrytych anomalii!</p>
                                    <p className="text-muted">Dane budżetowe wyglądają prawidłowo.</p>
                                </div>
                            ) : (
                                <div className="flex flex-col gap-md">
                                    {anomalies.map((anomaly, idx) => (
                                        <div
                                            key={idx}
                                            className="p-md"
                                            style={{
                                                background: 'var(--bg-darker)',
                                                borderRadius: 'var(--radius-md)',
                                                borderLeft: `4px solid ${getSeverityColor(anomaly.severity)}`,
                                                cursor: 'pointer',
                                                transition: 'transform 0.2s ease, box-shadow 0.2s ease'
                                            }}
                                            onClick={() => navigateToEntry(anomaly.entry_id)}
                                            onMouseEnter={(e) => {
                                                e.currentTarget.style.transform = 'translateX(4px)';
                                                e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
                                            }}
                                            onMouseLeave={(e) => {
                                                e.currentTarget.style.transform = 'translateX(0)';
                                                e.currentTarget.style.boxShadow = 'none';
                                            }}
                                        >
                                            <div className="flex justify-between items-start">
                                                <div>
                                                    <div className="flex items-center gap-sm mb-sm">
                                                        <span
                                                            className="badge"
                                                            style={{ background: getSeverityColor(anomaly.severity), color: 'white' }}
                                                        >
                                                            {getSeverityLabel(anomaly.severity)}
                                                        </span>
                                                        <span className="badge" style={{ background: 'var(--bg-dark)' }}>
                                                            {getAnomalyTypeLabel(anomaly.type)}
                                                        </span>
                                                        <span className="text-muted text-sm">Pozycja #{anomaly.entry_id}</span>
                                                    </div>
                                                    <div className="font-bold mb-xs">{anomaly.task}</div>
                                                    <div className="text-secondary text-sm">{anomaly.description}</div>
                                                    <div className="text-muted text-xs mt-sm">💡 {anomaly.recommendation}</div>
                                                </div>
                                                <div className="flex items-center gap-sm">
                                                    <span className="text-primary text-sm">Przejdź →</span>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {anomalies.length > 0 && (
                                <div className="mt-lg p-md" style={{ background: 'var(--info-bg)', borderRadius: 'var(--radius-md)' }}>
                                    <p className="text-sm" style={{ color: 'var(--info)' }}>
                                        💡 <strong>Wskazówka:</strong> Kliknij na anomalię, aby przejść do szczegółów pozycji budżetowej i wprowadzić poprawki.
                                    </p>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Optimization Tab */}
                    {activeTab === 'optimization' && (
                        <div>
                            {!optimization ? (
                                <div className="card text-center p-xl">
                                    <div className="text-4xl mb-md">⚡</div>
                                    <p className="text-muted mb-lg">Optymalizacja alokacji wieloletniej</p>
                                    <button className="btn btn-primary btn-lg" onClick={runOptimization}>
                                        🚀 Uruchom optymalizację
                                    </button>
                                </div>
                            ) : (
                                <div>
                                    {/* Allocation by year */}
                                    <div className="card mb-lg">
                                        <h3 className="mb-md">📊 Alokacja według roku</h3>
                                        <div className="table-container">
                                            <table className="table">
                                                <thead>
                                                    <tr>
                                                        <th>Rok</th>
                                                        <th>Limit</th>
                                                        <th>Nieodwoływalne</th>
                                                        <th>Odwoływalne</th>
                                                        <th>Suma</th>
                                                        <th>Luka / Nadwyżka</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    {Object.entries(optimization.allocation || {}).map(([year, data]) => (
                                                        <tr key={year}>
                                                            <td className="font-bold">{year}</td>
                                                            <td>{formatNumber(data.limit)}</td>
                                                            <td>{formatNumber(data.non_deferrable)}</td>
                                                            <td>{formatNumber(data.deferrable_allocated)}</td>
                                                            <td className="font-bold">{formatNumber(data.total_allocated)}</td>
                                                            <td>
                                                                {data.gap > 0 ? (
                                                                    <span style={{ color: 'var(--danger)' }}>
                                                                        🔴 -{formatNumber(data.gap)}
                                                                    </span>
                                                                ) : (
                                                                    <span style={{ color: 'var(--success)' }}>
                                                                        🟢 +{formatNumber(data.surplus)}
                                                                    </span>
                                                                )}
                                                            </td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>
                                    </div>

                                    {/* Suggested Shifts */}
                                    {optimization.suggested_shifts?.length > 0 && (
                                        <div className="card">
                                            <h3 className="mb-md">🔄 Sugerowane przesunięcia</h3>
                                            <div className="flex flex-col gap-md">
                                                {optimization.suggested_shifts.map((shift, idx) => (
                                                    <div
                                                        key={idx}
                                                        className="p-md flex items-center gap-md"
                                                        style={{ background: 'var(--bg-darker)', borderRadius: 'var(--radius-md)' }}
                                                    >
                                                        <div className="text-2xl">{shift.from_year}</div>
                                                        <div className="text-2xl">➡️</div>
                                                        <div className="text-2xl">{shift.to_year}</div>
                                                        <div className="flex-1">
                                                            <div className="font-bold">{formatNumber(shift.amount)} tys. PLN</div>
                                                            <div className="text-muted text-sm">{shift.reason}</div>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {optimization.suggested_shifts?.length === 0 && (
                                        <div className="card text-center p-lg">
                                            <div className="text-3xl mb-sm">✅</div>
                                            <p className="text-success">Alokacja jest już optymalna!</p>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    )}
                </>
            )}
        </div>
    );
}

export default Forecaster;
