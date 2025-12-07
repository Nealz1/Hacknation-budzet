const API_BASE = 'http://localhost:8000/api';

class ApiService {
    async request(endpoint, options = {}) {
        const url = `${API_BASE}${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
            ...options,
        };

        try {
            const response = await fetch(url, config);
            if (!response.ok) {
                const error = await response.json().catch(() => ({ detail: 'Request failed' }));
                throw new Error(error.detail || `HTTP ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error(`API Error (${endpoint}):`, error);
            throw error;
        }
    }

    async healthCheck() {
        return this.request('/health');
    }

    async getDashboardStats() {
        return this.request('/dashboard/stats');
    }

    async loadDemoData() {
        return this.request('/ingest/demo', { method: 'POST' });
    }

    async uploadExcel(file) {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch(`${API_BASE}/ingest/excel`, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            throw new Error('Upload failed');
        }
        return response.json();
    }

    async getEntries(filters = {}) {
        const params = new URLSearchParams();
        if (filters.department_code) params.append('department_code', filters.department_code);
        if (filters.status) params.append('status', filters.status);
        if (filters.priority) params.append('priority', filters.priority);
        if (filters.limit) params.append('limit', filters.limit);

        const query = params.toString();
        return this.request(`/entries${query ? '?' + query : ''}`);
    }

    async getEntry(id) {
        return this.request(`/entries/${id}`);
    }

    async createEntry(data) {
        return this.request('/entries', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async updateEntry(id, data) {
        return this.request(`/entries/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    }

    async approveEntry(id) {
        return this.request(`/entries/${id}/approve`, { method: 'POST' });
    }

    async rejectEntry(id, reason) {
        return this.request(`/entries/${id}/reject?reason=${encodeURIComponent(reason)}`, { method: 'POST' });
    }

    async getDepartments() {
        return this.request('/departments');
    }

    async getDepartmentEntries(code, year = 2025) {
        return this.request(`/departments/${code}/entries?year=${year}`);
    }

    async setDepartmentLimit(code, limit) {
        return this.request(`/departments/${code}/limit?limit=${limit}`, { method: 'PUT' });
    }

    async validateEntry(id) {
        return this.request(`/compliance/validate/${id}`, { method: 'POST' });
    }

    async semanticValidateEntry(id) {
        return this.request(`/compliance/semantic-validate/${id}`, { method: 'POST' });
    }

    async validateAllEntries() {
        return this.request('/compliance/validate-all', { method: 'POST' });
    }

    async getComplianceSummary() {
        return this.request('/compliance/summary');
    }

    async getKnowledgeFiles() {
        return this.request('/knowledge/files');
    }

    async getGapAnalysis(year = 2025) {
        return this.request(`/optimization/gap-analysis?year=${year}`);
    }

    async suggestCuts(targetReduction = null, year = 2025) {
        const params = new URLSearchParams({ year });
        if (targetReduction) params.append('target_reduction', targetReduction);
        return this.request(`/optimization/suggest-cuts?${params}`, { method: 'POST' });
    }

    async applyOptimization(entryId, action, newAmount = null, year = 2025) {
        const params = new URLSearchParams({ action, year });
        if (newAmount !== null) params.append('new_amount', newAmount);
        return this.request(`/optimization/apply/${entryId}?${params}`, { method: 'POST' });
    }

    async getDepartmentAllocation(year = 2025) {
        return this.request(`/optimization/department-allocation?year=${year}`);
    }

    async detectConflicts(year = 2025) {
        return this.request(`/conflicts/detect?year=${year}`, { method: 'POST' });
    }

    async resolveConflict(conflictId, resolution, keepEntryId = null, notes = null) {
        const params = new URLSearchParams({ resolution });
        if (keepEntryId) params.append('keep_entry_id', keepEntryId);
        if (notes) params.append('notes', notes);
        return this.request(`/conflicts/${conflictId}/resolve?${params}`, { method: 'POST' });
    }

    async getConflictsSummary() {
        return this.request('/conflicts/summary');
    }

    async getLimits() {
        return this.request('/limits');
    }

    async setGlobalLimit(year, limit) {
        return this.request(`/limits/${year}?limit=${limit}`, { method: 'PUT' });
    }

    // ============================================================================
    // AUDIT HISTORY - Version Tracking APIs
    // ============================================================================

    async getEntryHistory(entryId) {
        return this.request(`/entries/${entryId}/history`);
    }

    async getAllAuditHistory(limit = 50, action = null) {
        const params = new URLSearchParams({ limit });
        if (action) params.append('action', action);
        return this.request(`/audit/all?${params}`);
    }

    async restoreVersion(entryId, auditId) {
        return this.request(`/entries/${entryId}/restore/${auditId}`, { method: 'POST' });
    }

    async compareVersions(entryId, auditIdA, auditIdB) {
        return this.request(`/entries/${entryId}/compare/${auditIdA}/${auditIdB}`);
    }
}

const api = new ApiService();
export default api;
